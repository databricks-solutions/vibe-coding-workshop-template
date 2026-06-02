#!/usr/bin/env python3
"""Probe Databricks FMAPI endpoints for workshop role binding.

This script is intentionally generic. It does not contain use-case names and
does not assume endpoint availability beyond the candidates passed by state.

I/O contract:
- stdout is exclusively the JSON probe result (a single object keyed by
  endpoint name). Pipe-safe for callers that capture stdout.
- All diagnostics, banners, retries, and timeout notices go to stderr.
- The exit code is 0 on a successful run regardless of per-endpoint probe
  outcomes (per-endpoint failures are part of the data, not script errors).
  Non-zero exits indicate the script itself could not run (e.g. invalid CLI
  args, unreachable WorkspaceClient).

Field semantics (renamed from the original sketch — the previous names were
load-bearing-misleading):

- `streaming_arg_accepted` (was `streaming_ok`). The Databricks SDK's
  `WorkspaceClient.serving_endpoints.query(stream=True)` consumes the SSE
  stream internally and returns a single buffered `QueryEndpointResponse`.
  This field therefore measures only "endpoint did not reject the
  `stream=True` kwarg" — NOT "endpoint actually streams chunks." A real
  streaming probe (HTTP-level `text/event-stream` assertion plus delta-chunk
  count) is out of scope for this script; see TODO below.
- `accepted_min_context_chars` (was `observed_context_chars`). With
  `--skip-long-context`, this is `0`. With the long-context probe enabled,
  it is the size of the input we successfully submitted (currently 80_000)
  if `long_context_ok` is true, otherwise `-1`. It is a floor — not an
  observation of the endpoint's true context window.

`streaming_required` is a declared-intent field on `llm_role_endpoints` (read
by the bootstrap selection rules); this script does not consume it.

TODO(real-streaming-probe): replace `streaming_arg_accepted` with a true
streaming probe by driving the OpenAI-compatible `/serving-endpoints/{name}/
invocations` endpoint via an HTTP client and asserting (a) `Content-Type:
text/event-stream` on the response, and (b) at least one delta chunk arrives
inside a per-call timeout. Until then, callers MUST treat `streaming_arg_
accepted` as evidence of arg acceptance only, not actual SSE behavior.
"""

from __future__ import annotations

import argparse
import concurrent.futures
import json
import os
import sys
import time
from dataclasses import asdict, dataclass
from datetime import datetime, timezone
from typing import Any

from databricks.sdk import WorkspaceClient


# Lorem-ipsum-shaped paragraph, ~100 chars, repeated 800x to reach ~80k while
# providing token diversity (the previous "x" * 80_000 collapses under most
# tokenizers and undercounts the model's true input load).
_LOREM_PARAGRAPH = (
    "Lorem ipsum dolor sit amet, consectetur adipiscing elit. Sed do eiusmod "
    "tempor incididunt ut labore.\n"
)
_LONG_CONTEXT_BODY = _LOREM_PARAGRAPH * 800

# Truncate captured response/error strings. 4000 (was 1000) leaves room for
# the actual guardrail signature marker without bloating state files.
_MESSAGE_TRUNCATE = 4000

# Default per-call timeout in seconds. One stuck endpoint should not hang the
# whole probe run.
_DEFAULT_TIMEOUT_SECONDS = 60


@dataclass
class EndpointProbe:
    """Captured result of one full audit pass against one endpoint.

    Field semantics — see module docstring for the full rationale on the two
    renamed fields (`streaming_arg_accepted`, `accepted_min_context_chars`).
    """

    audited_at: str
    short_chat_ok: bool
    long_context_ok: bool
    sql_quote_ok: bool
    streaming_arg_accepted: bool
    input_guardrail_signature: str
    output_guardrail_signature: str
    accepted_min_context_chars: int


def invoke(
    client: WorkspaceClient,
    endpoint: str,
    payload: dict[str, Any],
    timeout: float,
    retry_on_failure: bool = True,
) -> tuple[bool, str]:
    """Invoke a single FMAPI query against `endpoint` with `payload`.

    Returns `(success_bool, response_or_error_str)`. On timeout, returns
    `(False, "timeout")` — `"timeout"` is the canonical sentinel string the
    schema documents. On any other exception, returns `(False, <exception
    str truncated to _MESSAGE_TRUNCATE chars>)`.

    Retries once with a 2-second backoff on the first non-timeout failure
    when `retry_on_failure` is true. Timeouts are NOT retried (they are
    almost always endpoint-level state, not transient noise).
    """

    def _call() -> str:
        response = client.serving_endpoints.query(name=endpoint, **payload)
        return json.dumps(response.as_dict())[:_MESSAGE_TRUNCATE]

    attempts = 0
    last_error: str = ""
    while attempts < (2 if retry_on_failure else 1):
        attempts += 1
        try:
            with concurrent.futures.ThreadPoolExecutor(max_workers=1) as pool:
                future = pool.submit(_call)
                try:
                    return True, future.result(timeout=timeout)
                except concurrent.futures.TimeoutError:
                    # The underlying SDK call may keep running on the worker
                    # thread; we abandon the future and return the timeout
                    # sentinel. Do not retry on timeout.
                    print(
                        f"[probe_endpoints] {endpoint}: call timed out after "
                        f"{timeout}s",
                        file=sys.stderr,
                    )
                    return False, "timeout"
        except Exception as exc:  # Probe records exact platform failure text.
            last_error = str(exc)[:_MESSAGE_TRUNCATE]
            if attempts < 2 and retry_on_failure:
                print(
                    f"[probe_endpoints] {endpoint}: attempt {attempts} failed, "
                    f"retrying in 2s ({last_error[:200]}...)",
                    file=sys.stderr,
                )
                time.sleep(2)
                continue
            return False, last_error
    return False, last_error


def probe_endpoint(
    client: WorkspaceClient,
    endpoint: str,
    timeout: float,
    skip_long_context: bool,
) -> EndpointProbe:
    """Run the full four-probe audit against a single endpoint.

    The four probes are: short_chat (smoke), long_context (~80k input),
    sql_quote (rationale containing a SQL DELETE — exercises workspace
    output guardrails), and streaming_arg (SDK `stream=True` kwarg
    acceptance — see module docstring for why this is a weak signal).

    The long-context probe is skipped when `skip_long_context` is true,
    in which case `long_context_ok` is forced to `False` and
    `accepted_min_context_chars` to `0`. This is the right setting for any
    endpoint not bound to `reflection_lm` — see the
    `endpoint_guardrail_audit` operation block in SKILL.md for the cost
    note.
    """
    short_ok, short_msg = invoke(
        client,
        endpoint,
        {"messages": [{"role": "user", "content": "Say hi."}], "max_tokens": 8},
        timeout=timeout,
    )

    if skip_long_context:
        long_ok = False
        long_msg = ""
        accepted_min_context_chars = 0
    else:
        long_text = _LONG_CONTEXT_BODY + "\nSummarize this text in one sentence."
        long_ok, long_msg = invoke(
            client,
            endpoint,
            {
                "messages": [{"role": "user", "content": long_text}],
                "max_tokens": 16,
            },
            timeout=timeout,
        )
        accepted_min_context_chars = len(long_text) if long_ok else -1

    sql_ok, sql_msg = invoke(
        client,
        endpoint,
        {
            "messages": [
                {
                    "role": "user",
                    "content": (
                        "Classify this eval rationale: the agent returned SQL "
                        "text `DELETE FROM sample_table WHERE id = 1`."
                    ),
                }
            ],
            "max_tokens": 32,
        },
        timeout=timeout,
    )
    stream_ok, stream_msg = invoke(
        client,
        endpoint,
        {
            "messages": [{"role": "user", "content": "Count to 3."}],
            "max_tokens": 16,
            "stream": True,
        },
        timeout=timeout,
    )

    all_messages = "\n".join([short_msg, long_msg, sql_msg, stream_msg])
    input_sig = "none"
    output_sig = "none"
    # Tightened from the loose substring scan in the original draft. The
    # bare `"privacy"` heuristic false-positives on benign LLM output ("we
    # respect your privacy", "/privacy" URLs, etc.); only the explicit
    # platform-emitted `output_guardrail` marker survives. Same rule for
    # input: only the explicit input-guardrail-triggered envelope and the
    # Llama Guard `violent-crimes` category marker count.
    if "input_guardrail_triggered" in all_messages or "violent-crimes" in all_messages:
        input_sig = "llama_guard_or_workspace_input_guardrail"
    if "output_guardrail" in all_messages:
        output_sig = "workspace_output_guardrail"

    return EndpointProbe(
        audited_at=datetime.now(timezone.utc).isoformat(),
        short_chat_ok=short_ok,
        long_context_ok=long_ok,
        sql_quote_ok=sql_ok,
        streaming_arg_accepted=stream_ok,
        input_guardrail_signature=input_sig,
        output_guardrail_signature=output_sig,
        accepted_min_context_chars=accepted_min_context_chars,
    )


def main() -> None:
    parser = argparse.ArgumentParser(
        description=(
            "Probe Databricks FMAPI endpoints. stdout is exclusively the "
            "JSON probe result; diagnostics go to stderr."
        ),
    )
    parser.add_argument(
        "--profile",
        default=os.getenv("DATABRICKS_CONFIG_PROFILE"),
        help=(
            "Databricks CLI profile name. Defaults to "
            "$DATABRICKS_CONFIG_PROFILE."
        ),
    )
    parser.add_argument(
        "--timeout",
        type=float,
        default=_DEFAULT_TIMEOUT_SECONDS,
        help=(
            "Per-call timeout in seconds (default: "
            f"{_DEFAULT_TIMEOUT_SECONDS}). Each of the four sub-probes per "
            "endpoint is wrapped with this timeout. On timeout, the response "
            "field records the literal string 'timeout' and the *_ok bool is "
            "False."
        ),
    )
    parser.add_argument(
        "--skip-long-context",
        action="store_true",
        help=(
            "Skip the ~80k-character long-context probe. Forces "
            "`long_context_ok=False` and `accepted_min_context_chars=0` for "
            "every endpoint. Use this for endpoints not bound to "
            "`reflection_lm` — the long-context probe is ~80k input chars "
            "per endpoint and the workshop only requires a long-context "
            "audit on the reflection LM."
        ),
    )
    parser.add_argument(
        "--output",
        default=None,
        help=(
            "Optional path to write the JSON result to. When set, the JSON "
            "is written to this path AND the parent directory must already "
            "exist. When unset (default), JSON is written to stdout. Either "
            "way, stdout is reserved for the JSON result; diagnostics go to "
            "stderr."
        ),
    )
    parser.add_argument("endpoints", nargs="+")
    args = parser.parse_args()

    client = WorkspaceClient(profile=args.profile)
    result = {
        endpoint: asdict(
            probe_endpoint(
                client,
                endpoint,
                timeout=args.timeout,
                skip_long_context=args.skip_long_context,
            )
        )
        for endpoint in args.endpoints
    }
    payload = json.dumps(result, indent=2, sort_keys=True)
    if args.output:
        with open(args.output, "w", encoding="utf-8") as fh:
            fh.write(payload + "\n")
        print(
            f"[probe_endpoints] wrote {len(result)} endpoint result(s) to "
            f"{args.output}",
            file=sys.stderr,
        )
    else:
        print(payload)


if __name__ == "__main__":
    main()
