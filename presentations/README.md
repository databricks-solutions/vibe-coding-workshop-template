# Workshop Presentation

MARP-based slide deck for the Vibe Coding Workshop. Covers the Data Product Accelerator (55 agent skills, 9-stage pipeline), platform training modules (Databricks Apps, AppKit, Lakebase, SDP/DLT, Genie Spaces), and the AppKit + Lakebase hands-on workshop.

## Prerequisites

Install marp-cli globally:

```bash
npm install -g @marp-team/marp-cli
```

An internet connection is required during rendering (mermaid diagrams load from CDN).

## Rendering

### HTML (recommended -- includes slide transitions)

```bash
marp --no-stdin --html presentations/workshop.marp.md -o presentations/workshop.html
```

Open `workshop.html` in Chrome/Edge for the best experience. Use arrow keys to navigate, `F` for fullscreen, `P` for presenter mode with speaker notes.

### PDF (printable handout)

```bash
marp --no-stdin --html --pdf presentations/workshop.marp.md -o presentations/workshop.pdf
```

### PPTX (shareable PowerPoint)

```bash
marp --no-stdin --html --pptx presentations/workshop.marp.md -o presentations/workshop.pptx
```

Each slide is rendered as an image inside the PPTX. Text is not editable, but all visuals (including mermaid diagrams) render correctly.

### Live Preview (hot reload)

```bash
marp -s --html presentations/workshop.marp.md
```

Opens a local server with live reload on file changes. Great for iterating on content.

## File Structure

```
presentations/
├── README.md              # This file
├── workshop.marp.md       # Source slide deck (Markdown + MARP directives)
├── workshop.html          # GENERATED: HTML output (slide deck)
├── workshop-explorer.html # Interactive workshop explorer (standalone)
├── workshop.pdf           # GENERATED: PDF output
└── workshop.pptx          # GENERATED: PPTX output
```

## Slide Outline (~70 slides, 5 acts)

| Act | Slides | Content |
|-----|--------|---------|
| I   | 1-8    | Welcome, vibe coding intro, repo overview, skill anatomy |
| II  | 9-30   | Data Product Accelerator 9-stage animated journey |
| III | 31-46  | Platform training: Apps, AppKit, Lakebase, SDP, Genie, UC |
| IV  | 47-62  | AppKit + Lakebase 5-phase workshop journey |
| V   | 63-70  | Synthesis, hands-on prompts, resources, Q&A |

## Notes

- The `--html` flag is **required** for all render commands (enables mermaid diagrams and styled HTML).
- Transitions only work in HTML output viewed in a browser. PDF and PPTX are static.
- Presenter mode (`P` key in browser) shows speaker notes with timing cues.
- The dark theme is optimized for projection. For printed handouts, consider the PDF output.
