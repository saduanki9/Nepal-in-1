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


def r2(x):
    return None if x is None else round(x, 2)


def build(prices, fund):
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
            "yr": f.get("yr"), "vol30": f.get("vol30"),
        }
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

    stocks = build(prices, fund)
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
