# SmartFuel Design System

## 1. Atmosphere & Identity
SmartFuel feels like a quiet fuel-cost command center: dense enough for card and station decisions, but calm enough that users can trust each number. The signature is silver-and-sky clarity: white panels, slate text, sky-blue actions, and amber caution for uncertain benefit data.

## 2. Color

### Palette
| Role | Token | Light | Dark | Usage |
|------|-------|-------|------|-------|
| Surface/primary | --white | #FFFFFF | #0F172A | Cards, modal surfaces |
| Surface/page | --slate-50 | #F8FAFC | #020617 | Page background |
| Surface/secondary | --slate-100 | #F1F5F9 | #1E293B | Empty states, secondary controls |
| Text/primary | --slate-900 | #0F172A | #F8FAFC | Main copy and headings |
| Text/secondary | --slate-600 | #475569 | #CBD5E1 | Supporting facts |
| Text/muted | --slate-500 | #64748B | #94A3B8 | Hints and metadata |
| Border/default | --slate-200 | #E2E8F0 | #334155 | Panels and dividers |
| Border/strong | --slate-300 | #CBD5E1 | #475569 | Form controls |
| Accent/primary | --primary | #0284C7 | #38BDF8 | Primary CTA, links, verified benefit headline |
| Accent/hover | --primary-hover | #0369A1 | #7DD3FC | Hover and pressed states |
| Accent/soft | --primary-light | #E0F2FE | #0C4A6E | Soft informational background |
| Status/warning | --accent | #F59E0B | #FBBF24 | Held or uncertain benefit state |
| Status/success | --naver-green | #03C75A | #4ADE80 | Confirmed external map/source actions |

### Rules
- Use sky-blue only for verified actions or links.
- Use amber caution for held, skipped, or unknown benefit states.
- Do not introduce raw colors in new UI; extend this table first.

## 3. Typography

### Scale
| Level | Size | Weight | Line Height | Tracking | Usage |
|-------|------|--------|-------------|----------|-------|
| H1 | 36px | 800 | 1.2 | -0.03em | Modal titles |
| H2 | 28px | 800 | 1.25 | -0.03em | Section headings |
| H3 | 22px | 800 | 1.35 | -0.02em | Card titles |
| Body | 16px | 400 | 1.6 | 0 | Default text |
| Body/sm | 14px | 400 | 1.5 | 0 | Secondary information |
| Caption | 12px | 700 | 1.4 | 0.04em | Eyebrows, labels |

### Font Stack
- Primary: Outfit, Inter, system-ui, -apple-system, sans-serif
- Mono: system monospace only when technical values require alignment

### Rules
- Benefit amounts use bold H1/H2 scale only when the value is verified.
- Held benefit copy uses body scale and caution tone to avoid false precision.

## 4. Spacing & Layout

### Base Unit
All spacing derives from 4px.

| Token | Value | Usage |
|-------|-------|-------|
| --space-1 | 4px | Icon-to-label |
| --space-2 | 8px | Tight inline gaps |
| --space-3 | 12px | Compact padding |
| --space-4 | 16px | Default form/control spacing |
| --space-5 | 20px | Panel internal rhythm |
| --space-6 | 24px | Card padding |
| --space-8 | 32px | Section separation |

### Grid
- Max content width: 1280px
- Modal and cards use responsive two-column layouts that collapse below tablet width.
- Breakpoints: mobile <= 760px, tablet <= 1024px, desktop > 1024px.

### Rules
- Keep form controls at least 44px tall.
- Place manual-entry controls directly below the uncertainty message.

## 5. Components

### Card catalog result
- Structure: image, issuer, name, status/action label.
- States: hover lift, focus ring, disabled only when loading.
- Accessibility: entire result is a button with card name as visible text.

### Catalog benefit detail
- Variants: verified benefit, held/manual-entry-required benefit.
- Spacing: 24px desktop, 18px mobile.
- States: verified shows numeric headline; held shows caution copy and opens manual entry by default.
- Accessibility: error text uses role=alert; status text uses role=status.

## 6. Motion & Interaction
- Micro: 100-150ms ease-out for button press.
- Standard: 200ms ease for panel and card hover states.
- Animate transform, opacity, filter only.
- Respect prefers-reduced-motion.

## 7. Depth & Surface
Strategy: mixed, but restrained.
- Cards use 1px slate borders with white surfaces.
- Primary actions may use the existing sky-tinted shadow.
- Warning panels use tonal background and border, not heavy shadow.
