# SkyLoyalty Variant Selector

> **Owned by:** `genai-agents/00-course-orchestrator/SKILL.md`.
> The root course path documents Variant 4 as the canonical walkthrough.
> Other variants are catalogued for comparison in
> `references/alternate-methods-catalog.md`; this template does not include
> root `alternate_methods/` walkthrough files.

| # | Name | Walkthrough | Underlying pathway+track | When to pick |
|---|------|-------------|--------------------------|--------------|
| 1 | Supervisor API + AppKit | Not bundled as a root walkthrough | Pathway C + Track B mirror | Hosted tools only, no custom loop, fastest ramp |
| 2 | Model Serving + AppKit | Not bundled as a root walkthrough | Pathway C + Track C mirror | Existing agents, multi-agent Genie, Knowledge Assistant |
| 3 | Agent on Apps (template UI only) | Use Track A and skip AppKit prompts | Pathway D + Track A | Conversational-only POC, fastest deploy |
| 4 | Agent on Apps + AppKit (canonical) | [`PROMPT-GUIDE.md`](../../PROMPT-GUIDE.md) | Pathway C + Track A | Full Python agent + rich AppKit dashboard (two Apps) |
| 5 | Integrated AppKit (Node-native) | Not included in this template | Single-App TypeScript exploration | TypeScript end-to-end, OK with OTLP + Playwright in lieu of MLflow SDLC |

**If you pick Variant 5,** treat it as custom exploration. The root template
does not include the older `06c-appkit-integrated-agent` skill path.

For the full canonical prompt flow, see [`PROMPT-GUIDE.md`](../../PROMPT-GUIDE.md).
