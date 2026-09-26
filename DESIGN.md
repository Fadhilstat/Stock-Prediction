# Ruang Risiko IDX Design System and Anti-Slop Specification

## 1. Product Identity
Ruang Risiko IDX is professional financial research software tailored specifically for the Indonesian equity market (Bursa Efek Indonesia / IDX).
The visual tone is sober, analytical, authoritative, and data-dense.
If the logo and title are removed, the software must still immediately be recognized as an Indonesian equity risk and probabilistic research terminal.

## 2. Anti-Slop UX Mandates
- No generic AI gradients (no purple to cyan, no blue to magenta, no rainbow accents).
- No decorative background grids, glowing borders, or arbitrary geometric floating blobs.
- No excessive glassmorphism or translucent card layering that degrades contrast.
- No pill-shaped containers for serious financial tabular metrics.
- No repetitive card walls where a structured tabular view is more readable.
- No generic AI icons (sparkles, magic wands, robots, crystal balls).
- No unsupported or hyperbolic performance claims, fake win rates, or pseudo-deterministic buy targets.
- No dead buttons, fake filter toggles, or decorative non-functional controls.
- No missing loading, empty, or error states.
- No em dash characters anywhere in UI copy, labels, tooltips, or documentation.

## 3. Typography Reasoning
- Primary interface font: Clean system sans-serif (Inter, -apple-system, BlinkMacSystemFont, Segoe UI, Roboto) for maximum legibility on low-resolution displays.
- Numerical and code font: Monospace with tabular figures (JetBrains Mono, SF Mono, Consolas) to ensure numbers align vertically in tables and financial metric panels.
- Font scale hierarchy:
  - Title: 24px bold (reserved for primary screen heading)
  - Section Header: 18px semibold
  - Subheader / Group Label: 14px semibold uppercase with letter-spacing
  - Body Text: 14px regular (line-height: 1.5)
  - Secondary / Caption: 12px regular
  - Micro / Audit Metadata: 11px monospace

## 4. Palette and Financial Semantics
- Neutral Dark Palette:
  - Background Base: `#0B0F19` (Deep slate navy, reducing eye strain during extended market research)
  - Surface Card / Panel: `#111827` (Subtle elevation)
  - Surface Border: `#1F2937` (1px clean border)
  - High Contrast Text: `#F9FAFB`
  - Secondary Text: `#9CA3AF`
  - Tertiary / Muted Text: `#6B7280`
- Financial Status Semantics:
  - Bullish / Positive Return: `#10B981` (Emerald green, avoiding oversaturated neon)
  - Bearish / Negative Return: `#EF4444` (Ruby red, distinct from warning orange)
  - Neutral / Unchanged: `#94A3B8` (Slate gray)
  - High Risk / Hard Veto: `#DC2626` (Intense crimson alert)
  - Warning / Moderate Risk / Event Imminent: `#F59E0B` (Amber gold)
  - Information / Calibration Note: `#3B82F6` (Muted sapphire)

## 5. Forecast and Uncertainty Semantics
- Median Path (q50): Solid crisp line indicating the statistical median expectation.
- Interquartile Range (q25 to q75): Moderate opacity fan fill indicating typical outcome dispersion.
- Tail Range (q10 to q90): Low opacity fan fill showing tail uncertainty.
- Invalidation Levels: Crisp dashed horizontal reference lines with price callouts.
- Rule: A wider fan visually signifies higher uncertainty, never false certainty.

## 6. Information Hierarchy and Analytical Density
- Information is organized logically:
  1. Context Bar: Selected ticker, current price, data cutoff date, provider freshness, trust score.
  2. Primary Action / Decision Passport: Current decision state (FAVORABLE_SETUP, WATCH, WAIT, AVOID, HIGH_RISK), risk veto status, and summary metrics.
  3. Interactive Chart & Day Inspector: Candlestick price action, volume, and synchronized historical evidence panel.
  4. Probabilistic Forecast & Calibration: Multi-horizon quantile fan (1D, 5D, 20D), expected return, and calibration reliability metrics.
  5. Multi-Layer Research Panels: Technical features, ICT hypotheses, fundamental metrics, corporate actions, and IHSG/sector alignment.
  6. Flow & Social Evidence: Foreign flow persistence, broker concentration proxies, creator claim ledger, and social narrative acceleration.
  7. Governance & Audit: Prediction Journal, paper trade ledger, walk-forward stats, and model registry.

## 7. Responsive and Touch Strategy
- Supported viewports: 360px, 412px, 768px, 1024px, 1440px.
- Touch target sizes: Minimum 44px by 44px for touchable buttons, selectors, and tabs.
- Layout flow: Desktop uses multi-column linked analytical panels; mobile collapses into stacked, logically ordered sections without page-level horizontal overflow.

## 8. Accessibility Principles (WCAG 2.2 AA)
- Contrast ratio: Minimum 4.5:1 for normal text and 3.0:1 for large headers or graphical components against backgrounds.
- Focus indicators: 2px solid `#3B82F6` outline with 2px offset on all interactive keyboard elements.
- Semantic HTML: Proper header nesting (h1, h2, h3), semantic tables with headers, and aria-labels for chart controls.
- Keyboard navigation: Full Tab order traversal, Enter and Space activation, Escape dismissal for modals and flyouts.
