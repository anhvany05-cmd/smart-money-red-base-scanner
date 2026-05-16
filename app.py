from __future__ import annotations

import re
import urllib.parse
import xml.etree.ElementTree as ET
from concurrent.futures import ThreadPoolExecutor, as_completed
from datetime import date, datetime, timedelta, timezone
from typing import Dict, List, Tuple

import numpy as np
import pandas as pd
import plotly.graph_objects as go
import requests
import streamlit as st

st.set_page_config(page_title="Market Winner Scanner V2.0 Late Cycle Guard", layout="wide", initial_sidebar_state="expanded")

# ============================================================
# UNIVERSE
# ============================================================
CORE_69 = """
HPG, SSI, FPT, MBB, TCB, VCB, BID, CTG, VPB, ACB, VIB, STB, SHB, HDB, TPB, LPB, MSB,
VND, VCI, HCM, VIX, MBS, SHS, DGC, DPM, DCM, GAS, PVD, PVS, PLX, MWG, FRT, PNJ, DGW,
MSN, VNM, VRE, VHM, VIC, KDH, NLG, DXG, DIG, CEO, HSG, NKG, GEX, GMD, VSC, SIP, IDC,
KBC, SZC, PVT, HAH, ANV, VHC, PDR, HAG, BSR, POW, REE, PC1, CTR, CMG, EIB, OCB, SAB, BMP
"""

BROAD_180 = """
HPG,HSG,NKG,SMC,TLH,VGS,TVN,SSI,VND,VCI,HCM,VIX,MBS,SHS,FTS,CTS,BSI,ORS,AGR,
FPT,CMG,CTR,ELC,FOX,ITD,MBB,TCB,VCB,BID,CTG,VPB,ACB,VIB,STB,SHB,HDB,TPB,LPB,MSB,EIB,OCB,SSB,NAB,BVB,KLB,
DGC,DPM,DCM,CSV,LAS,PLC,GAS,PVD,PVS,PLX,BSR,OIL,PVT,POW,REE,PC1,GEG,GEX,NT2,QTP,PPC,VSH,TTA,
MWG,FRT,PNJ,DGW,PET,PSD,MSN,VNM,SAB,BMP,DBC,BAF,HAG,PAN,TAR,LTG,VHC,ANV,IDI,FMC,ACL,ASM,
VHM,VIC,VRE,KDH,NLG,DXG,DIG,CEO,PDR,NVL,HDC,HDG,CRE,SCR,TCH,AGG,NTL,IJC,DRH,
KBC,IDC,SZC,SIP,PHR,BCM,VGC,LHG,D2D,GVR,DTD,ITA,ITC,
GMD,VSC,HAH,SCS,SGP,VOS,VTO,VIP,SKG,AST,ACV,HVN,VJC,SAS,
FLC,ROS,DLG,ITA,HQC,LDG,CII,FCN,HHV,LCG,VCG,CTD,HBC,PC1,DPG,C4G,HT1,BCC,CTI,
IMP,DHG,TRA,DVN,DBD,TNH,JVC,DCL,AMV,AAA,APH,NTP,DNP,PTB,TTF,GIL,MSH,TCM,TNG,VGT
"""

SECTOR_MAP = {
    **{x:"Thép" for x in "HPG HSG NKG SMC TLH VGS TVN".split()},
    **{x:"Chứng khoán" for x in "SSI VND VCI HCM VIX MBS SHS FTS CTS BSI ORS AGR".split()},
    **{x:"Công nghệ" for x in "FPT CMG CTR ELC FOX ITD".split()},
    **{x:"Ngân hàng" for x in "MBB TCB VCB BID CTG VPB ACB VIB STB SHB HDB TPB LPB MSB EIB OCB SSB NAB BVB KLB".split()},
    **{x:"Hóa chất/Phân bón" for x in "DGC DPM DCM CSV LAS PLC".split()},
    **{x:"Dầu khí" for x in "GAS PVD PVS PLX BSR OIL PVT".split()},
    **{x:"Điện/Năng lượng" for x in "POW REE PC1 GEG NT2 QTP PPC VSH TTA".split()},
    **{x:"Bán lẻ" for x in "MWG FRT PNJ DGW PET PSD".split()},
    **{x:"Tiêu dùng/Nông nghiệp" for x in "MSN VNM SAB BMP DBC BAF HAG PAN TAR LTG".split()},
    **{x:"Thủy sản" for x in "VHC ANV IDI FMC ACL ASM".split()},
    **{x:"Bất động sản" for x in "VHM VIC VRE KDH NLG DXG DIG CEO PDR NVL HDC HDG CRE SCR TCH AGG NTL IJC DRH".split()},
    **{x:"KCN" for x in "KBC IDC SZC SIP PHR BCM VGC LHG D2D GVR DTD ITA ITC".split()},
    **{x:"Cảng/Logistics/Hàng không" for x in "GMD VSC HAH SCS SGP VOS VTO VIP SKG AST ACV HVN VJC SAS".split()},
    **{x:"Đầu tư công/Xây dựng" for x in "CII FCN HHV LCG VCG CTD HBC DPG C4G HT1 BCC CTI".split()},
    **{x:"Y tế/Dược" for x in "IMP DHG TRA DVN DBD TNH JVC DCL AMV".split()},
    **{x:"Nhựa/Gỗ/Dệt may" for x in "AAA APH NTP DNP PTB TTF GIL MSH TCM TNG VGT".split()},
}

MACRO = {
    "S&P500":"^GSPC", "Nasdaq":"^IXIC", "DowJones":"^DJI", "VIX":"^VIX",
    "Nikkei":"^N225", "HangSeng":"^HSI", "Shanghai":"000001.SS", "KOSPI":"^KS11", "Taiwan":"^TWII", "Singapore":"^STI",
    "WTI":"CL=F", "Brent":"BZ=F", "DXY":"DX-Y.NYB", "US10Y":"^TNX", "Gold":"GC=F",
}

# ============================================================
# BASIC HELPERS
# ============================================================
def clamp(x, a, b):
    try:
        if np.isnan(x):
            return a
    except Exception:
        pass
    return float(max(a, min(b, x)))


def norm_ticker(x: str) -> str:
    return str(x).strip().upper().replace(".VN", "").replace(".HN", "")


def parse_tickers(text: str) -> List[str]:
    out = []
    for x in re.split(r"[,;\n\s]+", str(text)):
        t = norm_ticker(x)
        if t and t not in out:
            out.append(t)
    return out


def unix(d: date) -> int:
    return int(datetime(d.year, d.month, d.day, tzinfo=timezone.utc).timestamp())


def fmt(x):
    if pd.isna(x) or not np.isfinite(x):
        return ""
    return f"{x:.1f}" if x >= 100 else f"{x:.2f}" if x >= 10 else f"{x:.3f}"


def frange(a, b):
    return f"{fmt(a)}–{fmt(b)}" if np.isfinite(a) and np.isfinite(b) else ""


def yahoo_candidates(ticker: str) -> List[str]:
    t = norm_ticker(ticker)
    if t.startswith("^") or "." in t or "=" in t:
        return [t]
    # Yahoo dữ liệu VN không đồng nhất, thử nhiều suffix để tăng độ phủ.
    return [f"{t}.VN", f"{t}.HN"]


# ============================================================
# DATA LOADERS
# ============================================================
@st.cache_data(ttl=900, show_spinner=False)
def fetch_yahoo_symbol(symbol: str, start: date, end: date) -> pd.DataFrame:
    p1, p2 = unix(start), unix(end + timedelta(days=1))
    enc = urllib.parse.quote(symbol, safe="")
    url = f"https://query1.finance.yahoo.com/v8/finance/chart/{enc}?period1={p1}&period2={p2}&interval=1d&events=history"
    r = requests.get(url, headers={"User-Agent":"Mozilla/5.0"}, timeout=10)
    r.raise_for_status()
    js = r.json()
    result = js.get("chart", {}).get("result")
    if not result:
        err = js.get("chart", {}).get("error")
        raise ValueError(f"No data: {err}")
    item = result[0]
    ts = item.get("timestamp") or []
    q = (item.get("indicators", {}).get("quote") or [{}])[0]
    if not ts or not q:
        raise ValueError("Empty timestamp/quote")
    n = len(ts)
    def arr(k):
        v = q.get(k, []) or []
        return v[:n] + [np.nan] * max(0, n - len(v))
    df = pd.DataFrame({
        "date": [datetime.fromtimestamp(x).date() for x in ts],
        "open": arr("open"), "high": arr("high"), "low": arr("low"),
        "close": arr("close"), "volume": arr("volume"),
    }).dropna(subset=["open", "high", "low", "close"])
    if df.empty:
        raise ValueError("Empty frame")
    df["date"] = pd.to_datetime(df["date"])
    for c in ["open", "high", "low", "close", "volume"]:
        df[c] = pd.to_numeric(df[c], errors="coerce").fillna(0)
    return df.sort_values("date").drop_duplicates("date").reset_index(drop=True)


# ============================================================
# LIVE PULSE HELPERS
# ============================================================
def vn_now() -> datetime:
    return datetime.utcnow() + timedelta(hours=7)


def vn_market_status(now: datetime | None = None) -> Tuple[str, str]:
    now = now or vn_now()
    wd = now.weekday()  # Mon=0
    hm = now.hour * 60 + now.minute
    if wd >= 5:
        return "Cuối tuần", "VN đóng cửa nhưng vĩ mô/thế giới vẫn biến động. Ưu tiên theo dõi Live Macro Pulse."
    if 9*60 <= hm <= 11*60+30:
        return "Đang giao dịch sáng", "Có thể dùng để canh đỏ/rung lắc trong phiên."
    if 13*60 <= hm <= 15*60:
        return "Đang giao dịch chiều", "Ưu tiên quan sát phản ứng cuối phiên và giữ nền."
    if hm < 9*60:
        return "Trước giờ mở cửa", "Dùng để chuẩn bị watchlist, chưa vội đặt mua."
    if 11*60+30 < hm < 13*60:
        return "Nghỉ trưa", "Đánh giá lại biến động sáng, chờ phiên chiều xác nhận."
    return "Sau giờ đóng cửa", "Phù hợp chạy scan cuối ngày và lập kế hoạch mua đỏ ngày kế tiếp."


@st.cache_data(ttl=180, show_spinner=False)
def fetch_yahoo_intraday_symbol(symbol: str, range_str: str = "5d", interval: str = "5m") -> pd.DataFrame:
    enc = urllib.parse.quote(symbol, safe="")
    url = f"https://query1.finance.yahoo.com/v8/finance/chart/{enc}?range={range_str}&interval={interval}&includePrePost=false"
    r = requests.get(url, headers={"User-Agent":"Mozilla/5.0"}, timeout=8)
    r.raise_for_status()
    js = r.json()
    result = js.get("chart", {}).get("result")
    if not result:
        raise ValueError(str(js.get("chart", {}).get("error")))
    item = result[0]
    ts = item.get("timestamp") or []
    q = (item.get("indicators", {}).get("quote") or [{}])[0]
    closes = q.get("close") or []
    opens = q.get("open") or []
    highs = q.get("high") or []
    lows = q.get("low") or []
    vols = q.get("volume") or []
    n = min(len(ts), len(closes))
    if n == 0:
        raise ValueError("empty intraday")
    df = pd.DataFrame({
        "time": [datetime.fromtimestamp(x) for x in ts[:n]],
        "open": opens[:n] + [np.nan] * max(0, n - len(opens)),
        "high": highs[:n] + [np.nan] * max(0, n - len(highs)),
        "low": lows[:n] + [np.nan] * max(0, n - len(lows)),
        "close": closes[:n],
        "volume": vols[:n] + [0] * max(0, n - len(vols)),
    }).dropna(subset=["close"])
    for c in ["open", "high", "low", "close", "volume"]:
        df[c] = pd.to_numeric(df[c], errors="coerce")
    return df.dropna(subset=["close"]).reset_index(drop=True)


def live_macro_pulse() -> Tuple[pd.DataFrame, Dict[str, str]]:
    rows, errors = [], {}
    for name, sym in MACRO.items():
        try:
            df = fetch_yahoo_intraday_symbol(sym, "5d", "5m")
            if df.empty or len(df) < 2:
                continue
            last = float(df.close.iloc[-1])
            prev = float(df.close.iloc[-2])
            day_ref = float(df.close.iloc[max(0, len(df)-79)]) if len(df) > 80 else float(df.close.iloc[0])
            chg_5m = (last / prev - 1) * 100 if prev else 0
            chg_live = (last / day_ref - 1) * 100 if day_ref else 0
            risk = "Trung tính"
            if name == "VIX" and last > 25: risk = "Rủi ro cao"
            elif name == "VIX" and last < 18: risk = "Thuận lợi"
            elif name in ["WTI", "Brent", "DXY", "US10Y"] and chg_live > 1.2: risk = "Áp lực tăng"
            elif name in ["S&P500","Nasdaq","DowJones","Nikkei","HangSeng","KOSPI","Taiwan","Singapore"] and chg_live > 0.6: risk = "Hỗ trợ"
            elif name in ["S&P500","Nasdaq","DowJones","Nikkei","HangSeng","KOSPI","Taiwan","Singapore"] and chg_live < -0.8: risk = "Gây áp lực"
            rows.append({"market": name, "symbol": sym, "last": round(last, 3), "chg_5m_%": round(chg_5m, 2), "chg_live_%": round(chg_live, 2), "state": risk})
        except Exception as e:
            errors[name] = str(e)[:120]
    return pd.DataFrame(rows), errors


NEWS_QUERIES = {
    "Lạm phát/Fed/Lãi suất": "inflation OR CPI OR Federal Reserve OR interest rates stock market",
    "Chiến tranh/Địa chính trị": "war OR sanctions OR missile OR geopolitical risk oil stock market",
    "Dầu/Logistics": "oil prices OR Brent OR WTI OR shipping disruption market",
    "Châu Á": "Asia stocks Nikkei Hang Seng Kospi Taiwan market",
    "Việt Nam/VNIndex": "Vietnam stock market VNIndex foreign investors",
}
NEGATIVE_NEWS_WORDS = ["war","missile","attack","sanction","tariff","inflation","selloff","crash","recession","oil jumps","surge","pandemic","default","crisis"]
POSITIVE_NEWS_WORDS = ["rally","gains","eases","cut rates","rate cut","stimulus","peace","deal","recovery","cooling inflation"]


@st.cache_data(ttl=900, show_spinner=False)
def fetch_google_news_rss(query: str, n: int = 5) -> List[Dict[str, str]]:
    q = urllib.parse.quote(query)
    url = f"https://news.google.com/rss/search?q={q}&hl=en-US&gl=US&ceid=US:en"
    r = requests.get(url, headers={"User-Agent":"Mozilla/5.0"}, timeout=8)
    r.raise_for_status()
    root = ET.fromstring(r.content)
    out = []
    for item in root.findall(".//item")[:n]:
        title = (item.findtext("title") or "").strip()
        link = (item.findtext("link") or "").strip()
        pub = (item.findtext("pubDate") or "").strip()
        txt = title.lower()
        shock = 0
        shock += sum(1 for w in NEGATIVE_NEWS_WORDS if w in txt)
        shock -= sum(1 for w in POSITIVE_NEWS_WORDS if w in txt)
        out.append({"title": title, "published": pub, "shock_score": shock, "link": link})
    return out


def collect_news_pulse(max_per_group: int = 4) -> pd.DataFrame:
    rows = []
    for group, query in NEWS_QUERIES.items():
        try:
            for x in fetch_google_news_rss(query, max_per_group):
                x["group"] = group
                rows.append(x)
        except Exception as e:
            rows.append({"group": group, "title": f"Không tải được RSS: {e}", "published": "", "shock_score": 0, "link": ""})
    if not rows:
        return pd.DataFrame()
    df = pd.DataFrame(rows)
    return df.sort_values(["shock_score", "published"], ascending=[False, False]).reset_index(drop=True)


def inject_meta_refresh(seconds: int):
    st.markdown(f"<meta http-equiv='refresh' content='{int(seconds)}'>", unsafe_allow_html=True)


def fetch_one_ticker(ticker: str, days: int, end: date) -> Tuple[str, pd.DataFrame, str]:
    start = end - timedelta(days=int(days * 1.9) + 45)
    errors = []
    for sym in yahoo_candidates(ticker):
        try:
            df = fetch_yahoo_symbol(sym, start, end)
            if len(df) < max(55, min(110, days // 2)):
                raise ValueError(f"too few rows {len(df)}")
            t = norm_ticker(ticker)
            df["ticker"] = t
            df["sector"] = SECTOR_MAP.get(t, "Khác")
            df["value"] = df["close"] * df["volume"]
            return t, df, ""
        except Exception as e:
            errors.append(f"{sym}: {e}")
    return norm_ticker(ticker), pd.DataFrame(), " | ".join(errors[:2])


def fetch_universe_parallel(tickers: List[str], days: int, end: date, max_n: int, workers: int = 8) -> Tuple[pd.DataFrame, List[str]]:
    chosen = [norm_ticker(t) for t in tickers if norm_ticker(t)][:max_n]
    rows, errs = [], []
    prog = st.progress(0, text=f"Đang tải {len(chosen)} mã...")
    done = 0
    workers = int(max(1, min(workers, 12)))
    with ThreadPoolExecutor(max_workers=workers) as ex:
        futs = {ex.submit(fetch_one_ticker, t, days, end): t for t in chosen}
        for fut in as_completed(futs):
            t = futs[fut]
            try:
                name, df, err = fut.result()
                if not df.empty:
                    rows.append(df)
                elif err:
                    errs.append(f"{t}: {err}")
            except Exception as e:
                errs.append(f"{t}: {e}")
            done += 1
            prog.progress(done / max(1, len(chosen)), text=f"Đã xử lý {done}/{len(chosen)} mã | tải thành công {len(rows)}")
    prog.empty()
    if not rows:
        return pd.DataFrame(), errs
    return pd.concat(rows, ignore_index=True), errs


def demo_data(tickers, days=180):
    rng = np.random.default_rng(7)
    dates = pd.bdate_range(end=pd.Timestamp.today().normalize(), periods=days)
    rows = []
    for i, t in enumerate(tickers):
        px = (20 + i * 1.8) * np.cumprod(1 + rng.normal(0.0005, 0.017, len(dates)))
        vol = rng.integers(500000, 10000000, len(dates)).astype(float)
        if i % 5 == 0:
            vol[-25:] *= rng.uniform(1.25, 2.2)
        for d, c, v in zip(dates, px, vol):
            o = c * (1 + rng.normal(0, 0.006))
            h = max(o, c) * (1 + abs(rng.normal(0, 0.008)))
            l = min(o, c) * (1 - abs(rng.normal(0, 0.008)))
            rows.append([d, t, o, h, l, c, v, SECTOR_MAP.get(t, "Khác")])
    df = pd.DataFrame(rows, columns="date ticker open high low close volume sector".split())
    df["value"] = df["close"] * df["volume"]
    return df


def load_file(f):
    if f is None:
        return pd.DataFrame()
    return pd.read_csv(f) if f.name.lower().endswith("csv") else pd.read_excel(f)


def standardize_prices(df):
    if df is None or df.empty:
        return pd.DataFrame()
    df = df.copy(); df.columns = [str(c).strip().lower() for c in df.columns]
    aliases = {
        "ticker":["ticker","symbol","mã","ma","code"], "date":["date","ngày","ngay","time"],
        "open":["open","o"], "high":["high","h"], "low":["low","l"], "close":["close","c","price"],
        "volume":["volume","vol","kl"], "sector":["sector","ngành","nganh"],
    }
    ren = {}
    for k, opts in aliases.items():
        for o in opts:
            if o in df.columns:
                ren[o] = k; break
    df = df.rename(columns=ren)
    miss = {"date","ticker","open","high","low","close","volume"} - set(df.columns)
    if miss:
        raise ValueError(f"Thiếu cột {miss}")
    df["date"] = pd.to_datetime(df["date"]); df["ticker"] = df["ticker"].map(norm_ticker)
    for c in ["open","high","low","close","volume"]:
        df[c] = pd.to_numeric(df[c], errors="coerce")
    if "sector" not in df:
        df["sector"] = df["ticker"].map(SECTOR_MAP).fillna("Khác")
    df["value"] = df["close"] * df["volume"]
    return df.dropna(subset=["date","ticker","close"])

# ============================================================
# ANALYSIS ENGINE
# ============================================================
def enrich(d: pd.DataFrame) -> pd.DataFrame:
    d = d.sort_values("date").copy()
    d["ret5"] = d["close"].pct_change(5)
    d["ret20"] = d["close"].pct_change(20)
    d["ret60"] = d["close"].pct_change(60)
    d["value"] = d["close"] * d["volume"]
    d["vol20"] = d["volume"].rolling(20).mean(); d["val20"] = d["value"].rolling(20).mean(); d["val60"] = d["value"].rolling(60).mean()
    tr = pd.concat([(d.high-d.low), (d.high-d.close.shift()).abs(), (d.low-d.close.shift()).abs()], axis=1).max(axis=1)
    d["atr14"] = tr.rolling(14).mean()
    mfm = ((d.close-d.low)-(d.high-d.close))/(d.high-d.low).replace(0, np.nan)
    d["cmf20"] = (mfm.fillna(0)*d.volume).rolling(20).sum()/d.volume.rolling(20).sum().replace(0, np.nan)
    d["obv"] = (np.sign(d.close.diff()).fillna(0)*d.volume).cumsum()
    return d


def market_proxy(prices):
    p = prices.sort_values(["ticker","date"]).copy()
    p["norm"] = p.groupby("ticker")["close"].transform(lambda s: s / s.iloc[0] if len(s) else s)
    m = p.groupby("date")["norm"].mean().reset_index()
    m["close"] = 1000 * m["norm"]
    m["open"] = m.close.shift(1).fillna(m.close)
    m["high"] = m[["open","close"]].max(axis=1); m["low"] = m[["open","close"]].min(axis=1); m["volume"] = 0
    return m[["date","open","high","low","close","volume"]]


def macro_gate(end_date, days, market):
    score, notes, errs = 50.0, [], []
    start = end_date - timedelta(days=int(days * 1.8) + 40)
    for name, sym in MACRO.items():
        try:
            g = fetch_yahoo_symbol(sym, start, end_date)
            if len(g) < 30:
                continue
            r5 = g.close.iloc[-1]/g.close.iloc[-6]-1 if len(g) >= 6 else 0
            r20 = g.close.iloc[-1]/g.close.iloc[-21]-1 if len(g) >= 21 else 0
            ma20 = g.close.tail(20).mean(); last = g.close.iloc[-1]
            if name in ["S&P500","Nasdaq","DowJones","Nikkei","HangSeng","KOSPI","Taiwan","Singapore"]:
                score += (1 if r5 > 0 else 0) + (1 if r20 > 0 else 0) + (1 if last > ma20 else 0)
            if name == "VIX":
                if last < 18: score += 6; notes.append("VIX thấp")
                elif last > 25: score -= 10; notes.append("VIX cao")
            if name in ["WTI","Brent"] and r20 > 0.12: score -= 3; notes.append(f"{name} tăng nhanh")
            if name == "DXY":
                if r20 > 0.03: score -= 5; notes.append("DXY tăng mạnh")
                elif r20 < -0.02: score += 3
            if name == "US10Y" and r20 > 0.06: score -= 4; notes.append("US10Y tăng")
        except Exception as e:
            errs.append(f"{name}: {e}")
    if market is not None and len(market) >= 25:
        m = market.sort_values("date")
        r5 = m.close.iloc[-1]/m.close.iloc[-6]-1 if len(m) >= 6 else 0
        r20 = m.close.iloc[-1]/m.close.iloc[-21]-1 if len(m) >= 21 else 0
        score += 5 if r5 > 0 else -4 if r5 < -0.025 else 0
        score += 5 if r20 > 0 else 0
    score = clamp(score, 0, 100)
    if score >= 72: gate, mode = "MỞ CỬA GIẢI NGÂN CÓ CHỌN LỌC", "Normal"
    elif score >= 58: gate, mode = "MỞ MỘT PHẦN - CHỌN CORE/WATCH", "Reduced"
    elif score >= 45: gate, mode = "THẬN TRỌNG - CHỈ THĂM DÒ NHỎ", "Small"
    else: gate, mode = "ĐÓNG CỬA MUA MỚI - CHỜ THIÊN THỜI", "Off"
    return {"macro_score":round(score,1), "macro_gate":gate, "risk_mode":mode, "notes":notes[:6], "errors":errs[:20]}


def choose_vn_base(d: pd.DataFrame, cfg: Dict) -> Tuple[pd.DataFrame, float, float, float, str]:
    """Chọn nền phù hợp biên dao động cổ phiếu Việt Nam.

    Không dùng min-low/max-high của 60 phiên vì sẽ làm nền quá rộng khi có một nhịp rũ hoặc đỉnh cũ xa.
    Cách mới: thử nhiều cửa sổ gần nhất, dùng quantile để bỏ outlier, ưu tiên nền có close hiện tại nằm trong/ gần nền.
    """
    windows = [20, 25, 30, 35, 45, 60]
    max_w = int(cfg.get("base_window", 45))
    windows = [w for w in windows if w <= max_w and len(d) >= w]
    if not windows:
        w = min(len(d), max(20, len(d)))
        windows = [w]
    close = float(d.close.iloc[-1])
    best = None
    cap_pct = float(cfg.get("vn_base_cap_pct", 16.0))
    for w in windows:
        b = d.tail(w).copy()
        raw_low = float(b.low.min())
        raw_high = float(b.high.max())
        # Quantile nền: bỏ các đuôi quá cực đoan để tránh nền bị rộng kiểu 36k-70k.
        q_low = float(b.low.quantile(0.12))
        q_high = float(b.high.quantile(0.88))
        close_low = float(b.close.quantile(0.10))
        close_high = float(b.close.quantile(0.90))
        base_low = min(q_low, close_low)
        base_high = max(q_high, close_high)
        if base_low <= 0:
            continue
        # Nếu vẫn quá rộng, cắt về vùng hỗ trợ gần + trần nền hợp lý cho cổ phiếu VN.
        base_high = min(base_high, base_low * (1 + cap_pct / 100.0))
        rng = (base_high / base_low - 1) * 100 if base_low > 0 else 999
        in_or_near = base_low * 0.985 <= close <= base_high * 1.035
        # Ưu tiên nền hẹp, gần giá hiện tại, cửa sổ không quá ngắn.
        score = rng + (0 if in_or_near else 12) + abs(w-35)*0.06
        if best is None or score < best[0]:
            best = (score, b, base_low, base_high, rng, f"{w} phiên, quantile 12–88%, cap {cap_pct:.0f}%")
    if best is None:
        b = d.tail(min(35, len(d))).copy()
        base_low = float(b.low.tail(20).min())
        base_high = float(b.high.tail(20).max())
        rng = (base_high / base_low - 1) * 100 if base_low > 0 else 999
        return b, base_low, base_high, rng, "fallback"
    _, b, base_low, base_high, rng, method = best
    return b, float(base_low), float(base_high), float(rng), method


def analyze_one(t, g, market, cfg):
    d = enrich(g)
    last = d.iloc[-1]
    raw_base, raw_base_low, raw_base_high, raw_base_range_pct, raw_base_method = choose_vn_base(d, cfg)
    close = float(last.close)
    atr = float(last.atr14) if np.isfinite(last.atr14) and last.atr14 > 0 else max(close * 0.018, (raw_base_high-raw_base_low)/8)
    atr_pct = atr / close * 100 if close > 0 else np.nan

    # ========================================================
    # V1.9 PRACTICAL ZONE ENGINE
    # Không dùng nền cũ nếu giá đã rời nền quá xa. Ví dụ VIC giá 228k mà nền cũ 130k:
    # app phải báo CHỜ NỀN MỚI/PULLBACK GẦN, không được đưa vùng mua 130k phi thực tế.
    # ========================================================
    max_action_pullback_pct = float(cfg.get("max_action_pullback_pct", 7.0))
    max_action_pullback = max_action_pullback_pct / 100.0
    no_chase_pct = float(cfg.get("vn_no_chase_pct", 6.0)) / 100.0

    ema10 = float(d.close.ewm(span=10, adjust=False).mean().iloc[-1])
    ema20 = float(d.close.ewm(span=20, adjust=False).mean().iloc[-1])
    ema50 = float(d.close.ewm(span=50, adjust=False).mean().iloc[-1]) if len(d) >= 55 else float(d.close.rolling(min(30, len(d))).mean().iloc[-1])
    ret20 = float(d.close.iloc[-1] / d.close.iloc[-21] - 1) if len(d) >= 22 else 0.0
    ret60 = float(d.close.iloc[-1] / d.close.iloc[-61] - 1) if len(d) >= 62 else 0.0
    # V2.0 LATE CYCLE GUARD
    # Không nhầm cổ phiếu đã tăng nhiều lần với cổ phiếu còn vùng mua tốt.
    cycle_lookback = min(252, max(2, len(d) - 1))
    cycle_ref = float(d.close.iloc[-cycle_lookback]) if cycle_lookback < len(d) else float(d.close.iloc[0])
    cycle_return_pct = (close / cycle_ref - 1) * 100 if cycle_ref > 0 else 0.0
    low_lookback = d.tail(min(252, len(d)))
    low_lookback_min = float(low_lookback.low.min()) if len(low_lookback) else close
    runup_from_low_pct = (close / low_lookback_min - 1) * 100 if low_lookback_min > 0 else 0.0
    ema100 = float(d.close.ewm(span=100, adjust=False).mean().iloc[-1]) if len(d) >= 80 else ema50
    ema200 = float(d.close.ewm(span=200, adjust=False).mean().iloc[-1]) if len(d) >= 120 else ema100
    ema50_gap_pct = (close / ema50 - 1) * 100 if ema50 > 0 else 0.0
    ema100_gap_pct = (close / ema100 - 1) * 100 if ema100 > 0 else 0.0
    ema200_gap_pct = (close / ema200 - 1) * 100 if ema200 > 0 else 0.0
    recent10 = d.tail(min(10, len(d)))
    recent20 = d.tail(min(20, len(d)))
    recent30 = d.tail(min(30, len(d)))
    new_base_range_pct = np.nan
    new_base_mature = False
    if len(recent20) >= 15:
        nb_low = float(recent20.low.quantile(0.12))
        nb_high = float(recent20.high.quantile(0.88))
        new_base_range_pct = (nb_high / nb_low - 1) * 100 if nb_low > 0 else np.nan
        # Nền mới hợp lệ sau siêu tăng phải hẹp, đi ngang đủ phiên và không còn dựng đứng.
        new_base_mature = bool(np.isfinite(new_base_range_pct) and new_base_range_pct <= float(cfg.get("late_new_base_max_pct", 10.0)) and abs(ret20*100) <= 12 and close <= nb_high * 1.03)
    recent_high = float(recent20.high.max()) if len(recent20) else close
    recent_low_q = float(recent20.low.quantile(0.25)) if len(recent20) else close
    swing_low10 = float(recent10.low.min()) if len(recent10) else close
    pullback_floor = close * (1 - max_action_pullback)

    old_base_far = False
    if raw_base_high > 0:
        old_base_far = close > raw_base_high * (1 + no_chase_pct) or close > raw_base_low * (1 + float(cfg.get("vn_base_cap_pct", 16.0))/100.0 + no_chase_pct)
    trend_up = close > ema20 and ema20 >= ema50 * 0.985 and ret20 > 0.03

    zone_model = "Nền gần hiện tại"
    zone_valid = True
    practical_note = ""

    if old_base_far or (trend_up and close > raw_base_high * 1.04):
        # Cổ đã chạy khỏi nền cũ: chỉ dùng hỗ trợ động gần giá hiện tại.
        supports = [ema10, ema20, recent_low_q, swing_low10]
        supports = [float(x) for x in supports if np.isfinite(x) and x > 0 and x < close * 0.997]
        viable = [x for x in supports if x >= pullback_floor]
        if viable:
            base_low = max(viable)  # hỗ trợ gần nhất dưới giá, không phải nền cũ quá xa
            base_high = max(recent_high, close)
            base_method = f"V1.9 hỗ trợ động gần giá: EMA/low 10–20 phiên; bỏ nền cũ {fmt(raw_base_low)}–{fmt(raw_base_high)}"
            zone_model = "Pullback gần trong trend"
            base_range_pct = (base_high / base_low - 1) * 100 if base_low > 0 else np.nan
        else:
            # Không có hỗ trợ thực tế trong phạm vi chờ. Không giả vờ có điểm mua.
            base_low = pullback_floor
            base_high = close
            base_method = f"V1.9 không có hỗ trợ gần; nền cũ quá xa {fmt(raw_base_low)}–{fmt(raw_base_high)}"
            base_range_pct = max_action_pullback_pct
            zone_model = "Không có vùng mua thực tế"
            zone_valid = False
            practical_note = f"Giá đã rời nền cũ; không chờ về {fmt(raw_base_low)}. Chỉ xem lại khi tạo nền mới hoặc pullback không quá {max_action_pullback_pct:.1f}% từ giá hiện tại."
    else:
        base_low, base_high, base_range_pct, base_method = raw_base_low, raw_base_high, raw_base_range_pct, raw_base_method

    base_mid = (base_low + base_high) / 2

    # Vùng mua đỏ thực tế: nếu là nền thì bám đáy nền; nếu là trend thì bám hỗ trợ động gần.
    max_buy_pct = min(float(cfg.get("vn_red_zone_pct", 4.5)) / 100.0, max_action_pullback)
    if zone_model == "Pullback gần trong trend":
        zone_a_pct = 0.010
        zone_b_pct = min(0.026, max_buy_pct)
        zone_c_pct = min(0.040, max_buy_pct + 0.012)
        atr_a, atr_b, atr_c = 0.55, 1.05, 1.55
    else:
        zone_a_pct = float(cfg.get("zone_a_pct", 1.8)) / 100.0
        zone_b_pct = min(float(cfg.get("zone_b_pct", 3.2)) / 100.0, max_buy_pct)
        zone_c_pct = min(float(cfg.get("zone_c_pct", 4.8)) / 100.0, max_buy_pct + 0.015)
        atr_a, atr_b, atr_c = 0.9, 1.6, 2.4

    zA1 = base_low
    zA2 = min(base_low * (1 + zone_a_pct), base_low + atr_a * atr, close * 0.995, base_high)
    zB1 = zA2
    zB2 = min(base_low * (1 + zone_b_pct), base_low + atr_b * atr, close * 0.995, base_high)
    zC1 = zB2
    zC2 = min(base_low * (1 + zone_c_pct), base_low + atr_c * atr, close * 0.998, base_high)
    if zA2 <= zA1: zA2 = min(base_low * 1.010, close * 0.995, base_high)
    if zB2 <= zB1: zB2 = min(max(zB1, base_low * 1.020), close * 0.995, base_high)
    if zC2 <= zC1: zC2 = min(max(zC1, base_low * 1.032), close * 0.998, base_high)

    # Nếu vùng mua vẫn quá xa giá hiện tại, cấm báo mua.
    distance_to_zone_pct = (close / zB2 - 1) * 100 if zB2 > 0 else np.nan
    if np.isfinite(distance_to_zone_pct) and distance_to_zone_pct > max_action_pullback_pct:
        zone_valid = False
        practical_note = f"Vùng mua tính ra cách giá hiện tại {distance_to_zone_pct:.1f}%, vượt ngưỡng thực tế {max_action_pullback_pct:.1f}%. Chờ nền mới."

    stop_pct = float(cfg.get("vn_stop_pct", 2.2)) / 100.0
    stop_atr_mult = float(cfg.get("stop_atr_mult", 0.8))
    stop = min(base_low * (1 - stop_pct), base_low - stop_atr_mult * atr)
    max_stop_pct = float(cfg.get("vn_max_stop_pct", 5.0)) / 100.0
    stop = max(stop, base_low * (1 - max_stop_pct))

    # R/R tính theo điểm mua giả định giữa vùng A/B, không phải theo giá hiện tại nếu giá đang xa vùng mua.
    entry_ref = (zA1 + zB2) / 2 if zB2 > zA1 else min(close, zB2)
    target = base_high
    if target <= entry_ref:
        target = max(recent_high, close * 1.035)
    risk_from_entry = (entry_ref / stop - 1) * 100 if stop > 0 else np.nan
    reward_from_entry = (target / entry_ref - 1) * 100 if entry_ref > 0 else np.nan
    rr_entry = reward_from_entry / risk_from_entry if risk_from_entry and risk_from_entry > 0 else np.nan
    risk_from_close = (close / stop - 1) * 100 if stop > 0 else np.nan

    # Relative strength vs market proxy
    rs20 = 0.0; alpha = 50.0
    if market is not None and len(market):
        m = pd.merge(d[["date","close"]], market[["date","close"]].rename(columns={"close":"mclose"}), on="date", how="inner")
        if len(m) >= 25:
            rs20 = (m.close.iloc[-1]/m.close.iloc[-21]-1) - (m.mclose.iloc[-1]/m.mclose.iloc[-21]-1)
            alpha = clamp(50 + 300 * rs20, 0, 100)

    val20 = float(last.val20) if np.isfinite(last.val20) else 0
    val60 = float(last.val60) if np.isfinite(last.val60) else 0
    v5 = d.value.tail(5).mean()
    vr5 = v5/val20 if val20 > 0 else 1
    vr20 = val20/val60 if val60 > 0 else 1
    cmf = float(last.cmf20) if np.isfinite(last.cmf20) else 0
    recent = d.tail(20)
    upv = recent.loc[recent.close >= recent.open, "value"].sum()/recent.value.sum() if recent.value.sum() > 0 else .5
    obv_s = (d.obv.iloc[-1] - d.obv.iloc[-21])/max(1, abs(d.obv.iloc[-21])) if len(d) > 22 and d.obv.iloc[-21] != 0 else 0
    mf = 0
    mf += 6 if vr5 >= 1.25 else 4 if vr5 >= 1.05 else 2 if vr5 >= .85 else 0
    mf += 5 if vr20 >= 1.2 else 3 if vr20 >= 1.0 else 1
    mf += 5 if upv >= .58 else 3 if upv >= .52 else 1
    mf += 5 if cmf >= .12 else 3 if cmf >= .03 else 0
    mf += 4 if obv_s > 0 else 0
    mf = clamp(mf, 0, 25)
    mf_state = "Dòng tiền vào rõ" if mf >= 18 else "Dòng tiền tích lũy" if mf >= 13 else "Dòng tiền trung bình" if mf >= 8 else "Dòng tiền yếu"

    vol20 = float(last.vol20) if np.isfinite(last.vol20) else 0
    vol_ratio = float(last.volume/vol20) if vol20 > 0 else 1
    close_pos = (last.close-last.low)/(last.high-last.low) if last.high > last.low else .5
    in_base = base_low <= close <= base_high*1.01
    low_part = close <= zB2
    too_far = (not zone_valid) or close > zC2 or close > zB2 * (1 + no_chase_pct)
    tight = base_range_pct <= cfg["max_base_range_pct"] and in_base and zone_model == "Nền gần hiện tại"
    shake = zone_model == "Nền gần hiện tại" and last.low < base_low*1.012 and close_pos > .55 and vol_ratio >= cfg["volume_spike"]
    absorb = zone_model == "Nền gần hiện tại" and vol_ratio >= cfg["volume_spike"] and last.close >= last.open*.988 and in_base
    dist = close > base_mid and vol_ratio >= 1.8 and close_pos < .35 and raw_base.close.iloc[-1]/max(1e-9, raw_base.close.iloc[0])-1 > .12

    liq = 10 if val20 >= cfg["min_val"]*1e9 else 5 if val20 >= cfg["min_val"]*.5e9 else 0
    base_score = 15 if tight else 9 if zone_model == "Pullback gần trong trend" and zone_valid else 5 if base_range_pct <= cfg["max_base_range_pct"] + 6 else 0
    acc = (8 if absorb else 0) + (7 if shake else 0) + (5 if low_part and zone_valid else 0) + (5 if rs20 > 0 else 0)
    no_chase = 10 if zone_valid and not too_far else 2 if zone_model == "Không có vùng mua thực tế" else 4
    risk_score = 10 if np.isfinite(risk_from_entry) and risk_from_entry <= 5.5 and np.isfinite(rr_entry) and rr_entry >= 1.25 else 8 if np.isfinite(risk_from_entry) and risk_from_entry <= 7 and np.isfinite(rr_entry) and rr_entry >= 1.0 else 4
    total = clamp(liq + base_score + acc + no_chase + risk_score + mf*1.2, 0, 100)

    if dist:
        phase, sig = "Cảnh báo phân phối", "Distribution Warning"
    elif not zone_valid and old_base_far:
        phase, sig = "Đã rời nền/không có điểm mua thực tế", "Wait New Base"
    elif zone_model == "Pullback gần trong trend":
        phase, sig = "Trend tăng - chờ pullback ngắn", "Trend Pullback Watch"
    elif shake:
        phase, sig = "Rũ cung trong nền", "Shakeout Buy Zone"
    elif absorb:
        phase, sig = "Gom hàng trong nền", "Red Base Accumulation"
    elif tight:
        phase, sig = "Tạo nền/siết nền", "Early Watch"
    else:
        phase, sig = "Chưa rõ", "Watch only"

    if dist:
        action = "TRÁNH MUA"
    elif not zone_valid:
        action = "KHÔNG THỰC TẾ - CHỜ NỀN MỚI/PULLBACK GẦN"
    elif mf < 8:
        action = "CHƯA ƯU TIÊN - DÒNG TIỀN YẾU"
    elif close <= zA2 and close >= stop:
        action = "VÙNG A - CÓ THỂ CANH MUA ĐỎ"
    elif close <= zB2 and close >= stop:
        action = "VÙNG B - CHỈ THĂM DÒ"
    elif close <= zC2 and close >= stop:
        action = "VÙNG C - THẬN TRỌNG"
    elif too_far:
        action = "KHÔNG ĐU XANH - CHỜ VỀ VÙNG GẦN"
    else:
        action = "THEO DÕI - CHỜ RUNG LẮC"

    conc = clamp(total*.42 + mf*1.9 + (8 if phase in ["Gom hàng trong nền","Rũ cung trong nền","Trend tăng - chờ pullback ngắn"] else 0) + (8 if zone_valid and close <= zB2 else 0) - (20 if not zone_valid else 0) - (12 if dist else 0), 0, 100)
    clabel = "CORE" if conc >= 78 and mf >= 15 and zone_valid and not dist else "WATCH" if conc >= 62 and mf >= 10 and not dist else "EARLY"
    victory = clamp(.29*conc + .25*mf*4 + .20*alpha + .16*no_chase*10 + .10*risk_score*10, 0, 100)
    vlabel = "ỨNG VIÊN VƯỢT THỊ TRƯỜNG MẠNH" if victory >= 80 else "ỨNG VIÊN TỐT" if victory >= 68 else "THEO DÕI" if victory >= 55 else "CHƯA ĐỦ CHUẨN"

    # ========================================================
    # V2.0 LATE CYCLE / MULTIBAGGER GUARD
    # Cổ đã tăng quá xa như VIC tăng nhiều lần: không được đưa vào nhóm mua mới.
    # Dòng tiền mạnh ở vùng cao có thể là phân phối, FOMO hoặc kéo giữ giá, không phải lợi thế mua đỏ.
    # ========================================================
    hard_return = float(cfg.get("late_hard_return_pct", 180.0))
    hard_runup = float(cfg.get("late_hard_runup_pct", 260.0))
    warn_return = float(cfg.get("late_warn_return_pct", 100.0))
    warn_runup = float(cfg.get("late_warn_runup_pct", 150.0))
    hard_ma_gap = float(cfg.get("late_hard_ma200_gap_pct", 85.0))
    warn_ma_gap = float(cfg.get("late_warn_ma50_gap_pct", 28.0))
    blowoff = (ret20 * 100 >= 35 and vol_ratio >= 1.5) or (ret60 * 100 >= 80)
    late_cycle_hard_ban = bool((cycle_return_pct >= hard_return) or (runup_from_low_pct >= hard_runup) or (ema200_gap_pct >= hard_ma_gap) or blowoff)
    late_cycle_warning = bool(late_cycle_hard_ban or cycle_return_pct >= warn_return or runup_from_low_pct >= warn_runup or ema50_gap_pct >= warn_ma_gap)
    late_cycle_state = "Bình thường"
    if late_cycle_hard_ban:
        late_cycle_state = "CẤM MUA MỚI - cuối sóng/quá nóng"
        zone_valid = False
        phase = "Late-cycle/quá nóng"
        sig = "Late Cycle Hard Ban"
        action = "CẤM MUA - ĐÃ TĂNG QUÁ XA, CHỜ NỀN MỚI"
        practical_note = (
            f"Cổ đã tăng quá xa: tăng {cycle_return_pct:.1f}% trong {cycle_lookback} phiên, "
            f"tăng {runup_from_low_pct:.1f}% từ đáy {cycle_lookback} phiên, cách EMA50 {ema50_gap_pct:.1f}%. "
            "Không có lợi thế mua mới; chỉ xem lại khi tạo nền mới thực sự gần giá hiện tại."
        )
        conc = min(conc, 35)
        victory = min(victory, 48)
        clabel = "NO BUY"
        vlabel = "RỦI RO CUỐI SÓNG"
    elif late_cycle_warning and not new_base_mature:
        late_cycle_state = "Cảnh báo muộn sóng - chưa có nền mới"
        action = "KHÔNG MUA MỚI - CHỜ NỀN MỚI XÁC NHẬN"
        phase = "Muộn sóng/chưa có nền mới"
        sig = "Late Cycle Watch"
        conc = min(conc, 58)
        victory = min(victory, 62)
        if clabel == "CORE":
            clabel = "WATCH"
        if "ỨNG VIÊN VƯỢT" in vlabel:
            vlabel = "THEO DÕI RỦI RO"
    elif late_cycle_warning and new_base_mature:
        late_cycle_state = "Đã tăng mạnh nhưng có nền mới cần theo dõi"
        if clabel == "CORE":
            clabel = "WATCH"
        action = "CHỈ THEO DÕI NỀN MỚI - KHÔNG ĐU XANH"

    if zone_valid:
        red_zone_text = frange(zA1, zB2)
        buy_a_text = frange(zA1, zA2)
        buy_b_text = frange(zB1, zB2)
        buy_c_text = frange(zC1, zC2)
        buy_trigger = f"Chỉ mua khi đỏ/rung lắc trong {red_zone_text}, ưu tiên vùng A/B; không đóng cửa dưới {fmt(stop)}"
        no_buy_when = f"Không mua xanh; không mua nếu cách vùng mua đỏ > {max_action_pullback_pct:.1f}%; kháng cự gần {fmt(target)}"
    else:
        red_zone_text = "Chưa có vùng mua đỏ thực tế"
        buy_a_text = buy_b_text = buy_c_text = "Chờ nền mới/pullback gần"
        buy_trigger = practical_note or "Không mua hiện tại. Chờ cổ phiếu tạo nền mới hoặc pullback gần MA/ATR với volume cạn."
        no_buy_when = f"Không mua đuổi. Nền cũ quá xa; vùng cũ {fmt(raw_base_low)}–{fmt(raw_base_high)} không còn dùng làm điểm mua."

    invalidation = f"Đóng cửa dưới {fmt(stop)} hoặc thủng hỗ trợ {fmt(base_low)} với volume lớn" if zone_valid else "Chưa có điểm mua nên chưa có điểm cắt lỗ thực chiến; chỉ đặt stop sau khi có nền mới."
    position_plan = "30% vùng A, thêm 20–30% nếu giữ nền/rũ cung; không trung bình giá xuống" if zone_valid else "Không giải ngân. Chờ nền mới 5–10 phiên hoặc pullback gần rồi quét lại."
    why = [mf_state, phase, f"Mô hình vùng: {zone_model}", f"Biên vùng {base_range_pct:.1f}%", f"ATR {atr_pct:.1f}%"]
    if zone_valid and close <= zB2: why.append("Giá ở vùng mua đỏ")
    if rs20 > 0: why.append("Mạnh hơn thị trường")
    if too_far: why.append("Giá xa vùng mua")
    if not zone_valid: why.append("Loại vùng mua phi thực tế")
    if late_cycle_warning: why.append(late_cycle_state)
    if dist: why.append("Cảnh báo phân phối")

    return {
        "ticker":t, "sector":g.sector.iloc[-1] if "sector" in g else SECTOR_MAP.get(t,"Khác"), "close":close,
        "phase":phase, "signal":sig, "action_decision":action, "Điểm tổng":round(total,1),
        "victory_score":round(victory,1), "victory_label":vlabel, "concentration_score":round(conc,1), "concentration_label":clabel,
        "money_flow_score":round(mf,1), "money_flow_state":mf_state, "value_ratio_5_20":round(vr5,2), "value_ratio_20_60":round(vr20,2),
        "up_value_ratio_pct":round(upv*100,1), "cmf20":round(cmf,3), "rs20_vs_market_pct":round(rs20*100,2),
        "zone_model":zone_model, "zone_valid":zone_valid, "distance_to_buy_zone_pct":round(distance_to_zone_pct,2) if np.isfinite(distance_to_zone_pct) else np.nan,
        "base_zone":frange(base_low,base_high), "old_base_zone":frange(raw_base_low,raw_base_high), "base_range_pct":round(base_range_pct,2), "atr14_pct":round(atr_pct,2) if np.isfinite(atr_pct) else np.nan, "base_method":base_method,
        "red_buy_zone":red_zone_text, "buy_zone_A":buy_a_text, "buy_zone_B":buy_b_text, "buy_zone_C":buy_c_text,
        "stop_loss":fmt(stop) if zone_valid else "Chờ nền mới", "target_near":fmt(target), "risk_pct_from_close":round(risk_from_close,2) if np.isfinite(risk_from_close) else np.nan,
        "risk_pct_from_buy_zone":round(risk_from_entry,2) if np.isfinite(risk_from_entry) else np.nan,
        "reward_pct_from_buy_zone":round(reward_from_entry,2) if np.isfinite(reward_from_entry) else np.nan,
        "reward_pct_to_base_high":round(reward_from_entry,2) if np.isfinite(reward_from_entry) else np.nan, "rr_to_base_high":round(rr_entry,2) if np.isfinite(rr_entry) else np.nan,
        "no_buy_when":no_buy_when,
        "buy_trigger":buy_trigger,
        "invalidation":invalidation,
        "position_plan":position_plan,
        "why_focus":" | ".join(why), "distribution_warning":dist,
        "late_cycle_warning":late_cycle_warning, "late_cycle_hard_ban":late_cycle_hard_ban, "late_cycle_state":late_cycle_state,
        "cycle_return_pct":round(cycle_return_pct,1), "runup_from_low_pct":round(runup_from_low_pct,1),
        "ema50_gap_pct":round(ema50_gap_pct,1), "ema200_gap_pct":round(ema200_gap_pct,1),
        "new_base_range_pct":round(new_base_range_pct,1) if np.isfinite(new_base_range_pct) else np.nan,
        "new_base_mature":new_base_mature,
        "_base_low":base_low, "_base_high":target, "_red_high":zB2, "_stop":stop,
    }

def analyze_prices(prices, market, cfg):
    rows, details, errors = [], {}, []
    for t, g in prices.groupby("ticker"):
        try:
            gs = g.sort_values("date")
            row = analyze_one(t, gs, market, cfg)
            rows.append(row)
            details[t] = enrich(gs)
        except Exception as e:
            errors.append(f"{t}: {e}")
    return pd.DataFrame(rows), details, errors


def sector_map_df(res):
    if res.empty: return pd.DataFrame()
    g = res.groupby("sector").agg(
        so_ma=("ticker","count"), diem_dong_tien_tb=("money_flow_score","mean"),
        diem_co_dac_tb=("concentration_score","mean"), ung_vien=("concentration_label", lambda s:int(s.isin(["CORE","WATCH"]).sum())),
        rs20_tb=("rs20_vs_market_pct","mean"),
    ).reset_index()
    g["sector_state"] = np.where(g.diem_dong_tien_tb >= 15, "Ngành hút tiền", np.where(g.diem_dong_tien_tb >= 10, "Ngành tích lũy", "Ngành yếu/trung tính"))
    return g.sort_values(["diem_dong_tien_tb","diem_co_dac_tb"], ascending=False)


def focus_df(res, macro, n):
    r = res.copy(); mode = macro.get("risk_mode", "Normal")
    if mode == "Off":
        r["action_decision"] = "CHỜ THỊ TRƯỜNG - VĨ MÔ XẤU"; r["concentration_score"] *= .72
    elif mode == "Small":
        r.loc[r.action_decision.str.contains("CÓ THỂ|CHỈ", regex=True), "action_decision"] = "CHỈ THĂM DÒ NHỎ - CHỜ THIÊN THỜI"; r["concentration_score"] *= .86
    if "late_cycle_hard_ban" in r.columns:
        r = r[~r["late_cycle_hard_ban"]]
    c = r[~r.distribution_warning].sort_values(["victory_score","concentration_score","money_flow_score","rr_to_base_high"], ascending=False)
    cols = ["ticker","sector","concentration_label","concentration_score","victory_score","victory_label","money_flow_score","money_flow_state","action_decision","phase","close","red_buy_zone","stop_loss","rr_to_base_high","why_focus"]
    return c.head(n)[cols]


def chart(g,row):
    d = g.tail(110)
    fig = go.Figure(go.Candlestick(x=d.date, open=d.open, high=d.high, low=d.low, close=d.close, name="Giá"))
    for y, name, dash in [(row._base_low,"Đáy nền","dot"),(row._base_high,"Đỉnh nền","dot"),(row._red_high,"Mua đỏ tối đa","dash"),(row._stop,"Cắt lỗ","dash")]:
        fig.add_hline(y=float(y), line_dash=dash, annotation_text=name)
    fig.update_layout(height=520, xaxis_rangeslider_visible=False, margin=dict(l=10,r=10,t=30,b=10))
    return fig

# ============================================================
# UI
# ============================================================
st.title("Smart Money Red Base Scanner – Late Cycle Guard MVP V2.0")
st.caption("App sống theo thị trường: tự làm mới dữ liệu, theo dõi vĩ mô toàn cầu, tin tức cuối tuần và chỉ mở tín hiệu mua khi thiên thời không xấu.")
with st.expander("Triết lý hệ thống"):
    st.write("Không mua xanh/đu break. Ưu tiên cổ phiếu có dòng tiền, ngành có tiền, vĩ mô không xấu, giá ở vùng đỏ trong nền. Bản V2.0 sửa điểm chí mạng: không được nhầm dòng tiền vào ở cuối sóng với cơ hội mua. Cổ phiếu đã tăng quá xa/nhân nhiều lần trong 6–12 tháng sẽ bị chặn mua mới, dù dòng tiền còn mạnh. App chỉ theo dõi lại khi tạo nền mới thực sự gần giá hiện tại.")

with st.sidebar:
    st.header("0) Live Pulse")
    auto_refresh = st.checkbox("Tự làm mới app khi đang mở", value=False)
    refresh_sec = st.selectbox("Chu kỳ refresh", [60, 180, 300, 900, 1800], index=2, format_func=lambda x: f"{x//60} phút" if x>=60 else f"{x} giây")
    show_live_macro = st.checkbox("Hiện Live Macro Pulse", value=True)
    show_news_pulse = st.checkbox("Hiện tin tức vĩ mô nóng", value=True)
    if auto_refresh:
        inject_meta_refresh(refresh_sec)
        st.caption(f"Đang tự refresh mỗi {refresh_sec//60 if refresh_sec>=60 else refresh_sec} {'phút' if refresh_sec>=60 else 'giây'} khi tab này còn mở.")
    status, status_note = vn_market_status()
    st.info(f"Giờ VN: {vn_now().strftime('%H:%M:%S %d/%m/%Y')} | {status}")
    st.caption(status_note)

    st.header("1) Dữ liệu & độ bao phủ")
    data_mode = st.radio("Nguồn dữ liệu", ["Tự động Yahoo Direct", "Upload thủ công", "Demo"], index=0)
    universe_preset = st.selectbox("Rổ mã", ["Rộng 150+ mã thanh khoản/đại diện ngành", "Core 69 mã", "Tùy chỉnh"], index=0)
    if universe_preset == "Rộng 150+ mã thanh khoản/đại diện ngành":
        default_text = BROAD_180
    elif universe_preset == "Core 69 mã":
        default_text = CORE_69
    else:
        default_text = CORE_69
    ticker_text = st.text_area("Danh sách mã", default_text, height=150)
    scan_mode = st.radio("Chế độ quét", ["Đãi cát 2 vòng - khuyên dùng", "Một vòng đầy đủ", "Test nhanh"], index=0)
    end_date = st.date_input("Ngày kết thúc", value=date.today())
    if scan_mode == "Đãi cát 2 vòng - khuyên dùng":
        scan_limit = st.slider("Vòng 1: số mã quét rộng", 30, 180, 100, step=10)
        quick_days = st.slider("Vòng 1: số ngày nhanh", 90, 180, 120, step=30)
        deep_top = st.slider("Vòng 2: số mã phân tích sâu", 10, 60, 30, step=5)
        deep_days = st.slider("Vòng 2: số ngày phân tích sâu", 150, 360, 240, step=30)
    elif scan_mode == "Một vòng đầy đủ":
        scan_limit = st.slider("Số mã quét", 10, 180, 60, step=10)
        deep_days = st.slider("Số ngày lịch sử", 120, 420, 240, step=30)
        quick_days = deep_days; deep_top = scan_limit
    else:
        scan_limit = st.slider("Số mã test", 5, 30, 10, step=5)
        quick_days = 120; deep_days = 180; deep_top = scan_limit
    workers = st.slider("Số luồng tải song song", 2, 12, 8, step=1)
    run = st.button("🚀 Quét đãi cát tìm vàng", type="primary", use_container_width=True)
    st.header("2) Cấu hình lọc")
    min_val = st.number_input("GTGD bình quân 20 phiên tối thiểu (tỷ VND)", value=5.0, min_value=0.0, step=1.0)
    base_window = st.slider("Số phiên xác định nền", 20, 75, 45, step=5)
    volume_spike = st.slider("Ngưỡng volume bất thường", 1.1, 3.0, 1.5, step=.1)
    max_base = st.slider("Biên độ nền tối đa (%)", 6, 25, 14, step=1)
    st.caption("V1.8: biên nền mặc định 14% để hợp hơn với cổ phiếu Việt Nam; nền quá rộng sẽ bị hạ điểm.")
    vn_base_cap_pct = st.slider("Trần biên nền dùng để tính vùng mua (%)", 8, 24, 16, step=1)
    vn_red_zone_pct = st.slider("Độ rộng tối đa vùng mua đỏ (%)", 2.0, 8.0, 4.5, step=0.5)
    vn_stop_pct = st.slider("Cắt lỗ dưới hỗ trợ nền (%)", 1.0, 5.0, 2.2, step=0.2)
    vn_no_chase_pct = st.slider("Không mua nếu cách hỗ trợ quá (%)", 4.0, 12.0, 6.0, step=0.5)
    max_action_pullback_pct = st.slider("Vùng mua thực tế tối đa cách giá hiện tại (%)", 3.0, 12.0, 7.0, step=0.5)
    st.caption("V1.9: Nếu vùng mua tính ra thấp hơn ngưỡng này, app sẽ coi là không thực tế và chuyển sang CHỜ NỀN MỚI/PULLBACK GẦN.")
    st.header("2B) Chặn cổ phiếu quá nóng/cuối sóng")
    late_hard_return_pct = st.slider("Cấm mua nếu tăng 6–12 tháng vượt (%)", 80, 500, 180, step=10)
    late_hard_runup_pct = st.slider("Cấm mua nếu tăng từ đáy 6–12 tháng vượt (%)", 120, 900, 260, step=20)
    late_warn_return_pct = st.slider("Cảnh báo muộn sóng nếu tăng vượt (%)", 50, 300, 100, step=10)
    late_new_base_max_pct = st.slider("Nền mới sau siêu tăng tối đa rộng (%)", 6, 18, 10, step=1)
    st.caption("V2.0: cổ đã tăng nhiều lần như VIC sẽ bị chặn mua mới. Chỉ theo dõi lại nếu tạo nền mới hẹp đủ lâu gần giá hiện tại.")
    focus_n = st.slider("Số mã cô đặc cuối", 2, 5, 3)
    st.header("3) Thiên thời")
    enable_macro = st.checkbox("Bật Macro Timing Gate", value=True)
    macro_days = st.slider("Số ngày dữ liệu vĩ mô", 60, 260, 150, step=30)
    up_file = None
    if data_mode == "Upload thủ công":
        up_file = st.file_uploader("Upload prices CSV/XLSX", type=["csv","xlsx","xls"])
    st.info("Khuyên dùng: Đãi cát 2 vòng, 80–120 mã vòng 1, phân tích sâu 20–30 mã. Nếu nguồn chậm, giảm luồng còn 4–6.")

# Live dashboard vẫn hiển thị ngay cả khi chưa bấm quét.
if show_live_macro:
    st.subheader("A) Live Macro Pulse – vĩ mô sống")
    live_df, live_err = live_macro_pulse()
    if not live_df.empty:
        st.dataframe(live_df, use_container_width=True, hide_index=True)
        bad = live_df[live_df["state"].isin(["Rủi ro cao", "Gây áp lực", "Áp lực tăng"])]
        if len(bad):
            st.warning("Có biến động vĩ mô gây áp lực: " + ", ".join(bad.market.astype(str).head(6).tolist()))
        else:
            st.success("Chưa thấy tín hiệu vĩ mô intraday quá xấu trong bảng Live Pulse.")
    else:
        st.info("Chưa tải được Live Macro Pulse. App vẫn có thể chạy scan daily.")
    if live_err:
        with st.expander("Lỗi một số mã vĩ mô live"):
            st.write(live_err)

if show_news_pulse:
    st.subheader("B) Tin tức vĩ mô nóng – cuối tuần vẫn cập nhật")
    news_df = collect_news_pulse(3)
    if not news_df.empty:
        st.dataframe(news_df[["group", "shock_score", "published", "title"]].head(18), use_container_width=True, hide_index=True)
        shock_total = int(news_df["shock_score"].clip(lower=0).sum())
        if shock_total >= 6:
            st.error(f"News Shock cao ({shock_total}). Ưu tiên giảm tỷ trọng/chờ thị trường xác nhận.")
        elif shock_total >= 3:
            st.warning(f"News Shock trung bình ({shock_total}). Chỉ mua đỏ nhỏ và chọn CORE.")
        else:
            st.success("News Shock thấp. Không thấy cụm tin xấu nổi bật trong RSS hiện tại.")

if not run:
    st.info("Bấm nút quét để bắt đầu. Bản V2.0 có Late Cycle Guard: cổ đã tăng quá xa/nhân nhiều lần sẽ bị chặn mua mới, không nhầm dòng tiền cuối sóng với cơ hội mua.")
    st.stop()

tickers = parse_tickers(ticker_text)
cfg = {"min_val":min_val, "base_window":base_window, "volume_spike":volume_spike, "max_base_range_pct":max_base, "vn_base_cap_pct":vn_base_cap_pct, "vn_red_zone_pct":vn_red_zone_pct, "vn_stop_pct":vn_stop_pct, "vn_no_chase_pct":vn_no_chase_pct, "max_action_pullback_pct":max_action_pullback_pct, "late_hard_return_pct":late_hard_return_pct, "late_hard_runup_pct":late_hard_runup_pct, "late_warn_return_pct":late_warn_return_pct, "late_warn_runup_pct":150.0, "late_hard_ma200_gap_pct":85.0, "late_warn_ma50_gap_pct":28.0, "late_new_base_max_pct":late_new_base_max_pct}
errors = []

if data_mode == "Demo":
    prices = demo_data(tickers[:scan_limit], deep_days if scan_mode != "Đãi cát 2 vòng - khuyên dùng" else quick_days)
    market = market_proxy(prices)
    res, details, errs = analyze_prices(prices, market, cfg); errors += errs
elif data_mode == "Upload thủ công":
    try:
        prices = standardize_prices(load_file(up_file))
    except Exception as e:
        st.error(f"Lỗi upload: {e}"); st.stop()
    market = market_proxy(prices)
    res, details, errs = analyze_prices(prices, market, cfg); errors += errs
else:
    if scan_mode == "Đãi cát 2 vòng - khuyên dùng":
        st.subheader("Vòng 1: Quét rộng nhanh")
        quick_prices, e1 = fetch_universe_parallel(tickers, quick_days, end_date, scan_limit, workers)
        errors += e1
        if quick_prices.empty:
            st.error("Không tải được dữ liệu vòng 1. Hãy giảm số mã, giảm luồng, hoặc thử Demo/Upload.")
            if errors:
                with st.expander("Lỗi tải dữ liệu"): st.write(errors[:120])
            st.stop()
        quick_market = market_proxy(quick_prices)
        quick_res, _, e_an = analyze_prices(quick_prices, quick_market, cfg); errors += e_an
        if quick_res.empty:
            st.error("Không có ứng viên sau vòng 1."); st.stop()
        quick_res["quick_rank_score"] = quick_res["victory_score"]*.45 + quick_res["money_flow_score"]*2.0 + quick_res["concentration_score"]*.25
        shortlist = quick_res.sort_values("quick_rank_score", ascending=False).head(deep_top).ticker.tolist()
        st.success(f"Vòng 1 tải được {quick_prices.ticker.nunique()} mã. Chọn {len(shortlist)} mã tốt nhất để phân tích sâu.")
        st.dataframe(quick_res.sort_values("quick_rank_score", ascending=False).head(20)[["ticker","sector","quick_rank_score","money_flow_score","victory_score","phase","base_range_pct","red_buy_zone"]], use_container_width=True, hide_index=True)

        st.subheader("Vòng 2: Phân tích sâu top ứng viên")
        prices, e2 = fetch_universe_parallel(shortlist, deep_days, end_date, len(shortlist), workers)
        errors += e2
        if prices.empty:
            st.error("Vòng 2 không tải được dữ liệu. Dùng kết quả vòng 1 tạm thời.")
            prices, market, res, details = quick_prices, quick_market, quick_res, {}
            details = {t: enrich(g.sort_values("date")) for t, g in prices.groupby("ticker")}
        else:
            market = market_proxy(prices)
            res, details, e3 = analyze_prices(prices, market, cfg); errors += e3
    else:
        prices, e1 = fetch_universe_parallel(tickers, deep_days, end_date, scan_limit, workers)
        errors += e1
        if prices.empty:
            st.error("Không tải được dữ liệu cổ phiếu. Hãy giảm số mã, giảm luồng, thử Demo, hoặc upload file.")
            if errors:
                with st.expander("Lỗi tải"): st.write(errors[:120])
            st.stop()
        market = market_proxy(prices)
        res, details, errs = analyze_prices(prices, market, cfg); errors += errs

if res.empty:
    st.error("Không đủ dữ liệu để phân tích."); st.stop()

macro = macro_gate(end_date, macro_days, market) if enable_macro else {"macro_score":65,"macro_gate":"TẮT MACRO GATE","risk_mode":"Normal","notes":[],"errors":[]}
# Nếu bật tin tức, đưa News Shock vào cổng thiên thời để app không báo mua khi cuối tuần có tin xấu lớn.
try:
    if show_news_pulse:
        nd = collect_news_pulse(3)
        shock_total = int(nd["shock_score"].clip(lower=0).sum()) if not nd.empty else 0
        if shock_total >= 6:
            macro["macro_score"] = round(max(0, macro["macro_score"] - 12), 1)
            macro["macro_gate"] = "HẠ TÍN HIỆU DO NEWS SHOCK - CHỜ XÁC NHẬN"
            macro["risk_mode"] = "Small" if macro["risk_mode"] != "Off" else "Off"
            macro["notes"] = (macro.get("notes") or []) + [f"News Shock cao: {shock_total}"]
        elif shock_total >= 3:
            macro["macro_score"] = round(max(0, macro["macro_score"] - 5), 1)
            macro["notes"] = (macro.get("notes") or []) + [f"News Shock trung bình: {shock_total}"]
except Exception as e:
    macro["errors"] = (macro.get("errors") or []) + [f"News pulse: {e}"]

st.success(f"Đã phân tích {res.ticker.nunique()} mã sau vòng lọc. Dữ liệu đang dùng: {len(prices):,} dòng giá.")

st.caption(f"Cập nhật lần cuối theo giờ VN: {vn_now().strftime('%H:%M:%S %d/%m/%Y')}")
st.subheader("1) Độ bao phủ & chất lượng dữ liệu")
a,b,c,d = st.columns(4)
a.metric("Mã đầu vào", len(tickers))
b.metric("Mã tải/được phân tích", int(res.ticker.nunique()))
c.metric("Mã lỗi/bỏ qua", len(errors))
d.metric("Chế độ", scan_mode)
if errors:
    with st.expander("Mã lỗi / bị bỏ qua để biết độ phủ thực tế"):
        st.write(errors[:200])

st.subheader("2) Thiên thời vĩ mô / Market Timing Gate")
a,b,c = st.columns(3)
a.metric("Macro Score", f"{macro['macro_score']}/100")
b.metric("Cổng mua", macro["macro_gate"])
c.metric("Chế độ rủi ro", macro["risk_mode"])
if macro.get("notes"):
    st.write(" | ".join(macro["notes"]))
if macro.get("errors"):
    with st.expander("Một số dữ liệu vĩ mô không tải được"):
        st.write(macro["errors"])
if show_live_macro:
    with st.expander("Live Macro Pulse chi tiết"):
        live_df2, live_err2 = live_macro_pulse()
        if not live_df2.empty:
            st.dataframe(live_df2, use_container_width=True, hide_index=True)
        if live_err2:
            st.write(live_err2)
if show_news_pulse:
    with st.expander("Tin tức vĩ mô nóng chi tiết"):
        ndf2 = collect_news_pulse(4)
        if not ndf2.empty:
            st.dataframe(ndf2[["group", "shock_score", "published", "title", "link"]].head(25), use_container_width=True, hide_index=True)

st.subheader("3) Bản đồ dòng tiền theo ngành")
sec = sector_map_df(res)
st.dataframe(sec, use_container_width=True, hide_index=True, column_config={
    "diem_dong_tien_tb": st.column_config.ProgressColumn("Điểm dòng tiền TB", min_value=0, max_value=25, format="%.1f"),
    "diem_co_dac_tb": st.column_config.ProgressColumn("Điểm cô đặc TB", min_value=0, max_value=100, format="%.1f"),
})

st.subheader("4) Focus 2–3 mã cuối cùng")
focus = focus_df(res, macro, focus_n)
st.dataframe(focus, use_container_width=True, hide_index=True, column_config={
    "concentration_score": st.column_config.ProgressColumn("Điểm cô đặc", min_value=0, max_value=100, format="%.1f"),
    "victory_score": st.column_config.ProgressColumn("Điểm thắng TT", min_value=0, max_value=100, format="%.1f"),
    "money_flow_score": st.column_config.ProgressColumn("Điểm dòng tiền", min_value=0, max_value=25, format="%.1f"),
})

st.subheader("5) Bảng hành động thực chiến")
cols = ["ticker","sector","victory_score","victory_label","concentration_label","concentration_score","money_flow_score","money_flow_state","late_cycle_state","cycle_return_pct","runup_from_low_pct","ema50_gap_pct","ema200_gap_pct","new_base_mature","phase","signal","action_decision","close","zone_model","zone_valid","distance_to_buy_zone_pct","base_zone","old_base_zone","base_range_pct","atr14_pct","red_buy_zone","buy_zone_A","buy_zone_B","buy_zone_C","stop_loss","target_near","risk_pct_from_buy_zone","reward_pct_from_buy_zone","rr_to_base_high","rs20_vs_market_pct","base_method","why_focus"]
st.dataframe(res.sort_values(["victory_score","concentration_score"], ascending=False)[cols], use_container_width=True, hide_index=True, column_config={
    "victory_score": st.column_config.ProgressColumn("Điểm thắng TT", min_value=0, max_value=100, format="%.1f"),
    "concentration_score": st.column_config.ProgressColumn("Điểm cô đặc", min_value=0, max_value=100, format="%.1f"),
    "money_flow_score": st.column_config.ProgressColumn("Điểm dòng tiền", min_value=0, max_value=25, format="%.1f"),
})

st.subheader("6) Kế hoạch từng mã")
sel = st.selectbox("Chọn mã", res.sort_values("victory_score", ascending=False).ticker.tolist())
r = res[res.ticker == sel].iloc[0]
g = details.get(sel)
if g is not None and len(g):
    st.plotly_chart(chart(g, r), use_container_width=True)
c1,c2,c3,c4 = st.columns(4)
c1.metric("Giá hiện tại", fmt(r.close))
c2.metric("Vùng mua đỏ", r.red_buy_zone)
c3.metric("Cắt lỗ", r.stop_loss)
c4.metric("R/R từ vùng mua", r.rr_to_base_high)
st.markdown(f"""
### {sel} — {r.victory_label}
- **Quyết định:** {r.action_decision}
- **Pha:** {r.phase}
- **Dòng tiền:** {r.money_flow_state} ({r.money_flow_score}/25)
- **Bộ lọc cuối sóng:** {r.late_cycle_state} | Tăng chu kỳ: {r.cycle_return_pct}% | Tăng từ đáy: {r.runup_from_low_pct}% | Cách EMA50: {r.ema50_gap_pct}%
- **Điều kiện mua:** {r.buy_trigger}
- **Không mua khi:** {r.no_buy_when}
- **Điều kiện vô hiệu:** {r.invalidation}
- **Kế hoạch vị thế:** {r.position_plan}
- **Lý do:** {r.why_focus}
""")

st.subheader("7) Tải kết quả")
csv = res.sort_values(["victory_score","concentration_score"], ascending=False).to_csv(index=False).encode("utf-8-sig")
st.download_button("Tải CSV", data=csv, file_name="market_winner_v20_late_cycle_guard_results.csv", mime="text/csv")
