#!/usr/bin/env python3
"""Build site/screener.json, the data behind the NEPSE screener.

Usage:
    python3 scripts/update_screener.py            # prices and fundamentals (every company page)
    python3 scripts/update_screener.py --prices   # prices only; keeps the stored fundamentals

Sources (public pages, read politely, a few at a time):
- https://merolagani.com/latestmarket.aspx: every listed stock's last price and change today
- https://merolagani.com/CompanyDetail.aspx?symbol=X: sector, EPS, book value, dividend,
  52-week range, market capitalisation and one-year return for each company

The screener only filters and sorts published figures. It never ranks a stock as a buy.

Exit codes: 0 = written, 3 = nothing new, 1 = refused (problem printed). On any refusal
site/screener.json is left as it was, so the live site keeps its last good data.
"""
import html
import json
import re
import sys
import time
import urllib.request
from concurrent.futures import ThreadPoolExecutor
from datetime import datetime, timezone
from pathlib import Path

ROOT = Path(__file__).resolve().parent.parent
OUT = ROOT / "site" / "screener.json"
FUND = ROOT / "data" / "screener_fund.json"  # raw company-page figures, kept for --prices runs; not published
SKIP_SECTORS = {"Corporate Debenture"}  # bonds, not shares
MARKET = "https://merolagani.com/latestmarket.aspx"
HISTORY = "https://merolagani.com/handlers/TechnicalChartHandler.ashx?type=get_advanced_chart&resolution=1D&isAdjust=1&currencyCode=NPR&symbol="
COMPANY = "https://merolagani.com/CompanyDetail.aspx?symbol="
UA = "Mozilla/5.0 (compatible; NepalIn1-screener/1.0; public market data)"
MIN_STOCKS = 250


def fail(msg):
    print("REFUSED: " + msg)
    sys.exit(1)


def get(url, tries=3):
    last = None
    for i in range(tries):
        try:
            req = urllib.request.Request(url, headers={"User-Agent": UA, "Accept": "text/html"})
            with urllib.request.urlopen(req, timeout=40) as r:
                return r.read().decode("utf-8", "ignore")
        except Exception as e:  # network hiccup: wait and retry
            last = e
            time.sleep(2 * (i + 1))
    raise RuntimeError("could not fetch %s: %s" % (url, last))


def text(cell):
    return re.sub(r"\s+", " ", html.unescape(re.sub(r"<[^>]+>", " ", cell))).strip()


def num(s):
    """First number in a string ('33.89 (FY:083-084, Q:1)' -> 33.89); None if there is none."""
    m = re.search(r"-?[\d,]*\.?\d+", s or "")
    if not m:
        return None
    try:
        return float(m.group(0).replace(",", ""))
    except ValueError:
        return None


def market():
    page = get(MARKET)
    m = re.search(r"As of\s*(\d{4})/(\d{2})/(\d{2})", page)
    if not m:
        fail("the market page shows no 'As of' date")
    as_of = "%s-%s-%s" % m.groups()
    for table in re.findall(r"<table[^>]*>(.*?)</table>", page, re.S):
        rows = re.findall(r"<tr[^>]*>(.*?)</tr>", table, re.S)
        if not rows:
            continue
        head = [text(c) for c in re.findall(r"<t[hd][^>]*>(.*?)</t[hd]>", rows[0], re.S)]
        if head[:3] != ["Symbol", "LTP", "% Change"]:
            continue
        out = {}
        for r in rows[1:]:
            c = [text(x) for x in re.findall(r"<t[hd][^>]*>(.*?)</t[hd]>", r, re.S)]
            if len(c) < 7 or not re.fullmatch(r"[A-Z0-9]+", c[0] or ""):
                continue
            ltp, chg, qty = num(c[1]), num(c[2]), num(c[6])
            if ltp and ltp > 0:
                out[c[0]] = {"ltp": ltp, "chg": chg if chg is not None else 0.0, "qty": int(qty or 0)}
        return as_of, out
    fail("the market page has no price table")


FIELDS = {
    "Sector": "sector", "Company Name": "name", "EPS": "eps", "Book Value": "bvps",
    "% Dividend": "cash", "% Bonus": "bonus", "52 Weeks High - Low": "range",
    "Market Capitalization": "mcap", "1 Year Yield": "yr", "Paidup Value": "face",
    "120 Day Average": "avg120", "30-Day Avg Volume": "vol30", "P/E Ratio": "pe_src",
    "Market Price": "price_src", "Shares Outstanding": "shares",
}


def company(symbol):
    page = re.sub(r"<script.*?</script>|<style.*?</style>", "", get(COMPANY + symbol), flags=re.S)
    raw = {}
    for r in re.findall(r"<tr[^>]*>(.*?)</tr>", page, re.S):
        c = [text(x) for x in re.findall(r"<t[hd][^>]*>(.*?)</t[hd]>", r, re.S)]
        if len(c) == 2 and c[0] in FIELDS and FIELDS[c[0]] not in raw:
            raw[FIELDS[c[0]]] = c[1]
    if not raw.get("sector"):
        return symbol, None
    hi = lo = None
    if raw.get("range"):
        parts = [num(x) for x in raw["range"].split("-") if x.strip()]
        if len(parts) == 2:
            hi, lo = max(parts), min(parts)
    fy = re.search(r"FY:\s*([\d-]+)(?:,\s*Q:\s*(\d))?", raw.get("eps", ""))
    dfy = re.search(r"FY:\s*([\d-]+)", raw.get("cash", "") or raw.get("bonus", ""))
    return symbol, {
        "name": raw.get("name") or symbol,
        "sector": raw["sector"],
        "eps": num(raw.get("eps")),
        "eps_period": ("FY " + fy.group(1) + (" Q" + fy.group(2) if fy.group(2) else "")) if fy else "",
        "bvps": num(raw.get("bvps")),
        "cash": num(raw.get("cash")),
        "bonus": num(raw.get("bonus")),
        "div_fy": ("FY " + dfy.group(1)) if dfy else "",
        "face": num(raw.get("face")) or 100.0,
        "hi52": hi, "lo52": lo,
        "mcap": num(raw.get("mcap")),
        "yr": num(raw.get("yr")),
        "avg120": num(raw.get("avg120")),
        "vol30": num(raw.get("vol30")),
        "pe_src": num(raw.get("pe_src")),
        "price_src": num(raw.get("price_src")),
        "shares": num(raw.get("shares")),
    }


def history(symbol):
    """About 13 months of daily bars, adjusted for bonus and right shares: (closes, volumes), oldest first."""
    now = int(time.time())
    try:
        d = json.loads(get(HISTORY + symbol + "&rangeStartDate=%d&rangeEndDate=%d" % (now - 420 * 86400, now)))
    except Exception:
        return symbol, None
    if d.get("s") != "ok" or not d.get("c"):
        return symbol, None
    bars = [b for b in sorted(zip(d["t"], d["c"], d.get("v") or [0] * len(d["c"]))) if b[1]]
    # Nepal date of each bar (UTC+5:45), so today's close can be matched to the market page's date
    days = [datetime.fromtimestamp(t + 20700, timezone.utc).strftime("%Y-%m-%d") for t, _, _ in bars]
    return symbol, (days, [float(c) for _, c, _ in bars], [float(v or 0) for _, _, v in bars])


def sma(xs, n):
    return sum(xs[-n:]) / n if len(xs) >= n else None


def ema_series(xs, n):
    k, out, e = 2 / (n + 1), [], None
    for x in xs:
        e = x if e is None else x * k + e * (1 - k)
        out.append(e)
    return out


def rsi(xs, n=14):
    """Wilder's RSI."""
    if len(xs) <= n:
        return None
    gains = [max(0, xs[i] - xs[i - 1]) for i in range(1, len(xs))]
    losses = [max(0, xs[i - 1] - xs[i]) for i in range(1, len(xs))]
    ag, al = sum(gains[:n]) / n, sum(losses[:n]) / n
    for g, l in zip(gains[n:], losses[n:]):
        ag, al = (ag * (n - 1) + g) / n, (al * (n - 1) + l) / n
    return 100.0 if al == 0 else 100 - 100 / (1 + ag / al)


def technicals(days, closes, vols, ltp, as_of):
    """Standard trading indicators and a vote-based technical rating from -1 (all bearish) to +1 (all bullish)."""
    if not closes or len(closes) < 35:
        return None
    c, vols = closes[:], vols[:]
    if days[-1] == as_of:   # today's bar is there: use the market page's last price for it
        c[-1] = ltp
    elif days[-1] < as_of:  # history ends earlier: add today's price as the latest bar
        c.append(ltp)
        vols.append(0.0)
    s20, s50, s200 = sma(c, 20), sma(c, 50), sma(c, 200)
    e12, e26 = ema_series(c, 12), ema_series(c, 26)
    macd = [a - b for a, b in zip(e12, e26)]
    sig = ema_series(macd, 9)
    hist = [m - g for m, g in zip(macd, sig)]
    cross = 0  # MACD crossed its signal line in the last 3 sessions
    for i in range(len(hist) - 3, len(hist)):
        if i > 0 and hist[i - 1] <= 0 < hist[i]:
            cross = 1
        elif i > 0 and hist[i - 1] >= 0 > hist[i]:
            cross = -1
    gx = 0  # 50-day average crossed the 200-day average in the last 10 sessions
    if len(c) >= 210:
        for i in range(len(c) - 10, len(c)):
            a_now, b_now = sum(c[i - 49:i + 1]) / 50, sum(c[i - 199:i + 1]) / 200
            a_was, b_was = sum(c[i - 50:i]) / 50, sum(c[i - 200:i]) / 200
            if a_was <= b_was and a_now > b_now:
                gx = 1
            elif a_was >= b_was and a_now < b_now:
                gx = -1
    r = rsi(c)
    r_prev = rsi(c[:-1])
    mom = (c[-1] / c[-11] - 1) * 100 if len(c) > 11 and c[-11] else None
    v20 = sma(vols, 20) if vols and len(vols) >= 20 else None
    vsurge = bool(v20 and vols[-1] >= 2 * v20)
    votes = []
    for avg in (s20, s50, s200):
        if avg:
            votes.append(1 if ltp > avg else -1)
    if s50 and s200:
        votes.append(1 if s50 > s200 else -1)
    votes.append(1 if hist[-1] > 0 else -1)
    if r is not None and r_prev is not None:
        votes.append(1 if r < 30 and r > r_prev else -1 if r > 70 and r < r_prev else 0)
    if mom is not None:
        votes.append(1 if mom > 0 else -1 if mom < 0 else 0)
    score = sum(votes) / len(votes) if votes else 0
    label = ("Strong bullish" if score >= 0.5 else "Bullish" if score >= 0.1 else
             "Strong bearish" if score <= -0.5 else "Bearish" if score <= -0.1 else "Neutral")
    return {
        "rsi": r2(r), "macd": r2(macd[-1]), "macd_sig": r2(sig[-1]), "macd_x": cross,
        "sma20": r2(s20), "sma50": r2(s50), "sma200": r2(s200), "gx": gx,
        "mom10": r2(mom), "vsurge": vsurge, "score": r2(score), "label": label, "bars": len(c),
    }


def r2(x):
    return None if x is None else round(x, 2)


def build(prices, fund, hist=None, as_of=""):
    stocks = []
    for sym, p in sorted(prices.items()):
        f = fund.get(sym)
        if not f or f.get("sector") in SKIP_SECTORS:
            continue
        ltp, eps, bvps = p["ltp"], f.get("eps"), f.get("bvps")
        cash_rs = (f["cash"] or 0) * f.get("face", 100) / 100 if f.get("cash") else 0
        s = {
            "s": sym, "n": f["name"], "sec": f["sector"], "ltp": ltp, "chg": p["chg"], "qty": p["qty"],
            "eps": eps, "eps_p": f.get("eps_period", ""), "bvps": bvps,
            "pe": r2(ltp / eps) if eps and eps > 0 else None,
            "pb": r2(ltp / bvps) if bvps and bvps > 0 else None,
            "roe": r2(eps / bvps * 100) if eps is not None and bvps and bvps > 0 else None,
            "cash": f.get("cash"), "bonus": f.get("bonus"), "div_fy": f.get("div_fy", ""),
            "dy": r2(cash_rs / ltp * 100) if cash_rs else None,
            "hi52": f.get("hi52"), "lo52": f.get("lo52"),
            "mcap": round(f["shares"] * ltp) if f.get("shares") else (round(f["mcap"]) if f.get("mcap") else None),
            "yr": f.get("yr"), "vol30": f.get("vol30"), "a120": f.get("avg120"),
        }
        h = (hist or {}).get(sym)
        t = technicals(h[0], h[1], h[2], ltp, as_of) if h else None
        if t:
            s["t"] = t
        stocks.append(s)
    return stocks


def main():
    prices_only = "--prices" in sys.argv
    old = json.loads(OUT.read_text(encoding="utf-8")) if OUT.exists() else {}
    old_fund = json.loads(FUND.read_text(encoding="utf-8")) if FUND.exists() else {}
    as_of, prices = market()
    if len(prices) < MIN_STOCKS:
        fail("only %d prices on the market page (expected at least %d)" % (len(prices), MIN_STOCKS))

    fund = {}
    if prices_only and old_fund:
        fund = old_fund
        missing = [s for s in prices if s not in fund]
        if missing:  # newly listed companies: read just their pages
            with ThreadPoolExecutor(4) as ex:
                for sym, f in ex.map(company, missing):
                    if f:
                        fund[sym] = f
    else:
        with ThreadPoolExecutor(4) as ex:
            for sym, f in ex.map(company, sorted(prices)):
                if f:
                    fund[sym] = f
        if len(fund) < MIN_STOCKS:
            fail("only %d company pages could be read (expected at least %d)" % (len(fund), MIN_STOCKS))
        # Sanity: our P/E from the page's own price and EPS should match the page's P/E for most companies.
        checked = [f for f in fund.values() if f.get("pe_src") and f.get("price_src") and f.get("eps") and f["eps"] > 0]
        bad = [f for f in checked if abs(f["price_src"] / f["eps"] - f["pe_src"]) > max(0.5, 0.05 * f["pe_src"])]
        if checked and len(bad) > 0.25 * len(checked):
            fail("P/E check failed for %d of %d companies; the page layout may have changed" % (len(bad), len(checked)))

    wanted = [s for s in sorted(prices) if s in fund and fund[s].get("sector") not in SKIP_SECTORS]
    hist = {}
    with ThreadPoolExecutor(4) as ex:
        for sym, h in ex.map(history, wanted):
            if h:
                hist[sym] = h
    if len(hist) < 0.7 * len(wanted):
        fail("price history came back for only %d of %d shares" % (len(hist), len(wanted)))
    stocks = build(prices, fund, hist, as_of)
    if len(stocks) < MIN_STOCKS:
        fail("only %d stocks have both a price and fundamentals" % len(stocks))
    now = datetime.now(timezone.utc).isoformat(timespec="seconds")
    out = {
        "as_of": as_of,
        "fund_as_of": (old.get("fund_as_of") if prices_only and old_fund else now[:10]),
        "updated_at": now,
        "source_name": "Merolagani: latest market and company pages",
        "source_url": MARKET,
        "company_url": COMPANY,
        "note": "EPS is the latest annualised figure each company reported; P/E, P/B, ROE and dividend yield are worked out from today's price. Cash dividend yield uses the last declared cash dividend. A filter for research, not advice.",
        "stocks": stocks,
    }
    if old and old.get("as_of") == as_of and old.get("stocks") == stocks:
        print("NO CHANGE: prices as of %s already stored" % as_of)
        sys.exit(3)
    OUT.write_text(json.dumps(out, ensure_ascii=False, separators=(",", ":")), encoding="utf-8")
    FUND.parent.mkdir(exist_ok=True)
    FUND.write_text(json.dumps(fund, ensure_ascii=False, separators=(",", ":"), sort_keys=True), encoding="utf-8")
    print("WROTE site/screener.json: %d stocks, prices as of %s, fundamentals as of %s" % (len(stocks), as_of, out["fund_as_of"]))


if __name__ == "__main__":
    main()
