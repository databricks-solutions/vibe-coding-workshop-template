# Design Quality Guidelines for AppKit

> **Upstream (always check for latest):** https://github.com/anthropics/skills/blob/main/skills/frontend-design/SKILL.md
>
> This file adapts the Anthropic frontend-design skill for the AppKit context. AppKit UI components (Shadcn/Radix-based) are the structural foundation — layer distinctive styling on top of them.

---

## Design Thinking Process

Before writing any component code, answer these questions:

1. **Purpose** — What problem does this interface solve? Who are the users?
2. **Tone** — Pick a deliberate aesthetic: brutally minimal, maximalist, retro-futuristic, organic/natural, luxury/refined, playful, editorial, brutalist, art deco, soft/pastel, industrial/utilitarian. Commit to it.
3. **Constraints** — AppKit UI primitives, performance targets, accessibility requirements.
4. **Differentiation** — What makes this UI unforgettable? What's the one thing a user will remember?

Choose a clear conceptual direction and execute with precision. Bold maximalism and refined minimalism both work — the key is intentionality, not intensity.

---

## Aesthetic Guidelines

### Typography
- Choose fonts that are beautiful, unique, and characterful
- **Avoid** generic defaults: Inter, Roboto, Arial, system fonts
- Pair a distinctive display font with a refined body font
- Use font size, weight, and letter-spacing with deliberate contrast
- **Loading fonts in AppKit:** Add a Google Fonts `<link>` to `client/index.html`, then apply via `font-family` in `client/src/index.css`

### Color & Theme
- Commit to a cohesive palette using CSS variables
- Dominant colors with sharp accents outperform timid, evenly-distributed palettes
- **Avoid** cliched schemes — particularly purple gradients on white backgrounds
- Design for both light and dark themes; vary across projects
- **AppKit theming:** The scaffold generates `client/src/index.css` with commented-out oklch CSS custom properties (e.g. `--primary`, `--background`, `--accent`). Uncomment and customize these variables — this is the primary theming mechanism for creating a distinctive palette

### Motion & Interaction
- Use animations for delight and micro-interactions
- Focus on high-impact moments: a well-orchestrated page load with staggered reveals creates more delight than scattered micro-interactions
- Scroll-triggering and hover states that surprise
- Prefer CSS animations for HTML; use motion libraries in React when available

### Spatial Composition
- Unexpected layouts: asymmetry, overlap, diagonal flow, grid-breaking elements
- Generous negative space OR controlled density — both are valid directions
- Avoid predictable, cookie-cutter component placement

### Backgrounds & Visual Details
- Create atmosphere and depth, not just solid colors
- Gradient meshes, noise textures, geometric patterns, layered transparencies
- Dramatic shadows, decorative borders, custom cursors, grain overlays
- Match the visual treatment to the overall aesthetic

---

## Anti-Patterns (Generic AI Aesthetics)

Never produce UI that looks like "AI slop":

- Overused font families (Inter, Roboto, Arial, system fonts)
- Purple gradients on white backgrounds
- Predictable card-grid layouts with no visual hierarchy
- Cookie-cutter design that lacks context-specific character
- Converging on the same "safe" choices across different projects

Every project should feel distinct. Vary themes, fonts, layouts, and color palettes.

---

## Combining with AppKit UI Primitives

AppKit UI components are Shadcn/Radix-based. Use them as structural building blocks, then add distinctive styling:

- **Layout** — use AppKit grid/flex utilities for structure, then add asymmetry or unexpected spacing via custom CSS
- **Cards & Containers** — use `Card` components for semantic structure, customize with shadows, borders, backgrounds
- **Charts** — ECharts via AppKit props; customize colors, gradients, labels, and tooltip formatting for visual impact
- **Tables** — use AppKit `DataTable` for functionality, customize header styling, row hover states, alternating backgrounds
- **Forms** — use AppKit form primitives for accessibility, style with distinctive inputs, labels, and validation states

The goal: a UI that is technically sound (AppKit primitives handle accessibility, state, data binding) AND visually memorable (your styling choices make it unforgettable).

---

## Implementation Calibration

Match code complexity to the design vision:
- **Maximalist designs** need elaborate code — extensive animations, layered effects, rich textures
- **Minimalist designs** need restraint — precision in spacing, typography, and subtle details
- **Elegance** comes from executing the vision well, not from complexity itself
