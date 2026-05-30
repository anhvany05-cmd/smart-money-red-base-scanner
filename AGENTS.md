# AGENTS.md — VNINDEX88 Project Instructions

## Project goal
Build VNINDEX88: a Vietnam stock-market scanner app that filters the whole market to find 2–3 high-probability stocks using:
- smart money / big money footprint
- money flow
- sector leadership
- early T-1 signals
- red-base accumulation buy zones
- macro timing gate
- late-cycle guard
- practical Vietnam volatility calibration

The app must not simply recommend stocks that already ran too far. It must detect early accumulation before the price is high.

## Trading philosophy
The user prefers:
- buying early on red/risk-off pullbacks near a base/support area
- avoiding green candles and breakout chasing
- cutting loss if the base breaks
- focusing on 2–3 concentrated high-quality candidates
- filtering by sector money flow and macro timing

Do not prioritize breakout buying.
Do not recommend late-cycle / overextended stocks such as stocks that already multiplied several times without a new valid base.

## Current app
Main app file:
- app.py

Current target version:
- VNINDEX88 / Smart Money Red Base Scanner

Current important modules:
- Universe coverage
- Sector leaders
- Money flow score
- T-1 early alert
- Macro timing gate
- Late cycle guard
- Practical buy zones
- Gold pipeline / focus 2–3 stocks

## Rules for every Codex task
1. Read PROJECT_STATE.md first.
2. Read ROADMAP.md second.
3. Inspect app.py before editing.
4. Make changes incrementally.
5. Keep the app deployable on Streamlit Cloud.
6. Do not remove working features unless replacing them with better logic.
7. After every task, update PROJECT_STATE.md and DAILY_LOG.md.
8. If changing logic, explain what changed and why.
9. Ensure the app still runs with:
   streamlit run app.py

## Streamlit deployment
The app runs on Streamlit Cloud from GitHub.
Main file path:
app.py

Avoid heavy dependencies if possible.
Use Yahoo Direct API / fallback logic carefully to avoid timeout.
