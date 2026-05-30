# ROADMAP.md — VNINDEX88 Roadmap

## Phase 1 — Stability
- Make app run reliably on Streamlit Cloud.
- Avoid timeouts.
- Use caching and 2-stage scanning.
- Ensure enough sector leader coverage.

## Phase 2 — Early Alert
- Improve T-1 alert.
- Detect money flow before breakout.
- Detect accumulation before price runs.
- Detect sector money flow rotation.
- Detect price compression + volume absorption.

## Phase 3 — Gold Pipeline
- Rank all candidates through strict gates:
  1. data quality
  2. liquidity
  3. sector flow
  4. stock flow
  5. accumulation
  6. T-1 signal
  7. no late-cycle risk
  8. practical red buy zone
  9. risk/reward
  10. macro gate

## Phase 4 — Practical Action
- Output only 2–3 best candidates.
- For each candidate show:
  - current phase
  - red buy zone
  - stop loss
  - invalidation
  - no-buy condition
  - position plan
  - why selected
  - why rejected if not selected

## Phase 5 — Validation
- Add backtest mode.
- Test whether previous-day T-1 signals detected next-day winners.
- Compare against VNINDEX.
- Track false positives and false negatives.
