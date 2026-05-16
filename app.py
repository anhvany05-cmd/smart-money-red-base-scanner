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

st.set_page_config(page_title="Market Winner Scanner V1.7 Live Pulse", layout="wide", initial_sidebar_state="expanded")

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


def analyze_one(t, g, market, cfg):
    d = enrich(g); last = d.iloc[-1]
    bw = int(min(cfg["base_window"], max(30, len(d)-5)))
    base = d.tail(bw)
    close = float(last.close); base_low = float(base.low.min()); base_high = float(base.high.max())
    base_mid = (base_low + base_high) / 2
    atr = float(last.atr14) if np.isfinite(last.atr14) and last.atr14 > 0 else max(close * 0.025, (base_high-base_low)/10)
    base_range_pct = (base_high/base_low - 1) * 100 if base_low > 0 else 999
    zA1 = base_low; zA2 = base_low + .18*(base_high-base_low)
    zB1 = zA2; zB2 = base_low + .33*(base_high-base_low)
    zC1 = zB2; zC2 = base_low + .45*(base_high-base_low)
    stop = min(base_low - .5*atr, base_low * .985)
    risk = (close/stop - 1)*100 if stop > 0 else np.nan
    reward = (base_high/close - 1)*100 if close > 0 else np.nan
    rr = reward/risk if risk and risk > 0 else np.nan

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
    low_part = close <= base_low + .4*(base_high-base_low)
    too_far = close > base_low + .65*(base_high-base_low)
    tight = base_range_pct <= cfg["max_base_range_pct"] and in_base
    shake = last.low < base_low*1.01 and close_pos > .55 and vol_ratio >= cfg["volume_spike"]
    absorb = vol_ratio >= cfg["volume_spike"] and last.close >= last.open*.985 and in_base
    dist = close > base_mid and vol_ratio >= 1.8 and close_pos < .35 and base.close.iloc[-1]/base.close.iloc[0]-1 > .12
    liq = 10 if val20 >= cfg["min_val"]*1e9 else 5 if val20 >= cfg["min_val"]*.5e9 else 0
    base_score = 15 if tight else 8 if base_range_pct <= cfg["max_base_range_pct"] + 10 else 0
    acc = (8 if absorb else 0) + (7 if shake else 0) + (5 if low_part else 0) + (5 if rs20 > 0 else 0)
    no_chase = 10 if not too_far else 4
    risk_score = 10 if risk <= 8 and rr >= 1.4 else 6 if risk <= 10 else 2
    total = clamp(liq + base_score + acc + no_chase + risk_score + mf*1.2, 0, 100)
    if dist: phase, sig = "Cảnh báo phân phối", "Distribution Warning"
    elif shake: phase, sig = "Rũ cung trong nền", "Shakeout Buy Zone"
    elif absorb: phase, sig = "Gom hàng trong nền", "Red Base Accumulation"
    elif tight: phase, sig = "Tạo nền/siết nền", "Early Watch"
    else: phase, sig = "Chưa rõ", "Watch only"
    action = "TRÁNH MUA" if dist else "CHƯA ƯU TIÊN - DÒNG TIỀN YẾU" if mf < 8 else "CÓ THỂ CANH MUA ĐỎ" if close <= zB2 and close >= stop else "CHỈ THĂM DÒ NHỎ" if close <= zC2 else "KHÔNG ĐU XANH - CHỜ VỀ VÙNG" if too_far else "THEO DÕI - CHỜ RUNG LẮC"
    conc = clamp(total*.42 + mf*1.9 + (8 if phase in ["Gom hàng trong nền","Rũ cung trong nền"] else 0) + (6 if close <= zB2 else 0) - (10 if dist else 0), 0, 100)
    clabel = "CORE" if conc >= 78 and mf >= 15 and not dist else "WATCH" if conc >= 62 and mf >= 10 and not dist else "EARLY"
    victory = clamp(.29*conc + .25*mf*4 + .20*alpha + .16*no_chase*10 + .10*risk_score*10, 0, 100)
    vlabel = "ỨNG VIÊN VƯỢT THỊ TRƯỜNG MẠNH" if victory >= 80 else "ỨNG VIÊN TỐT" if victory >= 68 else "THEO DÕI" if victory >= 55 else "CHƯA ĐỦ CHUẨN"
    why = [mf_state, phase]
    if close <= zB2: why.append("Giá ở vùng mua đỏ")
    if rs20 > 0: why.append("Mạnh hơn thị trường")
    if too_far: why.append("Giá xa vùng mua")
    if dist: why.append("Cảnh báo phân phối")
    return {
        "ticker":t, "sector":g.sector.iloc[-1] if "sector" in g else SECTOR_MAP.get(t,"Khác"), "close":close,
        "phase":phase, "signal":sig, "action_decision":action, "Điểm tổng":round(total,1),
        "victory_score":round(victory,1), "victory_label":vlabel, "concentration_score":round(conc,1), "concentration_label":clabel,
        "money_flow_score":round(mf,1), "money_flow_state":mf_state, "value_ratio_5_20":round(vr5,2), "value_ratio_20_60":round(vr20,2),
        "up_value_ratio_pct":round(upv*100,1), "cmf20":round(cmf,3), "rs20_vs_market_pct":round(rs20*100,2),
        "base_zone":frange(base_low,base_high), "red_buy_zone":frange(zA1,zB2), "buy_zone_A":frange(zA1,zA2), "buy_zone_B":frange(zB1,zB2), "buy_zone_C":frange(zC1,zC2),
        "stop_loss":fmt(stop), "target_near":fmt(base_high), "risk_pct_from_close":round(risk,2) if np.isfinite(risk) else np.nan,
        "reward_pct_to_base_high":round(reward,2) if np.isfinite(reward) else np.nan, "rr_to_base_high":round(rr,2) if np.isfinite(rr) else np.nan,
        "no_buy_when":f"Không mua xanh/sát kháng cự {fmt(base_high)}; chờ về {frange(zA1,zB2)}",
        "buy_trigger":f"Chỉ mua khi đỏ/rung lắc trong {frange(zA1,zB2)}, không đóng cửa dưới {fmt(stop)}",
        "invalidation":f"Đóng cửa dưới {fmt(stop)} hoặc thủng nền với volume lớn",
        "position_plan":"30% vùng A, thêm 20–30% nếu giữ nền/rũ cung; không trung bình giá xuống",
        "why_focus":" | ".join(why), "distribution_warning":dist,
        "_base_low":base_low, "_base_high":base_high, "_red_high":zB2, "_stop":stop,
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
st.title("Smart Money Red Base Scanner – Live Pulse MVP V1.7")
st.caption("App sống theo thị trường: tự làm mới dữ liệu, theo dõi vĩ mô toàn cầu, tin tức cuối tuần và chỉ mở tín hiệu mua khi thiên thời không xấu.")
with st.expander("Triết lý hệ thống"):
    st.write("Không mua xanh/đu break. Ưu tiên cổ phiếu có dòng tiền, ngành có tiền, vĩ mô không xấu, giá ở vùng đỏ trong nền. Bản V1.7 thêm Live Pulse: tự refresh, theo dõi macro intraday và tin tức vĩ mô nóng kể cả cuối tuần.")

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
    base_window = st.slider("Số phiên xác định nền", 30, 90, 60, step=5)
    volume_spike = st.slider("Ngưỡng volume bất thường", 1.1, 3.0, 1.5, step=.1)
    max_base = st.slider("Biên độ nền tối đa (%)", 10, 45, 28, step=1)
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
    st.info("Bấm nút quét để bắt đầu. Bản V1.7 vẫn cập nhật Live Macro/Tin tức ở trên khi app đang mở.")
    st.stop()

tickers = parse_tickers(ticker_text)
cfg = {"min_val":min_val, "base_window":base_window, "volume_spike":volume_spike, "max_base_range_pct":max_base}
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
        st.dataframe(quick_res.sort_values("quick_rank_score", ascending=False).head(20)[["ticker","sector","quick_rank_score","money_flow_score","victory_score","phase","red_buy_zone"]], use_container_width=True, hide_index=True)

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
cols = ["ticker","sector","victory_score","victory_label","concentration_label","concentration_score","money_flow_score","money_flow_state","phase","signal","action_decision","close","base_zone","red_buy_zone","buy_zone_A","buy_zone_B","buy_zone_C","stop_loss","target_near","risk_pct_from_close","reward_pct_to_base_high","rr_to_base_high","rs20_vs_market_pct","why_focus"]
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
c4.metric("R/R tới đỉnh nền", r.rr_to_base_high)
st.markdown(f"""
### {sel} — {r.victory_label}
- **Quyết định:** {r.action_decision}
- **Pha:** {r.phase}
- **Dòng tiền:** {r.money_flow_state} ({r.money_flow_score}/25)
- **Điều kiện mua:** {r.buy_trigger}
- **Không mua khi:** {r.no_buy_when}
- **Điều kiện vô hiệu:** {r.invalidation}
- **Kế hoạch vị thế:** {r.position_plan}
- **Lý do:** {r.why_focus}
""")

st.subheader("7) Tải kết quả")
csv = res.sort_values(["victory_score","concentration_score"], ascending=False).to_csv(index=False).encode("utf-8-sig")
st.download_button("Tải CSV", data=csv, file_name="market_winner_v17_live_pulse_results.csv", mime="text/csv")
