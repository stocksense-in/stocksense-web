# StockSense — Design System ("Night Market")

## Product context
StockSense is stock research for Indian retail investors (NSE, ~2,600 stocks). Every stock gets a
0–100 score from six fundamentals (P/E, ROE, debt/equity, net margin, promoter holding, 3-yr revenue
growth), each judged against the healthy range for its own sector. Around that: dashboard (breadth,
sector moves, movers, top scores), screener, stock report pages (price chart, score breakdown,
report card, peers), IPO scores, geopolitics risk map, prospectus (DRHP) scanner, paper trading
with ₹1,00,000 virtual cash, investor profile → matched picks.

Users: first-time and early Indian investors (22–35) who want institutional-grade signals explained
in plain language. Job: "tell me if this stock is healthy for its sector, and why, in 10 seconds."

## Visual direction
A premium dark fintech terminal — the confidence of a trading desk, the warmth of Indian gold.
The previous version's dark + gold + green identity is the brand heritage the team loves; this
evolves it: deeper navy-black canvas, richer gold, vivid but controlled market colours, and colour
used to carry meaning (up/down, healthy/watch/concern, sectors) rather than decoration.
Not flat, not bland: layered surfaces, soft glows behind key numbers and charts, gradient strokes on
charts, coloured sector chips. Still disciplined: one glow per region, never neon everywhere.

## Color tokens
| Token | Hex | Use |
|---|---|---|
| bg | #070B14 | page background (deep navy-black) |
| bg-glow | radial #13233F → transparent | top-of-page ambient glow |
| surface | #0E1526 | panels/cards |
| surface-2 | #141D33 | raised elements, table header, inputs |
| surface-3 | #1B2640 | hover rows, selected items |
| border | rgba(148,163,209,0.12) | panel borders |
| border-strong | rgba(148,163,209,0.24) | inputs, focused/selected |
| text | #EEF2FA | primary text |
| text-2 | #A3AEC7 | secondary text |
| text-3 | #6B7794 | muted labels |
| gold (brand) | #F2B544 | primary actions, brand mark, score highlights, active nav |
| gold-soft | #F2B544 at 12% | gold washes, active nav background |
| up / healthy | #22D39A | gains, healthy status (mint green) |
| down / concern | #FF5D73 | losses, concern status (coral red) |
| watch | #F5A524 → use #FFB648 | in-between status (amber) — always with a word |
| info / chart | #5B8CFF | neutral chart series, links, info |
| violet | #9B7BFF | secondary data accent (sector chips, gradients with info) |
| cyan | #2FD3E8 | tertiary accent (sector chips) |

Gradients (sparingly): brand CTA `linear-gradient(135deg, #F7C25C, #E99A2C)`; chart area fill
`linear-gradient(to bottom, rgba(34,211,154,.28), transparent)` (or coral when down); hero ambient
glow `radial-gradient(60% 50% at 70% 0%, rgba(91,140,255,.18), transparent)` plus a gold glow.

## Typography
- Display/headings: Bricolage Grotesque 600–700, tight tracking (-0.02 to -0.035em).
- UI/body: IBM Plex Sans 400/500/600, 15px base.
- Numbers (prices, %, scores, tables): JetBrains Mono 500 with tabular figures — the terminal feel.
- No all-caps eyebrow labels; labels are sentence case, text-3 colour.

## Layout & components
- App shell: left sidebar (240px, surface with border-right), sticky top bar with search (⌘/ "/" hint)
  and an index ticker strip (NIFTY 50, SENSEX, BANK NIFTY, India VIX) with coloured changes.
- Panels: surface bg, 1px border, radius 14px, subtle inner top highlight (rgba(255,255,255,.04)).
- Buttons: primary = gold gradient with dark text (#1A1305); secondary = surface-2 with border;
  quiet = text-2. Radius 10px. Height 40px.
- Status badges: dot + word on a 12% tint of the status colour.
- Metric gauge: track surface-3, hatched ideal band in gold at 35% opacity, marker = status colour
  with a soft glow (0 0 12px status @60%).
- Score: big mono number, ring or bar coloured by band (weak <45 coral, fair 45–64 amber, strong 65+ mint).
- Tables: mono numbers right-aligned, coloured change column, hover row surface-3.
- Charts: 2px line in up/down colour, gradient area fill, gridlines border colour, crosshair.
- Sector chips use the categorical set: info, violet, cyan, gold, mint, coral (fixed order).

## Motion
One orchestrated moment per page (e.g. gauges sliding in on the hero report card, numbers counting
up once). Hover: 120ms colour/background transitions. Respect prefers-reduced-motion.

## Constraints
- Real data, Indian formatting (₹1,23,456.78, crore/lakh).
- Disclaimer: "For learning, not advice. StockSense is not a SEBI-registered investment adviser."
- Accessible contrast on dark (text ≥ 4.5:1); status never colour-only.
