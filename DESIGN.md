# ⚽ ApexOdds Europe — Complete Website Design Specification

> **Purpose:** This document provides a complete design blueprint of the ApexOdds Europe sports betting analytics platform. Use it as a reference for UI/UX redesign, prototyping in Google Sites, Figma, or any design tool.

---

## Table of Contents

1. [Product Overview](#1-product-overview)
2. [Site Map & Information Architecture](#2-site-map--information-architecture)
3. [Design Tokens & Brand Identity](#3-design-tokens--brand-identity)
4. [Layout System & Grid](#4-layout-system--grid)
5. [Page-by-Page Wireframes](#5-page-by-page-wireframes)
6. [Component Library](#6-component-library)
7. [Data Visualizations](#7-data-visualizations)
8. [User Flows & Interactions](#8-user-flows--interactions)
9. [Responsive Behavior](#9-responsive-behavior)
10. [Accessibility Notes](#10-accessibility-notes)

---

## 1. Product Overview

**ApexOdds Europe** is a premium sports betting analytics dashboard that covers the top 6 European football leagues and the UEFA Champions League. It provides real-time odds analysis, value bet detection, arbitrage scanning, and betting calculators — all through an interactive web interface.

### Target Users

- Sports bettors seeking data-driven insights
- Odds analysts and tipsters
- Sportsbook enthusiasts tracking line movements

### Core Value Proposition

- **Live odds** from 30+ bookmakers across 4 regions (US, UK, EU, AU)
- **Mathematical edge detection** — value bets, arbitrage, margin analysis
- **Interactive calculators** — parlays, Kelly Criterion, dutching, odds conversion
- **Premium dark UI** inspired by DraftKings, FanDuel, and Bet365

---

## 2. Site Map & Information Architecture

```
ApexOdds Europe
│
├── 🔲 HEADER (Hero Banner)
│   └── App Title + Tagline ("Premium Analytics · Real-Time Odds · Smart Calculators")
│
├── 📊 SUMMARY METRICS BAR (4 clickable KPI cards)
│   ├── 📅 Upcoming Matches (count) → links to Matches tab
│   ├── 💡 Value Bets (count) → links to Value Bets tab
│   ├── 🔄 Arb Opportunities (count) → links to Arbitrage tab
│   └── 🏦 Bookmakers (count) → links to Margins tab
│
├── 🏗️ THREE-PANE LAYOUT
│   │
│   ├── LEFT PANEL — Navigation (ratio: 2/10)
│   │   ├── 📅 Matches
│   │   ├── 💡 Value Bets
│   │   ├── 🔄 Arbitrage
│   │   ├── 📈 Movement
│   │   ├── 📊 Margins
│   │   ├── 🧮 Bet Calculator
│   │   └── 🎯 Custom Parlay
│   │
│   ├── CENTER PANEL — Main Content (ratio: 5/10)
│   │   ├── [Page: Matches] — Upcoming match cards with best odds
│   │   ├── [Page: Value Bets] — Value bet alerts + edge histogram
│   │   ├── [Page: Arbitrage] — Arb opportunity alerts + CSV export
│   │   ├── [Page: Movement] — Line movement charts (historical)
│   │   ├── [Page: Margins] — Bookmaker vig bar chart + table
│   │   ├── [Page: Bet Calculator] — Bet builder + 5 calculator tools
│   │   └── [Page: Custom Parlay] — Multi-leg parlay builder
│   │
│   └── RIGHT PANEL — Bet Slip (ratio: 3/10)
│       ├── Bet Builder Selections
│       ├── Custom Parlay Legs
│       ├── Live Payout Calculator
│       └── Clear All Button
│
├── ⚙️ SIDEBAR (Left Drawer)
│   ├── 🔲 Brand Logo ("APEXODDS EUROPE")
│   ├── ⚙️ Settings Title
│   ├── 🏆 League Multi-Select (6 leagues + UCL)
│   ├── 🔄 Refresh Data Button
│   ├── 🔑 API Key Override (password field)
│   └── 🕐 Last Refreshed Timestamp
│
└── 🔲 FOOTER
    └── "⚽ ApexOdds Europe · Built with Streamlit · Premium Sports Analytics"
```

---

## 3. Design Tokens & Brand Identity

### 3.1 Color Palette

| Token Name             | Hex Code    | Usage                                      |
|------------------------|-------------|---------------------------------------------|
| `--bg-primary`         | `#0D1B2A`   | Page background, chart backgrounds          |
| `--bg-secondary`       | `#1a2332`   | Sidebar, card backgrounds                   |
| `--bg-card`            | `rgba(20, 23, 32, 0.85)` | Match cards, nav panel            |
| `--bg-glass`           | `rgba(13, 27, 42, 0.55)` | Glassmorphism overlays            |
| `--bg-overlay`         | `rgba(5, 10, 20, 0.88)`  | Full-screen dark overlay          |
| `--accent-green`       | `#00C853`   | Primary accent, CTA buttons, active states  |
| `--accent-green-light` | `#00E676`   | Gradients, profit indicators                |
| `--accent-green-soft`  | `#69F0AE`   | Hover states                                |
| `--accent-gold`        | `#FFD700`   | Odds values, parlay highlights, profit      |
| `--accent-gold-dark`   | `#FFC107`   | Secondary gold for gradients                |
| `--accent-cyan`        | `#40C4FF`   | American odds, tertiary info                |
| `--accent-red`         | `#FF6B6B`   | Declining odds, alerts, remove actions      |
| `--accent-orange`      | `#FF6B35`   | Chart colorway element                      |
| `--accent-purple`      | `#E040FB`   | Chart colorway element                      |
| `--text-primary`       | `#E8EAED`   | Primary body text                           |
| `--text-muted`         | `#8899AA`   | Labels, captions, secondary text            |
| `--text-subtle`        | `#556677`   | Footer text                                 |
| `--text-label`         | `#A0AEC0`   | Parlay labels                               |
| `--border-subtle`      | `rgba(255, 255, 255, 0.08)` | Card borders, dividers       |
| `--border-green`       | `rgba(0, 200, 83, 0.15)` | Active/hover borders            |
| `--grid-line`          | `rgba(0, 200, 83, 0.08)` | Chart grid lines                |

### 3.2 Typography

| Element            | Font Family                                         | Size      | Weight | Extras                     |
|--------------------|------------------------------------------------------|-----------|--------|----------------------------|
| Body / Default     | Inter, -apple-system, BlinkMacSystemFont, Segoe UI  | —         | 400    | sans-serif stack           |
| Hero Title         | Same stack                                           | 1.65rem   | 800    | Text shadow, gradient text |
| Hero Subtitle      | Same stack                                           | 0.82rem   | 500    | Letter-spacing: 0.03em    |
| Section Header     | Same stack                                           | —         | —      | Green left border          |
| Nav Item           | Same stack                                           | 0.82rem   | 600    | uppercase                  |
| Match Team Name    | Same stack                                           | 0.95rem   | 700    | Text shadow                |
| Odds Value         | Same stack                                           | 1.05rem   | 800    | Gold (#FFD700)             |
| Stat Value         | Same stack                                           | 1.35rem   | 800    | Gradient text              |
| Metric Value       | Same stack                                           | 1.5rem    | 800    | Green gradient text        |
| Badge / Label      | Same stack                                           | 0.65rem   | 700    | UPPERCASE, 0.1em spacing   |
| Muted Text         | Same stack                                           | 0.7-0.78rem | 500–600 | Color: #8899AA           |
| Footer             | Same stack                                           | 0.72rem   | 400    | Color: #556677             |

### 3.3 Effects & Treatments

| Effect             | CSS Value                                                     | Used On                          |
|--------------------|---------------------------------------------------------------|----------------------------------|
| Glassmorphism      | `backdrop-filter: blur(12–24px); background: rgba(…, 0.5–0.9)` | Cards, panels, sidebar         |
| Box Shadow (card)  | `0 8px 32px rgba(0,0,0,0.3)`                                 | Match cards, stat panels         |
| Box Shadow (glow)  | `0 0 20px rgba(0,200,83,0.4)`                                | Active nav, CTA buttons          |
| Gold Shadow        | `0 2px 8px rgba(255,215,0,0.3)`                              | Odds badges, parlay badges       |
| Gradient (primary) | `linear-gradient(135deg, #00C853, #00E676)`                  | Buttons, active nav, VS badge    |
| Gradient (gold)    | `linear-gradient(135deg, #FFD700, #FFC107)`                  | Odds badges, parlay highlights   |
| Gradient (text)    | `linear-gradient(90deg, #00C853, #00E676, #40C4FF)`          | Metric values, stat values       |
| Top Accent Line    | `linear-gradient(90deg, #00C853, #FFD700, #00E676)` (3px)    | Hero header top border           |
| Hover Lift         | `transform: translateY(-2px to -3px)`                        | Cards, buttons                   |
| Pulse Animation    | `@keyframes pulse-green / pulse-gold` (2s ease-in-out)       | Value/Arb alert badges           |
| Transition         | `all 0.2s ease` / `all 0.25s ease`                           | All interactive elements         |
| Border Radius      | 6px–20px (scale: 6, 8, 10, 12, 14, 16, 20)                  | Various components               |

### 3.4 Background

- **Full-screen background image** — Stadium photo with dark overlay
  - Image: Football stadium (unsplash, 1920px wide)
  - Overlay: `rgba(5, 10, 20, 0.88)` — near-black with slight blue
  - Header: `rgba(5, 10, 20, 0.7)` with `blur(16px)`

### 3.5 Iconography

All icons are emoji-based (no external icon library required):

| Icon | Usage                  | Context              |
|------|------------------------|----------------------|
| ⚽   | App logo, match cards  | Brand, sports        |
| 📅   | Matches tab            | Navigation           |
| 💡   | Value Bets tab         | Navigation, KPI      |
| 🔄   | Arbitrage tab, refresh | Navigation, actions  |
| 📈   | Movement tab           | Navigation           |
| 📊   | Margins tab            | Navigation           |
| 🧮   | Bet Calculator tab     | Navigation           |
| 🎯   | Custom Parlay tab      | Navigation, summary  |
| ⚙️   | Settings               | Sidebar              |
| 🔑   | API Key                | Sidebar              |
| 🕐   | Last refreshed         | Sidebar, kickoff     |
| 🏦   | Bookmakers             | KPI card             |
| 🎫   | Bet Slip               | Right panel          |
| 💰   | Profit indicator       | Arbitrage badges     |
| 🗑️   | Clear / Remove         | Actions              |
| 🗒️   | Bet Slip list          | Bet slip             |
| ▲/▼  | Odds movement          | Match cards          |

---

## 4. Layout System & Grid

### 4.1 Overall Page Structure (Top to Bottom)

```
┌───────────────────────────────────────────────────────────────┐
│ [SIDEBAR DRAWER]              MAIN VIEWPORT                   │
│ ┌─────────────┐  ┌───────────────────────────────────────┐   │
│ │ Brand Logo  │  │          HERO HEADER BANNER            │   │
│ │ ─────────── │  ├───────────────────────────────────────┤   │
│ │ Settings    │  │  KPI-1  │  KPI-2  │  KPI-3  │  KPI-4 │   │
│ │ League      │  ├─────────┴─────────┴─────────┴─────────┤   │
│ │ Multi-      │  │                                        │   │
│ │ Select      │  │  NAV    │    MAIN CONTENT   │  BET    │   │
│ │             │  │  PANEL  │    AREA            │  SLIP   │   │
│ │ [Refresh]   │  │  (2/10) │    (5/10)          │  (3/10) │   │
│ │ ─────────── │  │         │                    │         │   │
│ │ API Key     │  │  📅     │  [Active Page      │  🎫     │   │
│ │ Override    │  │  💡     │   Content           │  Slip   │   │
│ │             │  │  🔄     │   Renders Here]     │  Items  │   │
│ │ Last        │  │  📈     │                    │  Payout  │   │
│ │ Refreshed   │  │  📊     │                    │  Clear   │   │
│ │             │  │  🧮     │                    │         │   │
│ └─────────────┘  │  🎯     │                    │         │   │
│                  ├─────────┴────────────────────┴─────────┤   │
│                  │              FOOTER                     │   │
│                  └────────────────────────────────────────┘   │
└───────────────────────────────────────────────────────────────┘
```

### 4.2 Column Ratios

| Section               | Ratio | Description                                |
|-----------------------|-------|--------------------------------------------|
| Navigation Panel      | 2/10  | Vertical navigation buttons                |
| Main Content Area     | 5/10  | Active page renders here                   |
| Bet Slip Panel        | 3/10  | Persistent bet slip with live calculations |

### 4.3 Summary Metrics Bar

- 4 equal columns (`st.columns(4)`)
- Each column: Glassmorphism metric card + action button below

### 4.4 Spacing

| Token             | Value       | Usage                              |
|-------------------|-------------|------------------------------------|
| Page top padding  | 1rem        | Above hero header                  |
| Card margin       | 0.85rem     | Between match cards                |
| Card padding      | 0.9rem–1.3rem | Card interior spacing            |
| Section gap       | 0.8rem      | Between main sections              |
| Nav item margin   | 0.3rem      | Between navigation buttons         |
| Footer margin-top | 2rem        | Space above footer                 |

---

## 5. Page-by-Page Wireframes

### 5.1 📅 Matches Page

```
┌─────────────────────────────────────────┐
│ [Subheader] Upcoming Matches            │
│                                         │
│ [Search Box] 🔍 Search by team name…    │
│                                         │
│ [Count Badge] "23 matches found"        │
│                                         │
│ ┌─ Column 1 ──────┐ ┌─ Column 2 ──────┐│
│ │ ┌──────────────┐ │ │ ┌──────────────┐││
│ │ │ ⚽ EPL       │ │ │ │ ⚽ LA LIGA   │││
│ │ │              │ │ │ │              │││
│ │ │ Arsenal      │ │ │ │ Barcelona    │││
│ │ │   [VS]       │ │ │ │   [VS]       │││
│ │ │ Chelsea      │ │ │ │ Real Madrid  │││
│ │ │              │ │ │ │              │││
│ │ │ 🕐 Mar 15   │ │ │ │ 🕐 Mar 16   │││
│ │ │──────────────│ │ │ │──────────────│││
│ │ │ HOME│DRAW│AWAY│ │ │ │ HOME│DRAW│AWAY│││
│ │ │ 2.10│3.25│3.50│ │ │ │ 1.85│3.60│4.20│││
│ │ └──────────────┘ │ │ └──────────────┘││
│ │ ┌──────────────┐ │ │ ┌──────────────┐││
│ │ │  Next card…  │ │ │ │  Next card…  │││
│ │ └──────────────┘ │ │ └──────────────┘││
│ └──────────────────┘ └──────────────────┘│
└─────────────────────────────────────────┘
```

**Components used:** Search input, Count badge, Match cards (2-column grid)

**Match Card Structure:**
1. **Card Top:** League badge → Team names with VS separator → Kickoff time
2. **Odds Row:** 3 odds buttons (Home | Draw | Away) with gold prices
3. **Movement indicators:** ▲ green (price > 2.0) / ▼ red (price < 1.8)

### 5.2 💡 Value Bets Page

```
┌─────────────────────────────────────────┐
│ [Subheader] Value Bets                  │
│                                         │
│ [Slider] Edge threshold: ──○── 5%       │
│                                         │
│ [Count Badge] "7 value bets found"      │
│ [CSV Download Button]                   │
│                                         │
│ ┌───────────────────────────────────────┐│
│ │ ⚽ Arsenal vs Chelsea                 ││
│ │             [+8.3% EDGE] (pulsing)    ││
│ │ Home @ 2.10 (+110) via Pinnacle       ││
│ └───────────────────────────────────────┘│
│ ┌───────────────────────────────────────┐│
│ │ ⚽ Barcelona vs Real Madrid           ││
│ │             [+5.7% EDGE] (pulsing)    ││
│ │ Away @ 4.20 (+320) via Bet365         ││
│ └───────────────────────────────────────┘│
│                                         │
│ [Expander] 📊 Edge Distribution Chart   │
│ ┌───────────────────────────────────────┐│
│ │      Plotly Histogram                 ││
│ │      (x: Edge %, y: Count)            ││
│ └───────────────────────────────────────┘│
└─────────────────────────────────────────┘
```

**Components used:** Slider (threshold), Count badge, Value alert cards, CSV download, Plotly histogram

**Value Card Structure:**
1. **Header Row:** Match name (left) + Pulsing green "+X.X% EDGE" badge (right)
2. **Detail Row:** Outcome @ decimal odds (American odds in cyan) via bookmaker

### 5.3 🔄 Arbitrage Page

```
┌─────────────────────────────────────────┐
│ [Subheader] Arbitrage Opportunities     │
│                                         │
│ [Count Badge] "2 arb opportunities"     │
│ [CSV Download Button]                   │
│                                         │
│ ┌───────────────────────────────────────┐│
│ │ 🔄 Arsenal vs Chelsea                ││
│ │           [💰 1.230% PROFIT] (pulse)  ││
│ │ Market: h2h                           ││
│ │ Home: 2.15 · Draw: 3.40 · Away: 3.80 ││
│ └───────────────────────────────────────┘│
│ ┌───────────────────────────────────────┐│
│ │ 🔄 Juventus vs AC Milan              ││
│ │           [💰 0.890% PROFIT] (pulse)  ││
│ │ Market: h2h                           ││
│ │ Home: 2.30 · Draw: 3.25 · Away: 3.10 ││
│ └───────────────────────────────────────┘│
│                                         │
│ [Empty state if none found]             │
│ "🔄 No arbitrage opportunities…"        │
└─────────────────────────────────────────┘
```

**Components used:** Count badge, Arbitrage alert cards, CSV download

**Arb Card Structure:**
1. **Header Row:** Match name (left) + Pulsing gold "💰 X.XXX% PROFIT" badge (right)
2. **Detail Row:** Market label + best odds per outcome (bold values, dot-separated)

### 5.4 📈 Odds Movement Page

```
┌─────────────────────────────────────────┐
│ [Subheader] Odds Movement               │
│                                         │
│ [Selectbox] Choose a match:             │
│ ┌─────────────────────────────────┐     │
│ │ Arsenal vs Chelsea              │ ▼   │
│ └─────────────────────────────────┘     │
│                                         │
│ ┌───────────────────────────────────────┐│
│ │                                       ││
│ │        Plotly Line Chart              ││
│ │                                       ││
│ │  Y-axis: Decimal Price                ││
│ │  X-axis: Timestamp                    ││
│ │  Lines: One per bookmaker             ││
│ │  Colors: Green/Gold/Cyan/Orange       ││
│ │                                       ││
│ │  Dark background (#0D1B2A)            ││
│ │  Green grid lines                     ││
│ │                                       ││
│ └───────────────────────────────────────┘│
│                                         │
│ [Empty state if no history]             │
│ "📈 No line-movement data yet."         │
└─────────────────────────────────────────┘
```

**Components used:** Selectbox (match picker), Plotly interactive line chart

**Chart Specification:**
- Type: Multi-line time series
- Y-axis: Decimal odds price
- X-axis: Timestamp
- Lines: One per bookmaker (color-coded)
- Dark theme with green-tinted grid
- Hover tooltip: Bookmaker, price, time

### 5.5 📊 Margins Page

```
┌─────────────────────────────────────────┐
│ [Subheader] Bookmaker Margin Analysis   │
│                                         │
│ ┌───────────────────────────────────────┐│
│ │                                       ││
│ │        Plotly Horizontal Bar Chart    ││
│ │                                       ││
│ │  Y-axis: Bookmaker names              ││
│ │  X-axis: Average margin %             ││
│ │  Color: RdYlGn_r scale               ││
│ │  (Green = low margin = good)          ││
│ │                                       ││
│ │  Sorted: Lowest margin first          ││
│ │                                       ││
│ └───────────────────────────────────────┘│
│                                         │
│ [Expander] Margin Detail Table          │
│ ┌───────────────────────────────────────┐│
│ │  Bookmaker   │ Avg Margin │ # Markets ││
│ │──────────────│────────────│───────────││
│ │  Pinnacle    │   2.3%     │    42     ││
│ │  Betfair     │   2.8%     │    38     ││
│ │  Bet365      │   4.1%     │    45     ││
│ │  …           │   …        │    …      ││
│ └───────────────────────────────────────┘│
│                                         │
│ [Empty state if no data]                │
│ "📊 Load odds data first."              │
└─────────────────────────────────────────┘
```

**Components used:** Plotly horizontal bar chart (color-scaled), Sortable data table in expander

### 5.6 🧮 Bet Calculator Page

This page has two modes: **Bet Builder** and **Calculator Tools**.

```
┌─────────────────────────────────────────┐
│ [Subheader] 🧮 Bet Calculator           │
│                                         │
│ [Radio Toggle]                          │
│ ( Bet Builder ) ( Calculator Tools )    │
│                                         │
│ ═══════════════════════════════════════  │
│                                         │
│ [IF Bet Builder MODE]:                  │
│                                         │
│ #### Add a Selection                    │
│ [Selectbox] Choose a match              │
│ [Selectbox] Choose outcome              │
│ [Button] ➕ Add to Slip                 │
│                                         │
│ #### 🗒️ Your Bet Slip                  │
│ ┌───────────────────────────────────┐   │
│ │ Arsenal vs Chelsea                │   │
│ │ Home                    [2.10]    │   │
│ ├───────────────────────────────────┤   │
│ │ Barcelona vs R. Madrid            │   │
│ │ Away                    [4.20]    │   │
│ └───────────────────────────────────┘   │
│ [Radio] ( Single Bets ) ( Accumulator ) │
│ [Number Input] Stake: $10.00            │
│ [Button] 💰 Calculate                   │
│ [Button] 🗑️ Clear Slip                 │
│                                         │
│ ##### Results                           │
│ Combined Odds: 8.82                     │
│ Payout: $88.20 | Profit: $78.20         │
│                                         │
│ ═══════════════════════════════════════  │
│                                         │
│ [IF Calculator Tools MODE]:             │
│                                         │
│ [Radio Toggle]                          │
│ (Single)(Acca)(Converter)(Kelly)(Dutch) │
│                                         │
│ [Active Sub-Calculator renders below]   │
│                                         │
└─────────────────────────────────────────┘
```

#### Sub-Calculators (Calculator Tools Mode)

**Single Bet Payout:**
- Inputs: Stake ($), Decimal Odds
- Output: Payout, Profit, Implied Probability metrics

**Accumulator/Parlay:**
- Inputs: Number of legs (1–20), Decimal odds per leg, Stake
- Output: Combined Odds, Payout, Profit, Implied Probability

**Odds Converter:**
- Input: One odds format value
- Radio toggle: Decimal / American / Fractional
- Output: All three formats displayed

**Kelly Criterion:**
- Inputs: Decimal Odds, Estimated Win Probability (%), Bankroll ($)
- Output: Kelly Fraction (%), Recommended Stake ($)

**Dutching Calculator:**
- Inputs: Number of selections, Odds per selection, Total Stake
- Output: Stake per selection, Equal profit amount

### 5.7 🎯 Custom Parlay Page

```
┌─────────────────────────────────────────┐
│ [Subheader] 🎯 Custom Parlay Builder    │
│                                         │
│ ┌─ Parlay Summary Banner ──────────────┐│
│ │ ═══ gold gradient top line ═══       ││
│ │ 🎯 PARLAY SUMMARY                   ││
│ │                                      ││
│ │ Legs    Combined   Payout   Profit   ││
│ │  3      8.82x     $88.20   $78.20   ││
│ │         (gold)    (gold)   (green)   ││
│ └──────────────────────────────────────┘│
│                                         │
│ ┌─ Parlay Leg Cards ───────────────────┐│
│ │ ① Arsenal ML              [2.10]    ││
│ │   Implied: 47.6%                     ││
│ ├──────────────────────────────────────┤│
│ │ ② Barcelona Over 2.5      [1.85]    ││
│ │   Implied: 54.1%                     ││
│ ├──────────────────────────────────────┤│
│ │ ③ Juventus Draw            [3.25]    ││
│ │   Implied: 30.8%                     ││
│ └──────────────────────────────────────┘│
│                                         │
│ #### Add a Leg                          │
│ [Text Input] Selection label            │
│ [Number Input] Decimal odds             │
│ [Button] ➕ Add Leg                     │
│                                         │
│ [Number Input] Stake: $10.00            │
│ [Radio] (Full Parlay)(Round Robin)(Singles)│
│ [Button] 💰 Calculate Parlay            │
│ [Button] 🗑️ Clear All Legs             │
│                                         │
│ ┌─ Payout Box ─────────────────────────┐│
│ │        POTENTIAL PAYOUT              ││
│ │          $88.20                       ││
│ │        (large green text)             ││
│ └──────────────────────────────────────┘│
└─────────────────────────────────────────┘
```

**Components used:** Parlay summary banner, Parlay leg cards, Text/number inputs, Radio toggle, Payout box

---

## 6. Component Library

### 6.1 Match Card

```
┌─────────────────────────────────────┐
│ ⚽ ENGLISH PREMIER LEAGUE (badge)   │  ← League badge (green pill)
│                                     │
│ Arsenal        [VS]        Chelsea  │  ← Team names + green VS badge
│                                     │
│ 🕐 2026-03-15 15:00 UTC             │  ← Kickoff time
│─────────────────────────────────────│
│  HOME    │   DRAW    │   AWAY       │  ← Odds row (dark bg)
│  2.10 ▲  │   3.25    │   3.50 ▼     │  ← Gold odds + movement
└─────────────────────────────────────┘
```

- **Background:** `rgba(20, 23, 32, 0.85)` with `blur(12px)`
- **Border:** `1px solid rgba(255,255,255,0.08)`, radius `16px`
- **Hover:** Lift `translateY(-3px)`, green glow border
- **Odds row:** Dark overlay `rgba(0,0,0,0.15)`, separated by top border

### 6.2 Stat Panel (KPI)

```
┌───────────────────────┐
│    UPCOMING MATCHES    │  ← Label: 0.65rem, uppercase, muted
│         23             │  ← Value: 1.35rem, gradient text
└───────────────────────┘
```

- **Background:** Glass `rgba(13,27,42,0.5)` with `blur(20px)`
- **Border:** Subtle, radius `14px`

### 6.3 Metric Card (Streamlit Native)

```
┌───────────────────────┐
│  📅 UPCOMING MATCHES   │  ← Label: 0.72rem, uppercase, muted
│  23                    │  ← Value: 1.5rem, gradient text
│  [→ View Matches]      │  ← Action button
└───────────────────────┘
```

- **Background:** Glass `rgba(13,27,42,0.55)` with `blur(20px)`
- **Border:** Subtle, radius `14px`
- **Shadow:** `0 8px 32px rgba(0,0,0,0.3)`

### 6.4 Value Bet Alert Card

```
┌─────────────────────────────────────────┐
│ ⚽ Arsenal vs Chelsea    [+8.3% EDGE]   │  ← Header: teams + pulsing badge
│ Home @ 2.10 (+110) via Pinnacle         │  ← Detail: outcome, odds, bookmaker
└─────────────────────────────────────────┘
```

- **Badge:** Green pill, pulsing green glow animation (2s cycle)
- **Background:** Glass, radius `14px`
- **Hover:** Lift `translateY(-2px)`

### 6.5 Arbitrage Alert Card

```
┌─────────────────────────────────────────┐
│ 🔄 Arsenal vs Chelsea  [💰 1.23% PROFIT]│  ← Header: teams + pulsing gold badge
│ Market: h2h                              │  ← Detail line 1
│ Home: 2.15 · Draw: 3.40 · Away: 3.80    │  ← Detail line 2 (bold values)
└─────────────────────────────────────────┘
```

- **Badge:** Gold pill, pulsing gold glow animation (2s cycle)

### 6.6 Bet Slip Card

```
┌───────────────────────────────────┐
│ │ Arsenal vs Chelsea     [2.10]   │  ← Green left border accent
│ │ Home                            │  ← Outcome name
└───────────────────────────────────┘
```

- **Left border:** 4px solid `#00C853`
- **Odds badge:** Gold gradient `#FFD700→#FFC107`, dark text
- **Hover:** Slide right `translateX(3px)`

### 6.7 Parlay Leg Card

```
┌───────────────────────────────────────┐
│ │ ① Arsenal ML    Implied: 47.6%  [2.10] │  ← Gold left border
└───────────────────────────────────────┘
```

- **Left border:** 3px solid `#FFD700`
- **Number badge:** Circle with gold bg, dark text
- **Odds badge:** Gold gradient

### 6.8 Parlay Summary Banner

```
┌─────────────────────────────────────────┐
│ ═══ gold gradient top line (3px) ═══    │
│ 🎯 PARLAY SUMMARY                      │
│                                         │
│ Legs: 3    Combined: 8.82x              │
│ Payout: $88.20     Profit: $78.20       │
└─────────────────────────────────────────┘
```

- **Top accent:** Gold gradient `#FFD700→#FFC107→#FF9800`
- **Background:** Dark gradient `135deg, rgba(20,23,32,0.9)→rgba(26,29,38,0.95)`
- **Border:** Gold-tinted `rgba(255,215,0,0.2)`

### 6.9 Navigation Item (Button)

```
 [ 📅 Matches        ]  ← Inactive: dark bg, muted text
 [ 💡 Value Bets     ]  ← Active: green gradient, dark text, glow
```

- **Inactive:** `rgba(13,27,42,0.4)`, text `#8899AA`
- **Hover:** Green-tinted bg, white text
- **Active:** Green gradient, dark text, glow shadow

### 6.10 Count Badge

```
 [ 23 matches found ]
```

- **Background:** Green gradient
- **Text:** Dark `#0D1B2A`, 0.8rem, weight 800
- **Shape:** Pill (radius `20px`)

### 6.11 League Badge (Pill)

```
 ⚽ ENGLISH PREMIER LEAGUE
```

- **Background:** `rgba(0,200,83,0.1)`
- **Text:** `#00C853`, 0.65rem, weight 700, uppercase
- **Border:** `1px solid rgba(0,200,83,0.2)`
- **Shape:** Pill (radius `20px`)

### 6.12 CTA Button (Primary)

```
 [ 🔄 REFRESH DATA ]
```

- **Background:** Green gradient `135deg, #00C853→#00E676`
- **Text:** Dark `#0D1B2A`, weight 700, uppercase
- **Hover:** Lift + stronger glow + lighter gradient
- **Radius:** `10px`

### 6.13 Payout Box

```
┌─────────────────────────────────────┐
│          POTENTIAL PAYOUT            │  ← Label (muted, uppercase)
│            $88.20                    │  ← Value (large, green, glowing)
└─────────────────────────────────────┘
```

- **Background:** Green-tinted glass `rgba(0,200,83,0.08→0.03)`
- **Border:** `rgba(0,200,83,0.2)`, radius `14px`
- **Text shadow:** Green glow

### 6.14 Empty State

```
        🎫
  Your bet slip is empty.
  Add selections from
  Bet Builder or Custom Parlay.
```

- **Icon:** 2.5rem, 60% opacity
- **Text:** 0.88rem, muted, centered, max-width 400px

### 6.15 Footer

```
───────────────────────────────────────
 ⚽ ApexOdds Europe · Built with Streamlit · Premium Sports Analytics
```

- **Background:** Glass `rgba(13,27,42,0.4)` with `blur(12px)`
- **Top border:** Green-tinted `rgba(0,200,83,0.08)`
- **Text:** `#556677`, 0.72rem
- **Accent text:** `#00C853` (for "Streamlit")

---

## 7. Data Visualizations

### 7.1 Chart Theme (Applied to All Plotly Charts)

Defined in `src/app.py` and applied to every Plotly figure via `_apply_dark_theme()`:

```python
DARK_THEME = {
    "paper_bgcolor": "#0D1B2A",    # Chart outer background
    "plot_bgcolor": "#0D1B2A",     # Plot area background
    "font_color": "#E8EAED",       # Axis labels, title text
    "gridcolor": "rgba(0,200,83,0.08)",  # Faint green grid
    "colorway": [
        "#00C853",  # Primary green
        "#FFD700",  # Gold
        "#00E676",  # Light green
        "#40C4FF",  # Cyan
        "#FF6B35",  # Orange
        "#E040FB",  # Purple
    ],
}
```

### 7.2 Edge Distribution Histogram (Value Bets Page)

- **Type:** Plotly `histogram`
- **X-axis:** Edge percentage
- **Y-axis:** Count of value bets
- **Color:** Green (`#00C853`)
- **Container:** Glass wrapper with `14px` radius

### 7.3 Odds Movement Line Chart (Movement Page)

- **Type:** Plotly `line` (multi-series)
- **X-axis:** Timestamp
- **Y-axis:** Decimal price
- **Lines:** One per bookmaker, using the 6-color colorway
- **Hover:** Show bookmaker name, price, timestamp
- **Container:** Glass wrapper

### 7.4 Bookmaker Margin Bar Chart (Margins Page)

- **Type:** Plotly `bar` (horizontal)
- **Y-axis:** Bookmaker names (sorted by margin, lowest first)
- **X-axis:** Average margin percentage
- **Color scale:** `RdYlGn_r` (green = low margin = good for bettors)
- **Container:** Glass wrapper

---

## 8. User Flows & Interactions

### 8.1 Primary User Flow: Discover Value Bets

```
1. User opens app → Hero header loads
2. User selects leagues in sidebar multi-select
3. User clicks "🔄 Refresh Data" → API fetches live odds
4. Summary metrics bar updates (KPIs animate)
5. User clicks "→ View Value Bets" or navigates via left panel
6. Value Bets page loads with edge threshold slider
7. User adjusts slider → list filters dynamically
8. User reviews alert cards (pulsing green badges)
9. User downloads CSV for offline analysis
```

### 8.2 Bet Builder Flow

```
1. User navigates to "🧮 Bet Calculator"
2. Selects "Bet Builder" mode via radio toggle
3. Picks a match from selectbox
4. Picks an outcome from selectbox
5. Clicks "➕ Add to Slip"
6. Selection appears in:
   - Inline bet slip (center pane)
   - Persistent bet slip (right pane)
7. Repeats steps 3–6 for more selections
8. Chooses "Single Bets" or "Accumulator"
9. Enters stake amount
10. Clicks "💰 Calculate"
11. Results display: Combined odds, payout, profit
12. Right pane updates live with payout calculations
```

### 8.3 Custom Parlay Builder Flow

```
1. User navigates to "🎯 Custom Parlay"
2. Enters a selection label (free text)
3. Enters decimal odds
4. Clicks "➕ Add Leg"
5. Leg card appears with:
   - Number badge (①, ②, ③…)
   - Label + implied probability
   - Gold odds badge
6. Parlay summary banner updates live:
   - Leg count, combined odds, payout, profit
7. Repeats steps 2–6 for more legs
8. Selects bet type: Full Parlay / Round Robin / Singles
9. Enters stake, clicks "💰 Calculate Parlay"
10. Detailed results display
```

### 8.4 Arbitrage Detection Flow

```
1. User refreshes data (sidebar button)
2. Navigates to "🔄 Arbitrage"
3. System auto-scans all markets for arb opportunities
4. Alert cards display with pulsing gold badges
5. Each card shows:
   - Match + guaranteed profit %
   - Best odds per outcome across bookmakers
6. User can download results as CSV
```

### 8.5 Navigation Interaction

- **Left Nav Panel:** Click button → updates `active_section` in session state → center pane re-renders
- **Summary Metric Buttons:** Click "→ View X" → jumps to corresponding section
- **Active State:** Current section button shows green gradient + glow
- **Sidebar:** Collapsible drawer (Streamlit native), always accessible

### 8.6 API Key Override Flow (Security)

```
1. User expands sidebar
2. Scrolls to "🔑 API Key Override"
3. Enters key in password field (masked)
4. Caption confirms "✅ Key active for this session"
5. Key stored in session memory ONLY (never persisted)
6. Key used for subsequent API calls in this browser tab
```

---

## 9. Responsive Behavior

### 9.1 Breakpoints

| Breakpoint      | Behavior                                          |
|-----------------|---------------------------------------------------|
| Desktop (>768px)| Full 3-pane layout: Nav + Content + Bet Slip      |
| Mobile (≤768px) | Match cards stack vertically, team names centered  |
|                 | Hero header padding and font size reduced          |
|                 | Sidebar becomes hamburger drawer (Streamlit native)|

### 9.2 Mobile Adaptations

```css
@media (max-width: 768px) {
    .match-card .teams {
        flex-direction: column;
        text-align: center;
    }
    .match-card .team-name.away {
        text-align: center;
    }
    .hero-header {
        padding: 1.2rem 1rem 1rem 1rem;
    }
    .hero-header .hero-title {
        font-size: 1.2rem;
    }
}
```

### 9.3 Streamlit Layout Notes

- `layout="wide"` enables full-width mode
- Sidebar is a native Streamlit drawer (hamburger on mobile)
- Columns collapse on narrow viewports (Streamlit default behavior)
- Charts auto-resize via Plotly responsive mode

---

## 10. Accessibility Notes

- **Color contrast:** Primary text `#E8EAED` on dark `#0D1B2A` (ratio > 10:1)
- **Interactive elements:** All buttons have hover/focus states with visible changes
- **Form labels:** All inputs have accessible labels (via Streamlit)
- **Keyboard navigation:** Streamlit provides native keyboard support
- **Screen readers:** Semantic HTML structure maintained where possible
- **Animations:** Pulse animations are subtle (box-shadow only, not disruptive)
- **Emoji icons:** Used as decorative indicators alongside text labels

---

## Appendix: Supported Leagues

| League                    | API Key                       | Badge Color |
|---------------------------|-------------------------------|-------------|
| English Premier League    | `soccer_epl`                  | Green       |
| La Liga (Spain)           | `soccer_spain_la_liga`        | Green       |
| Serie A (Italy)           | `soccer_italy_serie_a`       | Green       |
| Bundesliga (Germany)      | `soccer_germany_bundesliga`  | Green       |
| Ligue 1 (France)          | `soccer_france_ligue_one`    | Green       |
| UEFA Champions League     | `soccer_uefa_champs_league`  | Green       |

## Appendix: Supported Betting Markets

| Market   | Description                     | Outcomes             |
|----------|---------------------------------|----------------------|
| `h2h`    | Head-to-Head (1X2 Match Result) | Home, Draw, Away     |
| `totals` | Over/Under Goals                | Over X.5, Under X.5  |

## Appendix: Database Schema

### matches table

| Column        | Type    | Description                          |
|---------------|---------|--------------------------------------|
| match_id      | TEXT PK | Unique match identifier from API     |
| sport_key     | TEXT    | League API key (e.g. `soccer_epl`)   |
| league        | TEXT    | Human-readable league name           |
| home_team     | TEXT    | Home team name                       |
| away_team     | TEXT    | Away team name                       |
| commence_time | TEXT    | ISO 8601 kickoff timestamp           |
| created_at    | TEXT    | Record creation timestamp            |

### odds table

| Column       | Type    | Description                            |
|--------------|---------|----------------------------------------|
| id           | INT PK  | Auto-increment primary key             |
| match_id     | TEXT FK | Foreign key to matches table           |
| bookmaker    | TEXT    | Bookmaker name (e.g. `pinnacle`)       |
| market       | TEXT    | Market type (`h2h` or `totals`)        |
| outcome_name | TEXT    | Outcome label (e.g. `Home`, `Over 2.5`)|
| outcome_price| REAL    | Decimal odds                           |
| point        | REAL    | Points line (for totals, e.g. `2.5`)   |
| timestamp    | TEXT    | Snapshot timestamp                     |

---

*This design document was generated from the ApexOdds Europe codebase to serve as a complete reference for UI/UX redesign and prototyping.*
