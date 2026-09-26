# Ruang Risiko IDX Design System: Stockbit Terminal Specification

## 1. Product Identity and Design Philosophy
Ruang Risiko IDX is professional Indonesian equity risk and decision research software.
Its user interface is modeled directly after the authoritative, high-density workflow familiar to Indonesian institutional analysts and Stockbit community traders.

### Core Philosophy
1. **Familiarity & Speed**: Traders instantly recognize Stockbit layout conventions (top running ticker tape, Chartbit canvas, 10-level orderbook depth, Bandarmology broker summary, and key statistics).
2. **Quantitative Rigor without Slop**: Beneath familiar retail visualizations lies an audit-grade statistical engine (GARCH volatility forecasting, Value at Risk, Machine Learning directional quantiles, Point-In-Time fundamentals, and Hard Veto rules).
3. **Web-Based Operational Sovereignty**: Every critical system action (data updates, model recalculation, risk tolerance tuning, and passport issuance) can be monitored and controlled directly through the browser.

---

## 2. Anti-Slop UX Mandates
- **Zero Generic AI Slop**: No purple-to-cyan decorative gradients, glowing border animations, or floating particles.
- **Zero Decorative Placeholders**: Every button, slider, and selector triggers an actual computation, config change, or audit log entry.
- **Zero Pseudo-Certainty**: Predictions are rendered strictly as quantile probability distributions (q10 to q90), never as deterministic price guarantees.
- **Zero Look-Ahead Bias**: Historical inspection and fundamental data enforce strict Point-In-Time reporting dates.
- **Zero Em Dash Policy**: No em dash characters (`\u2014`) anywhere across UI copy, labels, tooltips, or system documentation.

---

## 3. Design Tokens and Theme Architecture

### Color Palette (Stockbit Dark Theme)
| Token Name | Hex Code | Purpose |
| :--- | :--- | :--- |
| `color-bg-base` | `#131722` | Terminal deep charcoal background |
| `color-bg-surface` | `#1E222D` | Cards, panels, orderbook background, and sidebar |
| `color-border-subtle` | `#2A2E39` | Clean structural dividing borders |
| `color-accent-blue` | `#2962FF` | Stockbit brand blue for active states, links, and median paths |
| `color-idx-green` | `#00C076` | IDX bullish price movement, bid queue, ARA limit, net foreign buy |
| `color-idx-red` | `#FF4A68` | IDX bearish price movement, offer queue, ARB limit, net foreign sell |
| `color-warning-amber` | `#F59E0B` | Watch setups, event risks, moderate volatility warnings |
| `color-veto-crimson` | `#DC2626` | Hard veto triggers, tail risk breaches, circuit breaker limits |
| `color-text-primary` | `#F9FAFB` | Primary headings, asset prices, and critical figures |
| `color-text-secondary` | `#D1D4DC` | Standard body copy, table figures, and active labels |
| `color-text-muted` | `#787B86` | Micro captions, audit metadata, and inactive headers |

### Typography & Tabular Alignment
- **Sans-Serif System Font**: `-apple-system, BlinkMacSystemFont, "Segoe UI", Roboto, sans-serif` for clean legibility on Indonesian retail trader devices.
- **Monospace Tabular Font**: `SFMono-Regular, Consolas, "Liberation Mono", Menlo, monospace` for the 10-level orderbook, broker lots, prices, and timestamped audit logs to ensure strict vertical digit alignment.

---

## 4. Layout and Information Hierarchy

```
┌─────────────────────────────────────────────────────────────────────────────────┐
│ Ticker Tape: IHSG 7,812.35 (+0.42%) | LQ45 982.10 | USD/IDR 15,420 | Net Flow   │
├─────────────────────────────────────────────────────────────────────────────────┤
│ Header: BBCA.JK | Rp 10,250 (+0.49%) | ARA: Rp 12,300 | ARB: Rp 8,200 | [FAVORABLE]│
├─────────────────────────────────────────────────────────────────────────────────┤
│ Metrics: Prob Up: 58.4% | Median q50: Rp 10,280 | GARCH Vol: 1.5% | VaR 99: 4.0%│
├─────────────────────────────────────────────────────────────────────────────────┤
│ Sub-Navigation Tabs:                                                            │
│ [Chartbit & Book] [Bandarmology] [Key Stats] [Radar] [Passport] [Stream] [Console]│
│                                                                                 │
│ Active Workspace Panel (Dynamic Content Based on Selected Tab)                  │
└─────────────────────────────────────────────────────────────────────────────────┘
```

### Sub-Navigation Tab Specifications:
1. **Chartbit & Orderbook**:
   - Left Panel (70%): Interactive Candlestick Chart with SMA (20, 50, 200), Bollinger Bands, and Volume Bars.
   - Right Panel (30%): Official 10-Level IDX Market Depth Queue (Bid lots, Bid price, Offer price, Offer lots, Bid/Offer ratio, and ARA/ARB callouts).
   - Bottom Panel: Interactive Orderbook Slippage & Depth Simulator (test buying or selling specific IDR values with average fill price, slippage bps, ticks traversed, and liquidity cliff warnings).
2. **Bandarmology & Broker Summary**:
   - Stockbit-style broker transaction breakdown.
   - Top 5 Buyer brokers vs Top 5 Seller brokers with broker codes, investor type (Domestic / Foreign), lot volumes, and average execution prices.
   - Three-Tier Institutional Classification: Foreign Institutional, Domestic Institutional, and Retail Domestic net flow breakdown.
   - Smart Money Accumulation Index (SMAI) from 0% to 100%.
   - Automated Retail Trap Detection alert.
3. **Key Stats & Fundamental PIT**:
   - Comprehensive fundamental ratios (P/E, P/BV, ROE, Net Profit Margin, Debt-to-Equity, Dividend Yield).
   - Point-In-Time reporting period and publication date disclosure.
4. **Ruang Risiko Radar & Scenarios**:
   - Multi-horizon quantile fan (1D, 5D, 20D) showing q10, q25, q50, q75, and q90 paths.
   - 5-Scenario simulation engine with probability and invalidation levels.
5. **Pre-Buy Decision Passport**:
   - Clear GO / NO-GO research certificate with hard veto rationale.
   - Position sizing limits and one-click Markdown passport download.
6. **Stream & Narrative Intelligence**:
   - ICT market structure hypothesis breakdown (MSS, FVG, Liquidity Sweeps).
   - Rolling beta and correlation against IHSG.
   - Public analyst / creator claim validation ledger.
7. **Web Action Console**:
   - Real-time action triggers (Refresh market data, recalculate risk models, refit directional classifiers).
   - Universe Bandarmology Radar: One-click smart money scanning and ranking across all tickers.
   - Interactive runtime parameter adjustment sliders (VaR confidence level, max allocation %, slippage limit).
   - Chronological audit ledger displaying recent actions, operators, parameters, and durations.
   - Headless API & Webhook Service documentation for zero-RDC remote triggers.

---

## 5. Web Action Control Plane Architecture
To ensure complete system transparency and autonomy without requiring command-line or RDC logins:
- Every action initiated in the **Web Action Console** invokes the backend `actions.py` controller.
- The action generates a unique immutable `action_id` (e.g. `ACT-20260927-000500-1284`).
- The action executes asynchronously or with immediate UI feedback and logs its status (`SUCCESS` / `FAILED`), execution duration (ms), operator ID, and parameter diff to `reports/audit/action_ledger.json`.
- The live audit ledger is immediately rendered on-screen, providing operational observability directly within the browser.
- External webhook and CI/CD triggers interact with `src/ruang_risiko_idx/api.py` via HTTP POST, allowing complete headless operation.

---

## 6. Accessibility and Compliance (WCAG 2.2 AA)
- **Contrast**: All text tokens against `#131722` and `#1E222D` maintain a minimum contrast ratio of 4.5:1.
- **Focus Rings**: Keyboard navigation highlights interactive inputs with a 2px `#2962FF` outline.
- **Color Independence**: Status states combine color cues with explicit text badges (`FAVORABLE_SETUP`, `HIGH_RISK`, `WATCH`).
