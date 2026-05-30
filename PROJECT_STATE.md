# PROJECT_STATE.md — VNINDEX88 Current State

## Current status
The app has already evolved through multiple versions:
- V1.0 Yahoo Direct
- V1.3 Focus 3 Money Flow
- V1.6 Coverage Engine
- V1.7 Live Pulse
- V1.8 VN Volatility Calibration
- V1.9 Practical Zones
- V2.0 Late Cycle Guard
- V2.1 Gold Pipeline
- V2.2 T-1 Early Alert
- V2.3 Sector Leaders Gold

The latest working code is in app.py.

## Key lessons learned
1. Scanning only 10 stocks is not enough. The market must be scanned broadly.
2. The app must analyze 5–7 sector leaders from every major sector.
3. The app must not wait until stocks already rise strongly before detecting them.
4. BID and GVR were examples of stocks that rose well but were not detected early enough.
5. The app needs strong T-1 early alert logic.
6. The app must not recommend overextended stocks like VIC after a huge multi-month run.
7. Buy zones must be practical for Vietnam’s market volatility.
8. Vietnam stocks often fall fast and rise slowly, so buy zones must not be too wide.
9. The user prefers buying red pullbacks near support/base, not green breakout chasing.
10. Macro timing matters: inflation, war, oil, Asia markets, DXY, US rates, VIX, global indices.

## Current strategic direction
Build VNINDEX88 as a full “đãi cát tìm vàng” system:
1. Scan broad universe.
2. Select sector leaders.
3. Detect sector money flow.
4. Detect stock money flow.
5. Detect T-1 early signals.
6. Remove late-cycle/overextended stocks.
7. Remove fake setups.
8. Find practical red buy zones.
9. Select 2–3 best candidates only.
10. Provide action plan: wait, buy zone, stop loss, invalidation.

## Current pain points to improve
- T-1 early detection must be more sensitive.
- Sector leader coverage must be reliable.
- Focus list should not miss early movers.
- Buy zones must remain close to real price action.
- Need better validation/backtesting of whether signals worked before large moves.
- Need a daily workflow: before market, during red pullback, after close.
