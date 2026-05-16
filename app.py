"""
Smart Money Red Base Scanner - MVP V0.4
Author: ChatGPT
Purpose: Scan Vietnamese stock candidates using an early-accumulation, red-base buying style.

This app is an analytical tool, not financial advice. Always verify data and manage risk.
"""

from __future__ import annotations

import io
import math
from datetime import date, timedelta
from dataclasses import dataclass
from typing import Dict, List, Optional, Tuple

import numpy as np
import pandas as pd
import plotly.graph_objects as go
import streamlit as st


# -----------------------------
# Configuration / Labels
# -----------------------------
REQUIRED_PRICE_COLUMNS = {"date", "ticker", "open", "high", "low", "close", "volume"}
OPTIONAL_PRICE_COLUMNS = {"value", "sector"}
REQUIRED_INDEX_COLUMNS = {"date", "open", "high", "low", "close"}
FUNDAMENTAL_COLUMNS = {
    "ticker",
    "revenue_growth_yoy",
    "profit_growth_yoy",
    "roe",
    "debt_to_equity",
    "operating_cashflow_positive",
    "expectation_score",
}


# Universe mặc định: nhóm thanh khoản/vốn hóa thường được thị trường theo dõi.
# Người dùng vẫn có thể sửa danh sách trong sidebar, nhưng app không còn bắt buộc upload file giá.
DEFAULT_TICKERS = [
    "HPG", "SSI", "FPT", "MBB", "TCB", "VCB", "BID", "CTG", "VPB", "ACB",
    "VIB", "STB", "SHB", "HDB", "TPB", "LPB", "MSB", "VND", "VCI", "HCM",
    "VIX", "MBS", "SHS", "DGC", "DPM", "DCM", "GAS", "PVD", "PVS", "PLX",
    "VNM", "MSN", "MWG", "FRT", "DGW", "PNJ", "SAB", "VRE", "VHM", "VIC",
    "KDH", "NLG", "DXG", "DIG", "CEO", "KBC", "SZC", "BCM", "GVR", "VGC",
    "HSG", "NKG", "HAG", "HNG", "ANV", "VHC", "GEX", "REE", "PC1", "POW",
    "CTR", "CMG", "FOX", "FPT", "DPR", "PHR", "PVT", "GMD", "HAH", "VSC"
]

VN30_LIKE_TICKERS = [
    "ACB", "BID", "BVH", "CTG", "FPT", "GAS", "GVR", "HDB", "HPG", "MBB",
    "MSN", "MWG", "PLX", "POW", "SAB", "SHB", "SSB", "SSI", "STB", "TCB",
    "TPB", "VCB", "VHM", "VIB", "VIC", "VJC", "VNM", "VPB", "VRE", "VPI"
]

DEFAULT_SECTOR_MAP = {
    # Ngân hàng
    "VCB": "Ngân hàng", "BID": "Ngân hàng", "CTG": "Ngân hàng", "MBB": "Ngân hàng", "TCB": "Ngân hàng",
    "VPB": "Ngân hàng", "ACB": "Ngân hàng", "STB": "Ngân hàng", "HDB": "Ngân hàng", "VIB": "Ngân hàng",
    "SHB": "Ngân hàng", "TPB": "Ngân hàng", "LPB": "Ngân hàng", "MSB": "Ngân hàng", "SSB": "Ngân hàng",
    # Chứng khoán
    "SSI": "Chứng khoán", "VND": "Chứng khoán", "VCI": "Chứng khoán", "HCM": "Chứng khoán", "VIX": "Chứng khoán",
    "MBS": "Chứng khoán", "SHS": "Chứng khoán", "FTS": "Chứng khoán", "CTS": "Chứng khoán", "BSI": "Chứng khoán",
    # Thép/vật liệu
    "HPG": "Thép", "HSG": "Thép", "NKG": "Thép", "SMC": "Thép", "TLH": "Thép",
    "GVR": "Cao su", "DPR": "Cao su", "PHR": "Cao su", "BMP": "Nhựa", "NTP": "Nhựa",
    # Bất động sản/KCN
    "VHM": "Bất động sản", "VIC": "Bất động sản", "VRE": "Bất động sản", "KDH": "Bất động sản", "NLG": "Bất động sản",
    "DXG": "Bất động sản", "DIG": "Bất động sản", "CEO": "Bất động sản", "NVL": "Bất động sản", "PDR": "Bất động sản",
    "KBC": "Khu công nghiệp", "SZC": "Khu công nghiệp", "BCM": "Khu công nghiệp", "VGC": "Khu công nghiệp", "IDC": "Khu công nghiệp",
    # Dầu khí/điện/hóa chất
    "GAS": "Dầu khí", "PVD": "Dầu khí", "PVS": "Dầu khí", "PLX": "Dầu khí", "BSR": "Dầu khí", "PVT": "Dầu khí",
    "POW": "Điện", "REE": "Điện", "PC1": "Điện", "NT2": "Điện", "GEG": "Điện",
    "DGC": "Hóa chất", "DPM": "Hóa chất", "DCM": "Hóa chất", "CSV": "Hóa chất", "LAS": "Hóa chất",
    # Tiêu dùng/bán lẻ/công nghệ
    "FPT": "Công nghệ", "CMG": "Công nghệ", "FOX": "Công nghệ", "CTR": "Công nghệ",
    "MWG": "Bán lẻ", "FRT": "Bán lẻ", "DGW": "Bán lẻ", "PNJ": "Bán lẻ", "PET": "Bán lẻ",
    "VNM": "Tiêu dùng", "MSN": "Tiêu dùng", "SAB": "Tiêu dùng", "KDC": "Tiêu dùng", "QNS": "Tiêu dùng",
    # Xuất khẩu/logistics/nông nghiệp
    "GMD": "Logistics", "HAH": "Logistics", "VSC": "Logistics", "VTP": "Logistics",
    "VHC": "Thủy sản", "ANV": "Thủy sản", "IDI": "Thủy sản", "HAG": "Nông nghiệp", "HNG": "Nông nghiệp",
}


@dataclass
class ScanConfig:
    min_avg_value_20: float = 5_000_000_000  # VND
    min_sessions: int = 80
    base_window: int = 60
    short_window: int = 20
    atr_window: int = 14
    volume_anomaly_mult: float = 1.5
    strong_volume_mult: float = 1.8
    buy_zone_fraction: float = 0.35
    no_chase_fraction: float = 0.65
    stop_atr_buffer: float = 0.5
    max_base_width_pct: float = 0.28
    red_day_threshold: float = 0.0


# -----------------------------
# Utility functions
# -----------------------------
def normalize_columns(df: pd.DataFrame) -> pd.DataFrame:
    df = df.copy()
    df.columns = [str(c).strip().lower().replace(" ", "_") for c in df.columns]
    return df


def read_csv_excel(file) -> pd.DataFrame:
    if file is None:
        raise ValueError("No file provided")
    name = file.name.lower()
    if name.endswith((".xlsx", ".xls")):
        return pd.read_excel(file)
    return pd.read_csv(file)


def ensure_numeric(df: pd.DataFrame, cols: List[str]) -> pd.DataFrame:
    df = df.copy()
    for c in cols:
        if c in df.columns:
            df[c] = pd.to_numeric(df[c], errors="coerce")
    return df


def preprocess_prices(df: pd.DataFrame) -> pd.DataFrame:
    df = normalize_columns(df)
    missing = REQUIRED_PRICE_COLUMNS - set(df.columns)
    if missing:
        raise ValueError(f"File giá thiếu cột bắt buộc: {', '.join(sorted(missing))}")
    df["date"] = pd.to_datetime(df["date"], errors="coerce")
    df["ticker"] = df["ticker"].astype(str).str.upper().str.strip()
    if "sector" not in df.columns:
        df["sector"] = "Unknown"
    if "value" not in df.columns:
        df["value"] = df["close"] * df["volume"]
    numeric_cols = ["open", "high", "low", "close", "volume", "value"]
    df = ensure_numeric(df, numeric_cols)
    df = df.dropna(subset=["date", "ticker", "open", "high", "low", "close", "volume"])
    df = df.sort_values(["ticker", "date"]).reset_index(drop=True)
    return df


def preprocess_index(df: pd.DataFrame) -> pd.DataFrame:
    df = normalize_columns(df)
    missing = REQUIRED_INDEX_COLUMNS - set(df.columns)
    if missing:
        raise ValueError(f"File VNIndex thiếu cột bắt buộc: {', '.join(sorted(missing))}")
    df["date"] = pd.to_datetime(df["date"], errors="coerce")
    numeric_cols = ["open", "high", "low", "close", "volume", "value"]
    df = ensure_numeric(df, [c for c in numeric_cols if c in df.columns])
    df = df.dropna(subset=["date", "open", "high", "low", "close"])
    df = df.sort_values("date").reset_index(drop=True)
    return df


def preprocess_fundamentals(df: Optional[pd.DataFrame]) -> pd.DataFrame:
    if df is None or df.empty:
        return pd.DataFrame(columns=list(FUNDAMENTAL_COLUMNS))
    df = normalize_columns(df)
    if "ticker" not in df.columns:
        raise ValueError("File nền tảng/kỳ vọng cần có cột ticker")
    df["ticker"] = df["ticker"].astype(str).str.upper().str.strip()
    for col in FUNDAMENTAL_COLUMNS - {"ticker"}:
        if col not in df.columns:
            df[col] = np.nan
    numeric_cols = list(FUNDAMENTAL_COLUMNS - {"ticker", "operating_cashflow_positive"})
    df = ensure_numeric(df, numeric_cols)
    if "operating_cashflow_positive" in df.columns:
        df["operating_cashflow_positive"] = df["operating_cashflow_positive"].astype(str).str.lower().isin(["1", "true", "yes", "y", "có", "co", "positive"])
    return df[list(FUNDAMENTAL_COLUMNS)]


# -----------------------------
# Online data loaders
# -----------------------------
def parse_ticker_text(text: str) -> List[str]:
    """Parse comma/space/newline separated ticker text and deduplicate while preserving order."""
    if not text:
        return []
    raw = []
    for part in text.replace(";", ",").replace("\n", ",").replace(" ", ",").split(","):
        t = part.strip().upper()
        if t:
            raw.append(t)
    seen = set()
    out = []
    for t in raw:
        if t not in seen:
            seen.add(t)
            out.append(t)
    return out


def normalize_external_history(df: pd.DataFrame, ticker: str, is_index: bool = False) -> pd.DataFrame:
    """Normalize OHLCV from vnstock/yfinance into internal format.

    Stocks are normalized to thousand-VND display units when the source returns VND/share.
    `value` is kept in VND so liquidity filters remain meaningful.
    """
    if df is None or df.empty:
        return pd.DataFrame()
    x = normalize_columns(df)
    rename_candidates = {
        "time": "date", "trading_date": "date", "datetime": "date", "index": "date",
        "adj_close": "close", "adjclose": "close",
        "vol": "volume", "matched_volume": "volume", "total_volume": "volume",
    }
    x = x.rename(columns={k: v for k, v in rename_candidates.items() if k in x.columns})
    if "date" not in x.columns and isinstance(x.index, pd.DatetimeIndex):
        x = x.reset_index().rename(columns={"index": "date"})
    required = {"date", "open", "high", "low", "close"}
    if not required.issubset(set(x.columns)):
        return pd.DataFrame()
    if "volume" not in x.columns:
        x["volume"] = 0
    x = ensure_numeric(x, ["open", "high", "low", "close", "volume"])
    x["date"] = pd.to_datetime(x["date"], errors="coerce").dt.tz_localize(None)
    x = x.dropna(subset=["date", "open", "high", "low", "close"])
    if x.empty:
        return pd.DataFrame()

    raw_close = x["close"].copy()
    if not is_index:
        # Many providers return VND/share (27050); some return thousand VND (27.05).
        # Internally we display stock price as thousand VND, but calculate value in actual VND.
        med = float(raw_close.dropna().median()) if raw_close.notna().any() else 0
        if med > 1000:
            for c in ["open", "high", "low", "close"]:
                x[c] = x[c] / 1000.0
            x["value"] = raw_close * x["volume"]
        else:
            x["value"] = x["close"] * 1000.0 * x["volume"]
        x["ticker"] = ticker.upper()
        x["sector"] = DEFAULT_SECTOR_MAP.get(ticker.upper(), "Unknown")
        return preprocess_prices(x[["date", "ticker", "open", "high", "low", "close", "volume", "value", "sector"]])

    out = x[["date", "open", "high", "low", "close", "volume"]].copy()
    return preprocess_index(out)


@st.cache_data(ttl=3600, show_spinner=False)
def fetch_history_vnstock(symbol: str, start: str, end: str, source: str = "VCI", is_index: bool = False) -> pd.DataFrame:
    """Fetch OHLCV via Vnstock. Supports both recent Quote API and older helper API when available."""
    symbol = symbol.upper().strip()
    errors = []

    # Modern documented API: from vnstock import Quote; Quote(symbol='HPG', source='VCI').history(...)
    try:
        from vnstock import Quote  # type: ignore
        quote = Quote(symbol=symbol, source=source)
        df = quote.history(start=start, end=end, interval="1D")
        out = normalize_external_history(df, symbol, is_index=is_index)
        if not out.empty:
            return out
    except Exception as e:
        errors.append(f"Quote API lỗi: {e}")

    # Compatibility with older vnstock/vnstock3 style.
    try:
        from vnstock import stock_historical_data  # type: ignore
        df = stock_historical_data(symbol=symbol, start_date=start, end_date=end)
        out = normalize_external_history(df, symbol, is_index=is_index)
        if not out.empty:
            return out
    except Exception as e:
        errors.append(f"Legacy API lỗi: {e}")

    raise RuntimeError("; ".join(errors[-2:]) if errors else "Không lấy được dữ liệu")


@st.cache_data(ttl=3600, show_spinner=False)
def fetch_history_yfinance(symbol: str, start: str, end: str, is_index: bool = False) -> pd.DataFrame:
    """Fallback via Yahoo Finance. Tries .VN and .HN suffix for equities."""
    try:
        import yfinance as yf  # type: ignore
    except Exception as e:
        raise RuntimeError(f"Chưa cài yfinance: {e}")

    candidates = [symbol]
    if is_index:
        candidates = ["^VNINDEX", "VNINDEX.VN", symbol]
    else:
        candidates = [f"{symbol}.VN", f"{symbol}.HN", symbol]

    last_error = None
    for ysym in candidates:
        try:
            df = yf.download(ysym, start=start, end=end, interval="1d", progress=False, auto_adjust=False)
            if df is None or df.empty:
                continue
            if isinstance(df.columns, pd.MultiIndex):
                df.columns = [c[0] for c in df.columns]
            df = df.reset_index()
            out = normalize_external_history(df, symbol, is_index=is_index)
            if not out.empty:
                return out
        except Exception as e:
            last_error = e
            continue
    raise RuntimeError(f"Yahoo không trả dữ liệu cho {symbol}. Lỗi cuối: {last_error}")


def fetch_one_symbol(symbol: str, start: str, end: str, provider: str, vnstock_source: str) -> Tuple[pd.DataFrame, Optional[str]]:
    """Fetch one equity, with graceful fallback."""
    try:
        if provider == "Vnstock":
            return fetch_history_vnstock(symbol, start, end, vnstock_source, is_index=False), None
        if provider == "Yahoo":
            return fetch_history_yfinance(symbol, start, end, is_index=False), None
        # Auto fallback: try Vnstock first, then Yahoo.
        try:
            return fetch_history_vnstock(symbol, start, end, vnstock_source, is_index=False), None
        except Exception:
            return fetch_history_yfinance(symbol, start, end, is_index=False), None
    except Exception as e:
        return pd.DataFrame(), f"{symbol}: {e}"


def fetch_index_auto(start: str, end: str, provider: str, vnstock_source: str) -> Tuple[pd.DataFrame, Optional[str]]:
    try:
        if provider == "Vnstock":
            return fetch_history_vnstock("VNINDEX", start, end, vnstock_source, is_index=True), None
        if provider == "Yahoo":
            return fetch_history_yfinance("VNINDEX", start, end, is_index=True), None
        try:
            return fetch_history_vnstock("VNINDEX", start, end, vnstock_source, is_index=True), None
        except Exception:
            return fetch_history_yfinance("VNINDEX", start, end, is_index=True), None
    except Exception as e:
        return pd.DataFrame(), f"VNINDEX: {e}"


def try_auto_list_symbols(limit: int = 120) -> List[str]:
    """Best-effort listing. If the installed vnstock version changes API, fallback is used."""
    candidates = []
    try:
        from vnstock import Listing  # type: ignore
        listing = Listing()
        for method_name in ["all_symbols", "symbols_by_exchange", "list_by_exchange"]:
            if hasattr(listing, method_name):
                method = getattr(listing, method_name)
                try:
                    df = method()
                    if isinstance(df, pd.DataFrame):
                        col = next((c for c in ["symbol", "ticker", "code"] if c in [str(x).lower() for x in df.columns]), None)
                        if col is None:
                            # find any object column that looks like ticker
                            for c in df.columns:
                                vals = df[c].dropna().astype(str).str.upper()
                                if len(vals) and vals.str.match(r"^[A-Z]{3,4}$").mean() > 0.5:
                                    col = c; break
                        if col is not None:
                            candidates.extend(df[col].dropna().astype(str).str.upper().tolist())
                    elif isinstance(df, (list, tuple)):
                        candidates.extend([str(x).upper() for x in df])
                except Exception:
                    pass
    except Exception:
        pass
    cleaned = []
    seen = set()
    for t in candidates:
        t = t.strip().upper()
        if 2 <= len(t) <= 5 and t.isalpha() and t not in seen:
            seen.add(t); cleaned.append(t)
    return cleaned[:limit] if cleaned else DEFAULT_TICKERS[:limit]


def build_neutral_fundamentals(tickers: List[str]) -> pd.DataFrame:
    """Use neutral fundamental score when automatic finance data is not configured.
    This keeps the scanner fully automatic while not pretending to know BCTC if it was not fetched.
    """
    return preprocess_fundamentals(pd.DataFrame({"ticker": tickers}))


def pct_change(series: pd.Series, periods: int) -> float:
    if len(series) <= periods or series.iloc[-periods - 1] == 0:
        return np.nan
    return float(series.iloc[-1] / series.iloc[-periods - 1] - 1)


def true_range(df: pd.DataFrame) -> pd.Series:
    prev_close = df["close"].shift(1)
    tr1 = df["high"] - df["low"]
    tr2 = (df["high"] - prev_close).abs()
    tr3 = (df["low"] - prev_close).abs()
    return pd.concat([tr1, tr2, tr3], axis=1).max(axis=1)


def safe_round_price(x: float) -> float:
    if pd.isna(x) or not np.isfinite(x):
        return np.nan
    if x >= 100:
        return round(x, 1)
    if x >= 10:
        return round(x, 2)
    return round(x, 3)


def format_range(a: float, b: float) -> str:
    if pd.isna(a) or pd.isna(b):
        return "—"
    return f"{safe_round_price(a)}–{safe_round_price(b)}"


def close_position(row: pd.Series) -> float:
    rng = row["high"] - row["low"]
    if rng <= 0:
        return 0.5
    return float((row["close"] - row["low"]) / rng)


# -----------------------------
# Demo data
# -----------------------------
def generate_demo_data(seed: int = 42) -> Tuple[pd.DataFrame, pd.DataFrame, pd.DataFrame]:
    rng = np.random.default_rng(seed)
    dates = pd.bdate_range(end=pd.Timestamp.today().normalize(), periods=150)
    tickers = ["ABC", "XYZ", "HHH", "KKK", "HPG", "SSI", "FPT", "VNM", "BID", "MBB"]
    sectors = {
        "ABC": "Thép",
        "XYZ": "Chứng khoán",
        "HHH": "Khu công nghiệp",
        "KKK": "Bất động sản",
        "HPG": "Thép",
        "SSI": "Chứng khoán",
        "FPT": "Công nghệ",
        "VNM": "Tiêu dùng",
        "BID": "Ngân hàng",
        "MBB": "Ngân hàng",
    }

    # VNIndex synthetic
    idx_price = 1180 + np.cumsum(rng.normal(0.8, 8, size=len(dates)))
    idx_open = idx_price + rng.normal(0, 3, len(dates))
    idx_high = np.maximum(idx_open, idx_price) + rng.uniform(2, 8, len(dates))
    idx_low = np.minimum(idx_open, idx_price) - rng.uniform(2, 8, len(dates))
    vnindex = pd.DataFrame(
        {
            "date": dates,
            "open": idx_open,
            "high": idx_high,
            "low": idx_low,
            "close": idx_price,
            "volume": rng.integers(500_000_000, 900_000_000, len(dates)),
            "value": rng.integers(12_000_000_000_000, 25_000_000_000_000, len(dates)),
        }
    )

    rows = []
    for t in tickers:
        base = rng.uniform(15, 55)
        noise = rng.normal(0, 0.35, len(dates))
        drift = rng.normal(0.03, 0.05)
        price = base + np.cumsum(noise + drift)

        # shape special demo patterns in last 60 sessions
        if t == "ABC":  # accumulation low base
            price[-60:] = 25 + rng.normal(0, 0.45, 60)
            price[-12:] += np.linspace(-0.2, 0.15, 12)
        elif t == "XYZ":  # shakeout
            price[-60:] = 18.8 + rng.normal(0, 0.38, 60)
            price[-3] = 17.95
            price[-2] = 18.55
            price[-1] = 18.45
        elif t == "HHH":  # already breakout
            price[-60:-8] = 31 + rng.normal(0, 0.55, 52)
            price[-8:] = np.linspace(31.5, 34.8, 8) + rng.normal(0, 0.25, 8)
        elif t == "KKK":  # distribution after run
            price[-70:-15] = 13 + np.linspace(0, 6, 55) + rng.normal(0, 0.2, 55)
            price[-15:] = 19 + rng.normal(0, 0.8, 15)
            price[-1] = price[-2] * 0.985
        elif t == "SSI":
            price[-60:] = 32 + np.linspace(0, 4, 60) + rng.normal(0, 0.5, 60)
        elif t == "HPG":
            price[-60:] = 28 + rng.normal(0, 0.6, 60)
            price[-10:] = 27.5 + rng.normal(0, 0.35, 10)
        elif t == "FPT":
            price[-60:] = 95 + np.linspace(0, 5, 60) + rng.normal(0, 0.8, 60)

        price = np.maximum(price, 3)
        opens = price + rng.normal(0, 0.25, len(dates))
        highs = np.maximum(opens, price) + rng.uniform(0.15, 0.9, len(dates))
        lows = np.minimum(opens, price) - rng.uniform(0.15, 0.9, len(dates))
        volume = rng.integers(500_000, 4_500_000, len(dates)).astype(float)

        if t in ["ABC", "XYZ", "HHH", "KKK"]:
            volume[-10:] *= rng.uniform(1.4, 2.3, 10)
        if t == "XYZ":
            volume[-3] *= 2.5
        if t == "HHH":
            volume[-5:] *= 2.0
        if t == "KKK":
            volume[-3:] *= 2.7

        value = volume * price * 1000  # approximate VND if price in thousand VND
        for i, d in enumerate(dates):
            rows.append(
                {
                    "date": d,
                    "ticker": t,
                    "open": max(opens[i], 1),
                    "high": max(highs[i], opens[i], price[i]),
                    "low": max(min(lows[i], opens[i], price[i]), 1),
                    "close": price[i],
                    "volume": int(volume[i]),
                    "value": float(value[i]),
                    "sector": sectors[t],
                }
            )
    prices = pd.DataFrame(rows)

    fundamentals = pd.DataFrame(
        [
            {"ticker": "ABC", "revenue_growth_yoy": 18, "profit_growth_yoy": 35, "roe": 14, "debt_to_equity": 0.6, "operating_cashflow_positive": True, "expectation_score": 11},
            {"ticker": "XYZ", "revenue_growth_yoy": 22, "profit_growth_yoy": 48, "roe": 13, "debt_to_equity": 0.4, "operating_cashflow_positive": True, "expectation_score": 12},
            {"ticker": "HHH", "revenue_growth_yoy": 10, "profit_growth_yoy": 20, "roe": 11, "debt_to_equity": 0.8, "operating_cashflow_positive": True, "expectation_score": 9},
            {"ticker": "KKK", "revenue_growth_yoy": -5, "profit_growth_yoy": -20, "roe": 4, "debt_to_equity": 2.2, "operating_cashflow_positive": False, "expectation_score": 3},
            {"ticker": "HPG", "revenue_growth_yoy": 15, "profit_growth_yoy": 28, "roe": 10, "debt_to_equity": 0.7, "operating_cashflow_positive": True, "expectation_score": 10},
            {"ticker": "SSI", "revenue_growth_yoy": 25, "profit_growth_yoy": 42, "roe": 12, "debt_to_equity": 0.5, "operating_cashflow_positive": True, "expectation_score": 13},
            {"ticker": "FPT", "revenue_growth_yoy": 20, "profit_growth_yoy": 22, "roe": 25, "debt_to_equity": 0.3, "operating_cashflow_positive": True, "expectation_score": 10},
            {"ticker": "VNM", "revenue_growth_yoy": 2, "profit_growth_yoy": 5, "roe": 18, "debt_to_equity": 0.2, "operating_cashflow_positive": True, "expectation_score": 4},
            {"ticker": "BID", "revenue_growth_yoy": 8, "profit_growth_yoy": 12, "roe": 16, "debt_to_equity": 1.0, "operating_cashflow_positive": True, "expectation_score": 7},
            {"ticker": "MBB", "revenue_growth_yoy": 12, "profit_growth_yoy": 18, "roe": 21, "debt_to_equity": 0.9, "operating_cashflow_positive": True, "expectation_score": 8},
        ]
    )
    return preprocess_prices(prices), preprocess_index(vnindex), preprocess_fundamentals(fundamentals)


# -----------------------------
# Scoring engines
# -----------------------------
def score_fundamentals(ticker: str, fundamentals: pd.DataFrame) -> Tuple[float, List[str]]:
    """Score fundamentals + expectations out of 15."""
    notes: List[str] = []
    if fundamentals.empty or ticker not in set(fundamentals["ticker"]):
        return 7.0, ["Chưa có file nền tảng/kỳ vọng: tạm cho điểm trung tính 7/15."]

    row = fundamentals.loc[fundamentals["ticker"] == ticker].iloc[-1]
    score = 0.0

    rev = row.get("revenue_growth_yoy", np.nan)
    prof = row.get("profit_growth_yoy", np.nan)
    roe = row.get("roe", np.nan)
    debt = row.get("debt_to_equity", np.nan)
    ocf = bool(row.get("operating_cashflow_positive", False))
    exp = row.get("expectation_score", np.nan)

    if pd.notna(rev):
        if rev > 20:
            score += 2.0; notes.append("Doanh thu tăng mạnh YoY.")
        elif rev > 5:
            score += 1.3; notes.append("Doanh thu tăng YoY.")
        elif rev >= 0:
            score += 0.6; notes.append("Doanh thu đi ngang/tăng nhẹ.")
        else:
            notes.append("Doanh thu giảm YoY.")

    if pd.notna(prof):
        if prof > 30:
            score += 3.0; notes.append("Lợi nhuận tăng mạnh YoY.")
        elif prof > 10:
            score += 2.0; notes.append("Lợi nhuận tăng YoY.")
        elif prof > 0:
            score += 1.0; notes.append("Lợi nhuận tăng nhẹ.")
        else:
            notes.append("Lợi nhuận giảm hoặc chưa cải thiện.")

    if pd.notna(roe):
        if roe >= 18:
            score += 2.0; notes.append("ROE tốt.")
        elif roe >= 10:
            score += 1.2; notes.append("ROE chấp nhận được.")
        elif roe >= 5:
            score += 0.5; notes.append("ROE thấp.")

    if pd.notna(debt):
        if debt <= 0.8:
            score += 1.5; notes.append("Đòn bẩy tài chính tương đối an toàn.")
        elif debt <= 1.5:
            score += 0.8; notes.append("Đòn bẩy ở mức cần theo dõi.")
        else:
            notes.append("Nợ/vốn chủ cao, cần cảnh giác.")

    if ocf:
        score += 1.5; notes.append("Dòng tiền kinh doanh dương/cải thiện.")
    else:
        notes.append("Dòng tiền kinh doanh chưa tích cực.")

    if pd.notna(exp):
        # expectation_score input is 0-15 or 0-10; normalize conservatively
        exp_norm = max(0.0, min(5.0, float(exp) / 15 * 5 if exp > 10 else float(exp) / 10 * 5))
        score += exp_norm
        if exp_norm >= 4:
            notes.append("Kỳ vọng/câu chuyện tương lai mạnh.")
        elif exp_norm >= 2.5:
            notes.append("Có câu chuyện kỳ vọng ở mức vừa.")
        else:
            notes.append("Kỳ vọng tương lai chưa rõ.")

    return min(score, 15.0), notes


def compute_sector_returns(prices: pd.DataFrame, window: int = 20) -> Dict[str, float]:
    out: Dict[str, float] = {}
    for sector, g in prices.groupby("sector"):
        returns = []
        for _, tg in g.groupby("ticker"):
            tg = tg.sort_values("date")
            r = pct_change(tg["close"], window)
            if pd.notna(r):
                returns.append(r)
        out[sector] = float(np.nanmedian(returns)) if returns else np.nan
    return out


def scan_one_ticker(
    tg: pd.DataFrame,
    vnindex: pd.DataFrame,
    fundamentals: pd.DataFrame,
    sector_returns: Dict[str, float],
    cfg: ScanConfig,
) -> Optional[Dict]:
    tg = tg.sort_values("date").reset_index(drop=True)
    ticker = tg["ticker"].iloc[-1]
    sector = tg["sector"].iloc[-1] if "sector" in tg.columns else "Unknown"
    if len(tg) < cfg.min_sessions:
        return None

    # Align VNIndex by date
    merged = tg[["date", "close"]].merge(vnindex[["date", "close"]].rename(columns={"close": "vn_close"}), on="date", how="left")
    merged["vn_close"] = merged["vn_close"].ffill().bfill()

    recent = tg.iloc[-cfg.base_window:].copy()
    recent20 = tg.iloc[-cfg.short_window:].copy()
    last = tg.iloc[-1]
    prev = tg.iloc[-2]

    tg["tr"] = true_range(tg)
    atr = float(tg["tr"].rolling(cfg.atr_window).mean().iloc[-1])
    if pd.isna(atr) or atr <= 0:
        atr = float((recent["high"] - recent["low"]).mean())
    atr = max(atr, 0.01)

    avg_volume_20 = float(recent20["volume"].mean())
    avg_volume_60 = float(recent["volume"].mean())
    avg_value_20 = float(recent20["value"].mean()) if "value" in recent20 else float((recent20["close"] * recent20["volume"]).mean())
    avg_value_60 = float(recent["value"].mean()) if "value" in recent else float((recent["close"] * recent["volume"]).mean())

    # Liquidity filter: keep but flag if not passed
    liquidity_pass = avg_value_20 >= cfg.min_avg_value_20

    # Base detection using 10/90 quantiles to avoid one-day extremes
    base_low = float(recent["low"].quantile(0.10))
    base_high = float(recent["high"].quantile(0.90))
    base_mid = (base_low + base_high) / 2
    base_width = max(base_high - base_low, 0.01)
    base_width_pct = base_width / base_mid if base_mid else np.nan
    close = float(last["close"])
    today_ret = float(close / prev["close"] - 1) if prev["close"] else 0
    in_base = base_low - 0.5 * atr <= close <= base_high + 0.3 * atr
    base_tight = base_width_pct <= cfg.max_base_width_pct
    low_zone_upper = base_low + cfg.buy_zone_fraction * base_width
    no_chase_level = base_low + cfg.no_chase_fraction * base_width

    # Buy zones A/B/C: lower part of the base
    zone_a_low = base_low
    zone_a_high = base_low + 0.15 * base_width
    zone_b_low = zone_a_high
    zone_b_high = base_low + 0.35 * base_width
    zone_c_low = zone_b_high
    zone_c_high = base_low + 0.50 * base_width

    stop = min(base_low - cfg.stop_atr_buffer * atr, recent["low"].min() - 0.05 * atr)
    # Avoid too-far stop if quantile base low is high; use structural base support with buffer
    stop = min(stop, base_low - 0.25 * atr)

    # Relative strength
    stock_r20 = pct_change(tg["close"], 20)
    stock_r10 = pct_change(tg["close"], 10)
    vn_r20 = pct_change(merged["vn_close"], 20)
    vn_r10 = pct_change(merged["vn_close"], 10)
    rs20 = stock_r20 - vn_r20 if pd.notna(stock_r20) and pd.notna(vn_r20) else np.nan
    rs10 = stock_r10 - vn_r10 if pd.notna(stock_r10) and pd.notna(vn_r10) else np.nan
    sector_r20 = sector_returns.get(sector, np.nan)
    sector_rs = stock_r20 - sector_r20 if pd.notna(stock_r20) and pd.notna(sector_r20) else np.nan

    # Market red/stock holds
    last_vn_ret = float(vnindex["close"].iloc[-1] / vnindex["close"].iloc[-2] - 1) if len(vnindex) >= 2 else np.nan
    market_red_holds = pd.notna(last_vn_ret) and last_vn_ret < -0.005 and today_ret > last_vn_ret + 0.006

    # Anomaly / behavior detection
    high_vol_today = last["volume"] > cfg.volume_anomaly_mult * avg_volume_20
    very_high_vol_today = last["volume"] > cfg.strong_volume_mult * avg_volume_20
    body_close_pos = close_position(last)
    lower_wick = (min(last["open"], last["close"]) - last["low"]) / max(last["high"] - last["low"], 0.01)
    closes_weak = body_close_pos < 0.45
    closes_strong = body_close_pos > 0.62

    # absorption in last 10 days: high volume but price does not collapse
    last10 = tg.iloc[-10:].copy()
    vol_ref = avg_volume_20
    absorption_days = 0
    shakeout_days = 0
    low_volume_pullback_days = 0
    for _, r in last10.iterrows():
        r_ret = (r["close"] / tg.loc[tg["date"] < r["date"], "close"].iloc[-1] - 1) if len(tg.loc[tg["date"] < r["date"]]) else 0
        r_pos = close_position(r)
        near_support = r["low"] <= base_low + 0.25 * base_width
        if r["volume"] > cfg.volume_anomaly_mult * vol_ref and r_ret > -0.025 and r["close"] >= base_low - 0.3 * atr:
            absorption_days += 1
        if r["low"] < base_low - 0.15 * atr and r["close"] > base_low and r["volume"] > 1.25 * vol_ref:
            shakeout_days += 1
        if r_ret < 0 and r["volume"] < 0.85 * vol_ref and r["close"] >= base_low:
            low_volume_pullback_days += 1

    # Compression: recent 10-day range vs previous 20-day range
    r10_range = (tg.iloc[-10:]["high"].max() - tg.iloc[-10:]["low"].min()) / close
    r20_prev_range = (tg.iloc[-30:-10]["high"].max() - tg.iloc[-30:-10]["low"].min()) / close if len(tg) >= 30 else np.nan
    compression = pd.notna(r20_prev_range) and r10_range < 0.75 * r20_prev_range

    # Breakout / distribution
    prior_high = float(tg.iloc[-cfg.base_window - 1 : -1]["high"].max()) if len(tg) > cfg.base_window + 1 else float(recent["high"].max())
    breakout = close > prior_high and high_vol_today and closes_strong
    runup_60 = pct_change(tg["close"], 60)
    far_from_base_low = (close - base_low) / base_width if base_width else 0
    distribution = (
        (pd.notna(runup_60) and runup_60 > 0.20 and very_high_vol_today and closes_weak)
        or (close > no_chase_level and very_high_vol_today and closes_weak)
    )

    # Price location for red-base style
    in_red_buy_zone = base_low <= close <= zone_b_high
    in_zone_c = zone_c_low < close <= zone_c_high
    is_red_day = today_ret <= cfg.red_day_threshold
    no_chase = close > no_chase_level or today_ret > 0.025 or breakout
    near_resistance = close >= base_high - 0.2 * atr

    # Scoring A: Big money potential / liquidity / playground - 15
    score_a = 0.0
    notes: List[str] = []
    warnings: List[str] = []
    if liquidity_pass:
        score_a += 5; notes.append("Thanh khoản/giá trị giao dịch đủ để dòng tiền lớn quan sát.")
    else:
        warnings.append("Thanh khoản dưới ngưỡng cấu hình; khó vào/ra quy mô lớn.")
    if avg_value_20 > avg_value_60 * 1.10:
        score_a += 3; notes.append("Giá trị giao dịch 20 phiên tăng so với 60 phiên.")
    elif avg_value_20 > avg_value_60 * 0.85:
        score_a += 1.5
    if sector != "Unknown":
        score_a += 2
    if base_mid >= 8:  # avoid extreme penny; simple proxy
        score_a += 2
    if len(tg) >= cfg.min_sessions:
        score_a += 3
    score_a = min(score_a, 15)

    # B: Accumulation / absorption - 25
    score_b = 0.0
    if in_base and base_tight:
        score_b += 5; notes.append("Có nền giá tương đối rõ và chưa biến động quá rộng.")
    elif in_base:
        score_b += 3; notes.append("Giá còn nằm trong vùng nền nhưng nền chưa thật chặt.")
    if compression:
        score_b += 4; notes.append("Biên độ dao động đang siết lại.")
    if absorption_days >= 2:
        score_b += 6; notes.append(f"Có {absorption_days} phiên hấp thụ: volume tăng nhưng giá không giảm tương ứng.")
    elif absorption_days == 1:
        score_b += 3; notes.append("Có 1 phiên hấp thụ cung đáng chú ý.")
    if shakeout_days >= 1:
        score_b += 5; notes.append("Có tín hiệu rũ cung/false breakdown quanh nền.")
    if low_volume_pullback_days >= 2:
        score_b += 3; notes.append("Các nhịp đỏ gần đây có volume thấp, cung bán suy yếu.")
    if close >= base_low and close <= base_high:
        score_b += 2
    score_b = min(score_b, 25)

    # C: Relative strength - 15
    score_c = 0.0
    if pd.notna(rs20) and rs20 > 0:
        score_c += 5; notes.append("Mạnh hơn VNIndex trong 20 phiên.")
    if pd.notna(rs10) and rs10 > 0:
        score_c += 3; notes.append("Mạnh hơn VNIndex trong 10 phiên.")
    if market_red_holds:
        score_c += 4; notes.append("Thị trường đỏ nhưng cổ phiếu giữ giá tốt hơn.")
    if pd.notna(sector_rs) and sector_rs > 0:
        score_c += 3; notes.append("Mạnh hơn trung bình ngành.")
    score_c = min(score_c, 15)

    # D: Red-base setup - 20
    score_d = 0.0
    if in_red_buy_zone:
        score_d += 7; notes.append("Giá đang ở vùng thấp của nền: phù hợp phong cách mua đỏ/mua nền.")
    elif in_zone_c:
        score_d += 4; notes.append("Giá ở nửa thấp của nền nhưng không còn vùng đẹp nhất.")
    if is_red_day and in_base:
        score_d += 4; notes.append("Phiên hiện tại đang đỏ/không xanh mạnh trong vùng nền.")
    if lower_wick > 0.35 and close >= base_low:
        score_d += 4; notes.append("Có rút chân quanh hỗ trợ nền.")
    if not no_chase and not near_resistance:
        score_d += 3
    if atr / close < 0.06:
        score_d += 2; notes.append("Biên độ rủi ro theo ATR không quá lớn.")
    score_d = min(score_d, 20)

    # E: Risk / no-chase - 10
    score_e = 10.0
    if no_chase:
        score_e -= 4; warnings.append("Không mua xanh/đuổi: giá đã xa vùng mua đỏ hoặc tăng mạnh trong phiên.")
    if near_resistance:
        score_e -= 2; warnings.append("Giá đang sát kháng cự/đỉnh nền, không còn lợi thế mua thấp.")
    if distribution:
        score_e -= 6; warnings.append("Cảnh báo phân phối: volume lớn vùng cao nhưng giá yếu.")
    if close < stop:
        score_e -= 6; warnings.append("Giá đã thủng vùng dừng lỗ cấu trúc.")
    score_e = max(0.0, min(score_e, 10.0))

    # F: Fundamentals + expectations - 15
    score_f, f_notes = score_fundamentals(ticker, fundamentals)
    notes.extend(f_notes)

    total_score = min(100.0, score_a + score_b + score_c + score_d + score_e + score_f)

    # Phase classification
    if distribution:
        phase = "Cảnh báo phân phối"
        signal = "Distribution Warning"
        action = "Không mua mới"
    elif close < stop:
        phase = "Thủng nền/suy yếu"
        signal = "Base Breakdown"
        action = "Loại hoặc chờ tạo nền mới"
    elif breakout:
        phase = "Đã kéo/breakout"
        signal = "No Chase / Wait Retest"
        action = "Không mua xanh; chờ retest/nền mới"
    elif shakeout_days >= 1 and in_base:
        phase = "Rũ cung trong nền"
        signal = "Shakeout Buy Zone"
        action = "Canh mua đỏ/thăm dò nếu giữ nền"
    elif absorption_days >= 2 and in_base and (in_red_buy_zone or in_zone_c):
        phase = "Gom hàng trong nền"
        signal = "Red Base Accumulation"
        action = "Canh đỏ mua vùng nền thấp"
    elif in_base and base_tight:
        phase = "Tạo nền/siết nền"
        signal = "Early Watch"
        action = "Theo dõi, chỉ mua khi về vùng thấp"
    else:
        phase = "Chưa rõ"
        signal = "Neutral"
        action = "Chờ tín hiệu rõ hơn"

    # Risk/reward: target = base high for early base buy; stop below base
    buy_ref = min(max(close, zone_a_low), zone_b_high) if in_red_buy_zone else (zone_b_high if close < zone_b_high else close)
    target_1 = base_high
    risk = max(buy_ref - stop, 0.01)
    reward = max(target_1 - buy_ref, 0.0)
    rr = reward / risk if risk > 0 else np.nan

    # Confidence based on total + risk context
    confidence = max(0, min(95, round(total_score * 0.8 + (10 if score_b >= 16 else 0) + (5 if score_c >= 8 else 0) - (10 if distribution else 0))))

    # Output fields
    not_buy_when = []
    if close > no_chase_level:
        not_buy_when.append(f"giá > {safe_round_price(no_chase_level)}")
    if near_resistance:
        not_buy_when.append(f"sát kháng cự {safe_round_price(base_high)}")
    if today_ret > 0.025:
        not_buy_when.append("nến xanh mạnh trong phiên")
    if breakout:
        not_buy_when.append("đã breakout/kéo xa, chờ retest")
    if not not_buy_when:
        not_buy_when.append(f"giá vượt {safe_round_price(no_chase_level)} hoặc xanh mạnh")

    invalidation = f"Đóng cửa dưới {safe_round_price(stop)} hoặc thủng nền {safe_round_price(base_low)} với volume lớn."

    return {
        "date": last["date"],
        "ticker": ticker,
        "sector": sector,
        "close": safe_round_price(close),
        "score": round(total_score, 1),
        "confidence": confidence,
        "phase": phase,
        "signal": signal,
        "action": action,
        "base_low": safe_round_price(base_low),
        "base_high": safe_round_price(base_high),
        "base_zone": format_range(base_low, base_high),
        "buy_zone_a": format_range(zone_a_low, zone_a_high),
        "buy_zone_b": format_range(zone_b_low, zone_b_high),
        "buy_zone_c": format_range(zone_c_low, zone_c_high),
        "red_buy_zone": format_range(zone_a_low, zone_b_high),
        "stop_loss": f"<{safe_round_price(stop)}",
        "stop_loss_value": safe_round_price(stop),
        "no_buy_when": "; ".join(not_buy_when),
        "invalidation": invalidation,
        "rr_to_base_high": round(rr, 2) if pd.notna(rr) and np.isfinite(rr) else np.nan,
        "avg_value_20": avg_value_20,
        "avg_volume_20": avg_volume_20,
        "atr": safe_round_price(atr),
        "today_ret_pct": round(today_ret * 100, 2),
        "rs20_pct": round(rs20 * 100, 2) if pd.notna(rs20) else np.nan,
        "rs10_pct": round(rs10 * 100, 2) if pd.notna(rs10) else np.nan,
        "score_a_big_money": round(score_a, 1),
        "score_b_accumulation": round(score_b, 1),
        "score_c_relative_strength": round(score_c, 1),
        "score_d_red_setup": round(score_d, 1),
        "score_e_risk": round(score_e, 1),
        "score_f_fundamental_expectation": round(score_f, 1),
        "notes": notes[:12],
        "warnings": warnings[:8],
    }


def run_scan(prices: pd.DataFrame, vnindex: pd.DataFrame, fundamentals: pd.DataFrame, cfg: ScanConfig) -> Tuple[pd.DataFrame, Dict[str, Dict]]:
    sector_returns = compute_sector_returns(prices, cfg.short_window)
    rows: List[Dict] = []
    details: Dict[str, Dict] = {}
    for ticker, tg in prices.groupby("ticker"):
        result = scan_one_ticker(tg, vnindex, fundamentals, sector_returns, cfg)
        if result is not None:
            rows.append({k: v for k, v in result.items() if k not in ["notes", "warnings"]})
            details[ticker] = result
    out = pd.DataFrame(rows)
    if out.empty:
        return out, details
    # Prioritize actionable red-base opportunities, then score
    phase_rank = {
        "Rũ cung trong nền": 1,
        "Gom hàng trong nền": 2,
        "Tạo nền/siết nền": 3,
        "Đã kéo/breakout": 4,
        "Chưa rõ": 5,
        "Cảnh báo phân phối": 6,
        "Thủng nền/suy yếu": 7,
    }
    out["phase_rank"] = out["phase"].map(phase_rank).fillna(9)
    out = out.sort_values(["phase_rank", "score", "rr_to_base_high"], ascending=[True, False, False]).drop(columns=["phase_rank"]).reset_index(drop=True)
    return out, details


# -----------------------------
# Plotting
# -----------------------------
def make_candlestick_chart(tg: pd.DataFrame, detail: Dict) -> go.Figure:
    tg = tg.sort_values("date").tail(100)
    fig = go.Figure()
    fig.add_trace(
        go.Candlestick(
            x=tg["date"],
            open=tg["open"],
            high=tg["high"],
            low=tg["low"],
            close=tg["close"],
            name="Giá",
        )
    )
    # Add volume as bar on secondary y axis manually
    fig.add_trace(
        go.Bar(
            x=tg["date"],
            y=tg["volume"],
            name="Volume",
            yaxis="y2",
            opacity=0.25,
        )
    )

    base_low = detail["base_low"]
    base_high = detail["base_high"]
    stop = detail["stop_loss_value"]
    # Parse zones
    for y, label, dash in [
        (base_low, "Đáy nền", "dot"),
        (base_high, "Đỉnh nền", "dot"),
        (stop, "Cắt lỗ", "dash"),
    ]:
        if pd.notna(y):
            fig.add_hline(y=y, line_dash=dash, annotation_text=label, annotation_position="top left")

    fig.update_layout(
        height=560,
        xaxis_rangeslider_visible=False,
        yaxis=dict(title="Giá"),
        yaxis2=dict(title="Volume", overlaying="y", side="right", showgrid=False, rangemode="tozero"),
        margin=dict(l=10, r=10, t=40, b=10),
        legend=dict(orientation="h"),
    )
    return fig


# -----------------------------
# Streamlit UI
# -----------------------------
def main():
    st.set_page_config(page_title="Smart Money Red Base Scanner", layout="wide")
    st.title("Smart Money Red Base Scanner – Auto Data MVP V0.5")
    st.caption("Tự tải dữ liệu thị trường, quét dấu hiệu tay to gom hàng, ưu tiên mua đỏ trong nền, không mua xanh/đu break.")

    with st.expander("Triết lý hệ thống", expanded=False):
        st.markdown(
            """
            **Mục tiêu:** phát hiện sớm cổ phiếu có dấu hiệu bất thường: hấp thụ cung, rũ cung, siết nền, mạnh hơn VNIndex, sau đó tính **vùng mua đỏ** và **vùng cắt lỗ khi thủng nền**.

            **Không phải khuyến nghị đầu tư.** App chỉ là công cụ sàng lọc xác suất. Người dùng cần kiểm tra lại dữ liệu, tin tức, thanh khoản và quản trị vốn.
            """
        )

    st.sidebar.header("1) Dữ liệu tự động")
    data_mode = st.sidebar.radio(
        "Chọn nguồn dữ liệu",
        ["Tự động: Vnstock → Yahoo fallback", "Tự động: Vnstock", "Tự động: Yahoo", "Upload thủ công", "Demo"],
        index=0,
    )

    provider_map = {
        "Tự động: Vnstock → Yahoo fallback": "Auto",
        "Tự động: Vnstock": "Vnstock",
        "Tự động: Yahoo": "Yahoo",
    }
    provider = provider_map.get(data_mode, "Auto")
    vnstock_source = st.sidebar.selectbox("Nguồn Vnstock", ["VCI", "KBS"], index=0, disabled=not data_mode.startswith("Tự động"))

    lookback_days = st.sidebar.slider("Số ngày lịch sử cần tải", 180, 900, 420, 30, disabled=not data_mode.startswith("Tự động"))
    end_dt = st.sidebar.date_input("Ngày kết thúc", value=date.today(), disabled=not data_mode.startswith("Tự động"))
    start_dt = end_dt - timedelta(days=int(lookback_days))

    preset = st.sidebar.selectbox(
        "Rổ mã tự quét",
        ["Top thanh khoản mặc định", "VN30-like", "Tự lấy danh sách từ Vnstock nếu được", "Tự nhập mã"],
        index=0,
        disabled=not data_mode.startswith("Tự động"),
    )
    if preset == "VN30-like":
        default_universe = VN30_LIKE_TICKERS
    elif preset == "Tự lấy danh sách từ Vnstock nếu được":
        default_universe = try_auto_list_symbols(120)
    elif preset == "Tự nhập mã":
        default_universe = ["HPG", "SSI", "FPT", "MBB", "TCB", "VCB", "VND", "VCI", "DGC", "KBC"]
    else:
        default_universe = DEFAULT_TICKERS

    ticker_text = st.sidebar.text_area(
        "Danh sách mã tự tải/quét",
        value=", ".join(default_universe),
        height=120,
        disabled=not data_mode.startswith("Tự động"),
        help="Có thể sửa trực tiếp: HPG, SSI, FPT... App sẽ tự tải giá từng mã và VNINDEX.",
    )
    max_symbols = st.sidebar.slider("Giới hạn số mã tải", 10, 300, min(80, len(parse_ticker_text(ticker_text)) or 80), 10, disabled=not data_mode.startswith("Tự động"))

    price_file = st.sidebar.file_uploader("Upload prices.csv/xlsx", type=["csv", "xlsx", "xls"], disabled=data_mode != "Upload thủ công")
    index_file = st.sidebar.file_uploader("Upload vnindex.csv/xlsx", type=["csv", "xlsx", "xls"], disabled=data_mode != "Upload thủ công")
    fundamental_file = st.sidebar.file_uploader("Upload fundamentals.csv/xlsx tùy chọn", type=["csv", "xlsx", "xls"], disabled=data_mode not in ["Upload thủ công"])

    st.sidebar.header("2) Cấu hình quét")
    min_value_bil = st.sidebar.number_input("GTGD bình quân 20 phiên tối thiểu (tỷ VND)", min_value=0.0, value=5.0, step=1.0)
    base_window = st.sidebar.slider("Số phiên xác định nền", 30, 90, 60, 5)
    volume_mult = st.sidebar.slider("Ngưỡng volume bất thường", 1.1, 3.0, 1.5, 0.1)
    max_base_width_pct = st.sidebar.slider("Biên độ nền tối đa (%)", 10, 50, 28, 1) / 100

    cfg = ScanConfig(
        min_avg_value_20=min_value_bil * 1_000_000_000,
        base_window=base_window,
        volume_anomaly_mult=volume_mult,
        max_base_width_pct=max_base_width_pct,
    )

    try:
        if data_mode == "Demo":
            prices, vnindex, fundamentals = generate_demo_data()
            st.info("Đang dùng dữ liệu demo để minh họa logic. Chuyển sang chế độ Tự động để app tự tải dữ liệu thị trường.")

        elif data_mode == "Upload thủ công":
            if price_file is None or index_file is None:
                st.warning("Chế độ upload thủ công cần tối thiểu 2 file: prices và VNIndex. Nếu muốn app tự tải, đổi nguồn dữ liệu sang chế độ Tự động.")
                st.stop()
            prices = preprocess_prices(read_csv_excel(price_file))
            vnindex = preprocess_index(read_csv_excel(index_file))
            fundamentals = preprocess_fundamentals(read_csv_excel(fundamental_file)) if fundamental_file is not None else preprocess_fundamentals(None)

        else:
            tickers = parse_ticker_text(ticker_text)[:max_symbols]
            if not tickers:
                st.warning("Chưa có mã nào để tải. Hãy nhập danh sách mã hoặc chọn rổ mặc định.")
                st.stop()
            start_str = pd.Timestamp(start_dt).strftime("%Y-%m-%d")
            end_str = pd.Timestamp(end_dt + timedelta(days=1)).strftime("%Y-%m-%d")  # include end date for Yahoo-style APIs

            with st.spinner(f"Đang tự tải dữ liệu {len(tickers)} mã + VNINDEX từ {data_mode}..."):
                idx_df, idx_err = fetch_index_auto(start_str, end_str, provider, vnstock_source)
                if idx_df.empty:
                    st.error(f"Không tự tải được VNINDEX. Lỗi: {idx_err}")
                    st.stop()

                parts = []
                failed = []
                progress = st.progress(0, text="Đang tải mã...")
                for i, t in enumerate(tickers, start=1):
                    df_one, err = fetch_one_symbol(t, start_str, end_str, provider, vnstock_source)
                    if not df_one.empty:
                        parts.append(df_one)
                    if err:
                        failed.append(err)
                    progress.progress(i / len(tickers), text=f"Đã xử lý {i}/{len(tickers)} mã")
                progress.empty()

                if not parts:
                    st.error("Không tải được mã cổ phiếu nào. Hãy thử đổi nguồn Vnstock KBS/VCI, dùng Yahoo fallback, hoặc kiểm tra Internet.")
                    if failed:
                        with st.expander("Chi tiết lỗi tải dữ liệu"):
                            st.write(failed[:30])
                    st.stop()

                prices = preprocess_prices(pd.concat(parts, ignore_index=True))
                vnindex = idx_df
                fundamentals = build_neutral_fundamentals(sorted(prices["ticker"].unique()))

                st.success(f"Đã tự tải {prices['ticker'].nunique()} mã, {len(prices):,} dòng giá và VNINDEX. Không cần upload file.")
                if failed:
                    st.warning(f"Có {len(failed)} mã không tải được. App bỏ qua các mã đó và vẫn quét phần còn lại.")
                    with st.expander("Xem lỗi các mã không tải được"):
                        st.write(failed[:80])
                st.caption("BCTC/kỳ vọng đang để điểm trung tính nếu chưa có nguồn tự động ổn định. Bản này ưu tiên phát hiện dòng tiền, nền giá, rũ cung, vùng mua đỏ và cắt lỗ tự động.")

    except Exception as e:
        st.error(f"Lỗi đọc/tải dữ liệu: {e}")
        st.stop()

    scan_df, details = run_scan(prices, vnindex, fundamentals, cfg)

    if scan_df.empty:
        st.warning("Không có mã nào đủ dữ liệu để quét. Kiểm tra lại số phiên hoặc dữ liệu đầu vào.")
        st.stop()

    # Overview metrics
    c1, c2, c3, c4 = st.columns(4)
    c1.metric("Số mã đã quét", f"{len(scan_df)}")
    c2.metric("Cơ hội mua đỏ", f"{scan_df['signal'].isin(['Red Base Accumulation', 'Shakeout Buy Zone']).sum()}")
    c3.metric("Cảnh báo phân phối", f"{(scan_df['signal'] == 'Distribution Warning').sum()}")
    c4.metric("Điểm cao nhất", f"{scan_df['score'].max():.1f}")

    st.subheader("Bảng quét tổng hợp")
    display_cols = [
        "ticker", "sector", "score", "confidence", "phase", "signal", "action", "close",
        "base_zone", "red_buy_zone", "buy_zone_a", "buy_zone_b", "buy_zone_c", "stop_loss",
        "rr_to_base_high", "today_ret_pct", "rs20_pct", "no_buy_when",
    ]
    st.dataframe(
        scan_df[display_cols],
        use_container_width=True,
        hide_index=True,
        column_config={
            "score": st.column_config.ProgressColumn("Điểm", min_value=0, max_value=100),
            "confidence": st.column_config.ProgressColumn("Độ tin cậy", min_value=0, max_value=100),
            "rr_to_base_high": st.column_config.NumberColumn("R/R tới đỉnh nền", format="%.2f"),
            "today_ret_pct": st.column_config.NumberColumn("% hôm nay", format="%.2f"),
            "rs20_pct": st.column_config.NumberColumn("RS20 vs VNIndex %", format="%.2f"),
        },
    )

    # Download result
    csv = scan_df.to_csv(index=False).encode("utf-8-sig")
    st.download_button("Tải kết quả scan CSV", data=csv, file_name="smart_money_red_base_scan.csv", mime="text/csv")

    st.subheader("Chi tiết từng mã")
    ticker_choice = st.selectbox("Chọn mã để xem chi tiết", scan_df["ticker"].tolist())
    detail = details[ticker_choice]
    tg = prices.loc[prices["ticker"] == ticker_choice].copy()

    left, right = st.columns([1.45, 1])
    with left:
        st.plotly_chart(make_candlestick_chart(tg, detail), use_container_width=True)

    with right:
        st.markdown(f"### {ticker_choice} – {detail['phase']}")
        st.markdown(f"**Điểm:** {detail['score']}/100  \n**Độ tin cậy:** {detail['confidence']}%  \n**Tín hiệu:** {detail['signal']}  \n**Hành động:** {detail['action']}")
        st.markdown("#### Vùng giá")
        st.write(f"- Vùng nền: **{detail['base_zone']}**")
        st.write(f"- Vùng mua đỏ tổng: **{detail['red_buy_zone']}**")
        st.write(f"- Vùng A đẹp nhất: **{detail['buy_zone_a']}**")
        st.write(f"- Vùng B chấp nhận: **{detail['buy_zone_b']}**")
        st.write(f"- Vùng C thăm dò: **{detail['buy_zone_c']}**")
        st.write(f"- Cắt lỗ: **{detail['stop_loss']}**")
        st.write(f"- Không mua khi: **{detail['no_buy_when']}**")
        st.write(f"- Điều kiện vô hiệu: **{detail['invalidation']}**")

        st.markdown("#### Điểm thành phần")
        comp = pd.DataFrame(
            [
                ["Tay to có thể quan tâm", detail["score_a_big_money"], 15],
                ["Gom hàng/hấp thụ", detail["score_b_accumulation"], 25],
                ["Sức mạnh tương đối", detail["score_c_relative_strength"], 15],
                ["Setup mua đỏ", detail["score_d_red_setup"], 20],
                ["Rủi ro/không mua đuổi", detail["score_e_risk"], 10],
                ["Nền tảng & kỳ vọng", detail["score_f_fundamental_expectation"], 15],
            ],
            columns=["Nhóm", "Điểm", "Tối đa"],
        )
        st.dataframe(comp, hide_index=True, use_container_width=True)

    st.markdown("#### Bằng chứng")
    if detail["notes"]:
        for n in detail["notes"]:
            st.write(f"- {n}")
    else:
        st.write("- Chưa có bằng chứng đủ mạnh.")

    if detail["warnings"]:
        st.markdown("#### Cảnh báo")
        for w in detail["warnings"]:
            st.warning(w)

    with st.expander("Format dữ liệu đầu vào"):
        st.markdown(
            """
            **prices.csv/xlsx** bắt buộc có cột:
            `date, ticker, open, high, low, close, volume`  
            Nên có thêm: `value, sector`.

            **vnindex.csv/xlsx** bắt buộc có cột:
            `date, open, high, low, close`  
            Nên có thêm: `volume, value`.

            **fundamentals.csv/xlsx** tùy chọn:
            `ticker, revenue_growth_yoy, profit_growth_yoy, roe, debt_to_equity, operating_cashflow_positive, expectation_score`

            `expectation_score` có thể chấm thủ công 0–10 hoặc 0–15 theo câu chuyện ngành/doanh nghiệp.
            """
        )


if __name__ == "__main__":
    main()
