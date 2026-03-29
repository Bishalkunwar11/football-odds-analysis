# CLAUDE.md — ApexOdds Pro Upgrade Master Plan

> **Claude Code**: Read this file at the start of EVERY session. It is your persistent memory for this project.

---

## SESSION RECOVERY PROTOCOL

**Every time you start a new session, do this FIRST:**

1. Read `.apexodds-upgrade-state.json` to find `current_step` and which steps are `"done"` vs `"pending"`
2. Tell the user: "Resuming ApexOdds upgrade from Step {N}: {task description}"
3. If a step has `status: "in_progress"`, check the `notes` field and `files_touched` to see what was partially done
4. Continue from exactly where you left off — do NOT restart completed steps

**After completing each step:**
1. Update `.apexodds-upgrade-state.json`:
   - Set the completed step's `status` to `"done"`
   - Add any files you created/modified to `files_touched`
   - Add any relevant notes to `notes`
   - Set `current_step` to the next pending step
   - Update `last_updated` to today's date
2. Commit the state file along with your code changes
3. Tell the user what was completed and what's next

**If you hit a context/token limit mid-step:**
1. Update the current step's `status` to `"in_progress"`
2. Write detailed notes about exactly where you stopped and what remains
3. List any files that were partially modified
4. Tell the user: "Stopping at Step {N} — {what remains}. Say 'continue upgrade' to resume."

---

## MODEL STRATEGY

**Two options — pick one before starting:**

### Option A: "Set and forget" (RECOMMENDED for hands-off workflow)
```
claude config set model claude-sonnet-4-6
```
Run the ENTIRE upgrade on **Sonnet only**. Sonnet can handle all 21 steps — it's fast, cheap, and good enough for this codebase size. You just say "start the upgrade" and let it rip through steps without ever switching models. If any step's output quality isn't good enough, you can manually switch to Opus for just that one step and redo it.

**Pros**: Zero manual intervention, fastest throughput, cheapest
**Cons**: CSS rewrite and complex refactors may need a redo on Opus

### Option B: "Two-pass" (for maximum code quality)
Do the entire upgrade in TWO sessions instead of switching per-step:

**Session 1 — Sonnet**: Run steps 1, 3, 5, 8, 18, 20 (all planning/audit steps)
```
claude config set model claude-sonnet-4-6
```
Say: "Run all Sonnet-tagged steps in the upgrade plan — planning and auditing only, skip coding steps"

**Session 2 — Opus**: Run steps 2, 4, 6, 7, 9–17, 19, 21 (all coding steps)
```
claude config set model claude-opus-4-6
```
Say: "Run all Opus-tagged steps — the Sonnet planning steps are already done"

**Pros**: Best code quality, Opus gets the planning context from Sonnet's notes in the JSON
**Cons**: Two sessions, Opus is more expensive

### Step-level model tags (reference only)
| Steps | Model | Task Type |
|-------|-------|-----------|
| 1, 3, 5, 8, 18, 20 | 🟡 Sonnet | Reading, planning, auditing, verifying |
| 2, 4, 6, 7, 9–17, 19, 21 | 🔴 Opus | Writing code, refactoring, creating files |

---

## PROJECT CONTEXT

**ApexOdds Pro** is a Streamlit-based football odds analytics dashboard. We are upgrading it to FanDuel/Bet365 production quality.

**Source tree**: `src/` — see full structure in the upgrade spec below.

**Key constraints** (NEVER violate these):
- Stay on **Streamlit** — no React/Next.js migration
- Stay on **SQLite** — no Postgres/Supabase
- No external UI libraries (streamlit-extras, etc.) — all custom HTML via `st.markdown(unsafe_allow_html=True)`
- Preserve ALL existing functionality — every feature must still work
- App must work WITHOUT an API key using seeded demo data
- Single CSS file: `src/assets/styles.css`
- Mobile-responsive: ≥ 375px wide

---

## THE 21-STEP UPGRADE PLAN

### PHASE 1: BACKEND

**Step 1** 🟡 Sonnet — Audit imports
- `grep -r "ui_components" src/` to find all references
- List every file that imports from `ui_components.py`
- Map each import to its equivalent in `src/components/`

**Step 2** 🔴 Opus — Delete ui_components.py + fix imports
- Delete `src/ui_components.py`
- Update every file found in Step 1 to import from `src/components/` instead
- Verify no import errors

**Step 5** 🟡 Sonnet — Plan DB schema upgrade
- Map current tables (matches, odds, feedback) to new schema
- Plan migration path that preserves existing data
- New tables needed: leagues, bookmakers, markets, odds_snapshots (with price direction), user_bets, user_settings, alerts

**Step 6** 🔴 Opus — Upgrade DB schema
- Add all new tables to `db_manager.py`
- Add `migrate()` method that checks schema version and applies changes
- Add `price_direction` ENUM('up','down','stable') and `previous_price` to odds tracking
- Add `user_bets` table for persistent bankroll
- Add `alerts` table for the alert engine
- Preserve existing data during migration

**Step 7** 🔴 Opus — Price direction tracking
- In `store_odds()`, look up previous price for same (match_id, bookmaker, market, outcome)
- Store `previous_price` and compute `price_direction`
- Add `get_price_movements(match_id)` method
- UI should render real ▲/▼ arrows from this data

**Step 12** 🔴 Opus — Alert engine
- Add `AlertEngine` class that scans for: new value bets, new arb opps, significant price movements (>5%), sharp line moves
- Store alerts in DB with `is_read` flag
- Add `get_unread_count()`, `mark_read(alert_id)`, `get_alerts(filter, limit)`
- Add `src/sections/alerts.py` section

**Step 17** 🔴 Opus — Bankroll to DB
- Move bet log from `st.session_state` to `user_bets` table
- Add `settle_bet()`, `get_bankroll_stats()`, `get_pnl_timeseries()`
- Update `src/sections/bankroll.py` to use DB instead of session state
- Support CSV import of historical bets

### PHASE 2: UI/UX

**Step 3** 🟡 Sonnet — Plan CSS rewrite
- Audit `styles.css` — identify which CSS classes are actually used in components/
- List the 3 competing design systems and which rules belong to which
- Define the single target system: "Obsidian Terminal" (see design tokens below)

**Step 4** 🔴 Opus — Rewrite styles.css from scratch
```
DESIGN TOKENS:
--bg-base: #0A0F1A
--bg-surface: rgba(13, 27, 42, 0.65) + backdrop-filter: blur(16px)
--bg-raised: rgba(20, 23, 32, 0.85)
--border: rgba(255, 255, 255, 0.06)
--primary: #00C853 (green — CTAs, active states)
--accent-gold: #FFD700 (odds values, premium badges)
--accent-red: #FF3D3D (losses, live indicators)
--text-primary: #E8EAED
--text-secondary: #8899AA
--text-muted: #556677
Fonts: 'Barlow Condensed' (display), 'DM Sans' (body), 'JetBrains Mono' (odds)
```
- Write ONE coherent stylesheet — no layered overrides
- Remove all scanline/dot-grid ::after overlays
- Remove the background-image Unsplash URL
- All cards use glassmorphism (semi-transparent bg + blur + subtle border)

**Step 8** 🟡 Sonnet — Plan layout rewrite
- Map the current `app.py` structure (sidebar, hero, KPI, 3-column layout, footer)
- Design the new layout: sidebar nav + full-width main + collapsible bet slip drawer
- List all session state keys that need to change

**Step 9** 🔴 Opus — Rewrite app.py layout
- Replace 3-column layout with sidebar nav + full-width main
- Bet slip becomes a collapsible right drawer (toggled by floating button)
- Use `st.columns([1.5, 8.5])` when slip is hidden, `[1.5, 6, 3]` when visible
- Add "Bet Slip (N)" floating toggle button
- Add "dashboard" as the new default `active_section`

**Step 10** 🔴 Opus — Redesign match cards
- Show implied probability under each odds button
- Real ▲/▼ from price_direction data (not hardcoded thresholds)
- Clickable odds buttons that add to bet slip via `on_click`
- PRO EDGE badge only when real value edge exists
- Team initial circles as logo placeholders

**Step 11** 🔴 Opus — Upgrade bet slip
- Tab switcher: Single / Parlay / Round-Robin
- Per-selection stake input in Singles mode
- Remove button per selection
- Live-updating payout as stake changes
- Quick-add buttons (+10, +50, +100, MAX)
- "Place Bet" CTA with total stake
- Odds change warning banner

**Step 13** 🔴 Opus — Dashboard home (new default)
- Add `src/sections/dashboard.py`
- KPI row: matches, value bets, arb opps, bankroll + ROI
- Hot Bets horizontal strip (top 5 value bets)
- P&L trend sparkline (7-day)
- Upcoming fixtures preview (3 cards)
- Recent alerts preview (3 items)
- "View All →" links for each section

**Step 14** 🔴 Opus — Navigation upgrade
- Icons + labels (not just text)
- Group: "Markets" (Dashboard, Matches, Value Bets, Arbitrage, Margins), "Tools" (Calculator, Parlay Builder), "Live" (Live Center), "Account" (Bankroll, Alerts, Settings, Feedback)
- Badge counts on Value Bets, Arbitrage, Live Center, Alerts
- Active state: left border accent + background highlight

**Step 15** 🔴 Opus — Value bets upgrade
- Toggle: Card View / Table View
- Sort by: Edge, Odds, Match, League
- Filter by: League, Bookmaker, Market, Min Edge
- "Add to Slip" button per card
- Kelly recommended stake per bet
- Aggregate stats banner

**Step 16** 🔴 Opus — Live center upgrade
- `LiveSimulator` class with match state persistence
- Simulated match events (goals, cards, half-time)
- Live odds that shift with score changes
- Match stats panel (possession, shots, corners)
- Clear "SIMULATED" watermark

### PHASE 3: CODE QUALITY

**Step 18** 🟡 Sonnet — Verify everything
- Run `streamlit run src/app.py` and click through every section
- Check for import errors, missing components, broken layouts
- List any issues found

**Step 19** 🔴 Opus — Write test suite
- `tests/test_analyzer.py` — all OddsAnalyzer methods
- `tests/test_bet_calculator.py` — all BetCalculator methods
- `tests/test_db_manager.py` — integration tests with `:memory:` DB
- `tests/test_api_client.py` — mock tests
- `tests/test_components.py` — HTML render snapshot tests
- Target >80% coverage

**Step 20** 🟡 Sonnet — Run tests + mypy
- `pytest --cov=src tests/`
- `mypy --strict src/`
- List all failures

**Step 21** 🔴 Opus — Final cleanup
- Fix all mypy errors
- Fix all test failures
- Add missing type hints
- Move magic numbers to config.py
- Add `.env.example`
- Final pass on error handling

---

## SUCCESS CRITERIA

1. ✅ Looks indistinguishable from a real sportsbook
2. ✅ Real odds movement tracking (not fake arrows)
3. ✅ Persistent bet history (SQLite, not session_state)
4. ✅ Working alert system
5. ✅ Single cohesive design system (no competing CSS)
6. ✅ Zero imports from deleted `ui_components.py`
7. ✅ Collapsible bet slip drawer
8. ✅ Dashboard home with KPIs, hot bets, P&L, alerts
9. ✅ `mypy --strict` passes
10. ✅ >80% backend test coverage
