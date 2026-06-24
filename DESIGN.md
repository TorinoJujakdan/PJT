# SmartFuel Design System: Silver & Sky Blue Spec

> **Goal**: Establish a unified, readable, and premium "Silver & Sky Blue Control-Center" aesthetic. This updates the previous mint-green theme to ensure high text contrast, resolve sidebar color discord, and eliminate low-visibility gradient backgrounds.

---

## 1. Brand Identity & Product Feel
- **Personality**: Professional, clean, reliable, and fluid.
- **Concept**: A high-tech vehicle console using clean metallic silvers combined with refreshing, active sky-blue accents.
- **Contrast Promise**: Never overlay light text on light gradients. Ensure all text meets the WCAG AA minimum contrast ratio of 4.5:1.

---

## 2. Color Palette & Tokens
All primary and secondary colors are refactored to Silver & Sky Blue, ensuring strong legibility on solid backgrounds.

```css
:root {
  /* Brand Sky Blue Accents */
  --primary: #0284c7;             /* Sky Blue / Cyan (Text, high-contrast states) */
  --primary-hover: #0369a1;       /* Deep Sky Blue for hover actions */
  --primary-light: #e0f2fe;       /* Very Soft Sky Blue Surface (Light background tint) */
  
  --secondary: #38bdf8;           /* Neon Sky Blue / Cyber Blue Accent (Active states, pulses) */
  --secondary-glow: rgba(56, 189, 248, 0.35); /* Glow effect for interactive elements */
  
  --accent: #f59e0b;              /* Orange (Warning, alerts, database fallback data) */
  
  /* Brand Naver Green for Map Redirections */
  --naver-green: #03c75a;         /* Naver Brand Green */
  --naver-green-hover: #02b34f;   /* Hover state Naver Green */
  
  /* Metallic Silver & Slate Neutrals */
  --slate-50: #f8fafc;            /* Base background */
  --slate-100: #f1f5f9;           /* Secondary background, soft silver */
  --slate-200: #e2e8f0;           /* Borders, separators */
  --slate-300: #cbd5e1;           /* Silver-gray separators / Muted text */
  --slate-400: #94a3b8;           /* Metal silver / Muted icons */
  --slate-500: #64748b;           /* Body helper text */
  --slate-600: #475569;           /* Secondary actions */
  --slate-700: #334155;           /* Primary text / Subheadings */
  --slate-900: #0f172a;           /* Headings, high-contrast panels */
  --white: #ffffff;
  
  /* Interactive Elements */
  --shadow-sm: 0 1px 3px rgba(0, 0, 0, 0.05);
  --shadow-md: 0 4px 6px -1px rgba(0, 0, 0, 0.05), 0 2px 4px -1px rgba(0, 0, 0, 0.03);
  --shadow-lg: 0 10px 25px -5px rgba(2, 132, 199, 0.08), 0 8px 10px -6px rgba(2, 132, 199, 0.08);
  --shadow-premium: 0 20px 40px -15px rgba(15, 23, 42, 0.08);
  --radius-lg: 16px;
  --radius-md: 12px;
  --radius-sm: 8px;
}
```

---

## 3. Map & Interface Component Rules

### A. Legibility Guarantee (No Low-Contrast Gradients)
- **Anti-pattern**: Light blue/green text over light-mint/sky gradients.
- **Rule**: Buttons like "길찾기" or "추천 받기" must use solid background fills with high-contrast text.
  - Primary button: Solid `--primary` (`#0284c7`) background with **solid white text** (`#ffffff`).
  - Active tags: Dark text on `--primary-light` surfaces.

### B. Harmonized Sidebar Menu (`iconSidebar`)
- **Anti-pattern**: Harsh dark backgrounds that clash with light content panels.
- **Rule**: The vertical sidebar menu (`iconSidebar`) must use a clean, metallic silver-gray background (`--slate-100` or `--slate-50` with a subtle right border) to blend seamlessly with the main content area, avoiding visual fatigue.
- **Active state**: Active tabs in the menu display a vertical highlight line using `--primary` and inherit a clean `--primary` icon color.

### C. Map Route Polyline
- **Stroke Color**: **`#0ea5e9`** (sharp, highly visible sky-blue on map canvases).
- **Properties**: `strokeColor: "#0ea5e9"`, `strokeOpacity: 0.9`, `strokeWeight: 6`.

### D. User Location Marker
- Inner dot: `--primary` (`#0284c7`) or `--secondary` (`#38bdf8`) with white border.
- Outer pulse: `--secondary-glow` (`rgba(56, 189, 248, 0.35)`).

### E. Naver Link Integration (길찾기)
- **Rule**: The Naver Maps direction redirection button must utilize the solid Naver Brand Green (`--naver-green`: `#03c75a`) with solid white text (`#ffffff`) to maximize both legibility and brand familiarity. Gradients are strictly forbidden for this element.

### F. Detail Card Borders
- **Rule**: Rounded panels (such as `.floatingDetailCard`) with high border-radius must not employ left-hand pseudo-element (`::before`) gradient border lines, as they cause boundary misalignment on rounded corners. Clean, solid thin border outlines (`1px solid rgba(226, 232, 240, 0.9)`) are to be used instead.

### G. Common Active Elements (Tabs, Badges, Actions)
- **Rule**: The active state of tab buttons (e.g. `.cardsTabs button.active`), representative badges (e.g. `.defaultBadge`), and primary actions (e.g. `.primaryAction`, `.cardPrimaryButton`) must not use 3D gradients. They should use a clean, solid `--primary` background with solid white (`#ffffff`) text, or `--primary-light` background with solid `--primary` text, adhering to flat and modern UI principles.

---

## 4. Typography Hierarchy
- **Font Stack**: `Outfit`, `Inter`, system UI, sans-serif.
- **Header Elements**: Bold weight, clean slate colors. Avoid colorful gradients for body typography to maintain accessibility.

---

## 5. Agent Hand-off Prompt Guide
When modifying styling sheets or Vue components:
1. Ensure all buttons use solid colors (either `--primary` or `--naver-green`) instead of multi-color gradients.
2. Remove the `::before` visual accent lines from card components that have rounded corners.
3. Clean up legacy gradient fills from tabs (`.cardsTabs button.active`), badges (`.defaultBadge`), and primary actions (`.primaryAction`, `.cardPrimaryButton`) to enforce a flat design.
