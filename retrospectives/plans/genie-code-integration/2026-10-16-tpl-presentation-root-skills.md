# tpl-presentation-root-skills — plan r0 (2026-10-16; human-ruled, D-217)

repo=template · base origin/feature/genie-code-mcp-integration (4655102)
PR plan path: retrospectives/plans/genie-code-integration/2026-10-16-tpl-presentation-root-skills.md
Status: SIGNED by the human's ruling (D-217; the ruling stands in for the critic, as with D-109). Docs only.

## Change
presentations/workshop-explorer.html:1558, the one sentence that today reads (inside the HTML):
"Five root <code>skills/</code> steer behavior across clients: <code>vibecoding-state</code> (detects the client
and gates each prompt), <code>genie-code-environment</code> (the in-workspace behavior manifest), and
<code>lakebase-cdf</code> (the Lakebase CDF reference for the <code>sync_from_lakebase</code> step when
<code>enable_lakebase_cdf=true</code>)."
→ name all five, in AGENTS.md:7's order and wording: vibecoding-state (detects the client and gates each prompt),
genie-code-environment (the in-workspace behavior manifest), databricks-asset-bundles and databricks-expert-agent
(shared deep-reference skills), and lakebase-cdf (unchanged clause). Same <code> markup style.
Only that sentence changes; every other byte of the file identical (line 1558 is one long HTML line: compare the
line with that sentence cut out).

## Acceptance
- A1 scope: presentations/workshop-explorer.html + this plan file (byte-identical to the FORGE copy).
- A2 the sentence names exactly the five skills AGENTS.md:7 names, each in <code>; nothing else on the line or in the
  file changed.
- A3 the HTML still parses (python html.parser, no new errors vs base) and the file's script blocks are unchanged.
- A4 diff gate (FORGE tools/genie_gate_diff.py, base-ref origin/feature/genie-code-mcp-integration, head-ref <commit>,
  APP seed copy from APP origin/feature/genie-code-mcp-integration): exit 0, counted lines and fork findings unchanged
  (presentations/ is not audited, so 0 change is expected).

## Tampers
- X1 drop databricks-expert-agent from the sentence → A2 red.
- X2 change one byte elsewhere on line 1558 → A2 red.

## Release
Review + gate, merge only into TPL integration. Then RC #28's head moves; refresh #28's description (B1, B3) and
run its one review + gate on the new head. The human merges #28.
