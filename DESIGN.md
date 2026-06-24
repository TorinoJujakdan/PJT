# SmartFuel Design System

## Product feel

SmartFuel uses a fluorescent mint control-center style: trustworthy, calm, and data-driven. UI copy should make backend truth and user-visible outcomes match, especially for fuel prices, route costs, and card benefits.

## Tokens

- Primary: `#00796b`; hover: `#005f56`; neon surface: `#c6fff4`
- Secondary/neon: `#00ffcc`; warning/accent: `#f59e0b`
- Neutral scale: `--slate-50` through `--slate-900`; base surface: white
- Radius: 8px small, 12px medium, 16px large
- Shadows: use existing `--shadow-sm`, `--shadow-md`, `--shadow-lg`, and `--shadow-premium`

## Typography

- Font stack: Outfit, Inter, system UI, sans-serif
- Top-level title: 26px, 800 weight, tight negative tracking
- Section heading: about 22px, 800 weight
- Panel/card heading: about 18px, 800 weight
- Body and form controls: 13-14px, 600-700 weight where actionable
- Eyebrow labels: 11px, uppercase, 800 weight, primary color

## Layout and interaction

- Max app width: 1240px; shell padding: 32px desktop, responsive reduction on small screens
- Keep panels on white surfaces with subtle borders and fluorescent mint-tinted depth and neon CTA glow
- Use 4px-based spacing increments and preserve clear grouping between data, controls, and results
- Motion should be subtle: 0.2s ease for color, border, shadow, and transform; honor reduced motion

## Data-trust rules

- If a normalized backend value exists, the UI should display and submit that value rather than a placeholder fallback.
- User adjustments may override defaults, but copied catalog or saved-card defaults must remain traceable to the normalized benefit tier.
