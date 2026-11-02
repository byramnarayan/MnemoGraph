# Kit: UI/UX system (WeMakeDevs-inspired)

Technical-editorial look: hairline frames, dashed section dividers, mono eyebrows, one accent, sharp radii.

## Reuse in another project (Vite + React + Tailwind v4)
1. Copy `src/kit/` into the project.
2. In `src/index.css`, in this order:
   ```css
   @import url('https://fonts.googleapis.com/css2?family=Inter:wght@400;500;600;700&family=Geist+Mono:wght@400;500;600&display=swap');
   @import 'tailwindcss';
   @import './kit/kit.css';
   ```
3. `import { Section, Panel, Button, ... } from './kit'`. Call `useTheme()` once at the app root (adds `.dark` to `<html>`).

## Tokens (`kit.css`)
`background foreground card muted muted-foreground border accent accent-soft accent-foreground ok warn bad info`.
Re-theme by changing `--accent` in `:root` and `.dark`. Use as `bg-card`, `text-muted-foreground`, `border-border`, `text-accent`.
Fonts: `font-sans` (Inter), `font-mono` (Geist Mono).

## Principles
- Proof first: stats, sources and confidence next to every claim.
- One idea per numbered section: `<Section n="01" label="..." title="..."/>`.
- Mono for metadata (eyebrows, tags, ids, scores); sans for reading.
- Hairline borders over shadows. Radius is `rounded-sm` or smaller. Accent used sparingly for state and primary action.
- Colour never carries state alone: pair with a Tag label or icon glyph.
- Motion: `.rise` staggered entrance, `.beam` travelling line, 200ms colour transitions. All respect reduced motion.
- Interactive controls need real state, visible `:focus-visible`, and AA contrast.
- Responsive: grids collapse at ~1000px, tables scroll horizontally inside their panel.

## Components
Layout: `Frame Section Panel Header StickyBanner`  
Text/labels: `Eyebrow Tag Stat StatRow`  
Controls: `Button Segmented Field ThemeToggle`  
Data: `DataTable Meter Stepper CodeBlock`  
Feedback: `Callout EmptyState`  
Helpers: `scoreTone(v)` maps 0..1 to ok/warn/bad. `useTheme()`.  
CSS utilities: `.dashed-b .hatch .grid-bg .rise .beam .caret`.
