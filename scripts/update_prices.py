#!/usr/bin/env python3
"""Weekly market prices for the Mentor tab, from Kalimati market's daily wholesale table.

Usage:
    python3 scripts/update_prices.py            # fetch https://kalimatimarket.gov.np/price
    python3 scripts/update_prices.py --html F   # read a saved copy of that page instead (for testing)
    python3 scripts/update_prices.py --html F --today 2026-12-08   # pretend it is another day (testing)

It writes site/data.json -> mentor.market:
    items        this week's price for each tracked item, with its change over about 4 weeks
    history      up to 26 weekly prices per item
    opportunity  the business whose price rose most over 4 weeks (10% or more), or null

It only reads public prices and does arithmetic: no text is generated. It never changes the
study-based profit figures. If none of the tracked items are found, it writes nothing.

Exit codes: 0 = written, 1 = refused (problem printed).
"""
import argparse
import json
import re
import sys
import urllib.request
from datetime import date, datetime, timedelta, timezone
from html import unescape
from pathlib import Path

SITE_DATA = Path(__file__).resolve().parent.parent / "site" / "data.json"
URL = "https://kalimatimarket.gov.np/price"
SOURCE_NAME = "Kalimati Fruits and Vegetables Market, daily wholesale prices"
NEPAL_TZ = timezone(timedelta(hours=5, minutes=45))

# Kalimati row name -> which Mentor business it informs. Names are exactly as Kalimati prints them.
ITEMS = [
    {"key": "tomato-tunnel", "idea": "tomato", "name": "गोलभेडा सानो(टनेल)", "label": "Small tomato, tunnel-grown", "unit": "kg"},
    {"key": "banana-nepali", "idea": "banana", "name": "केरा(नेपाली)", "label": "Banana, Nepali", "unit": "dozen"},
    {"key": "fish-rohu", "idea": "fish", "name": "ताजा माछा(रहु)", "label": "Fresh rohu carp", "unit": "kg"},
    {"key": "fish-chhari", "idea": "fish", "name": "ताजा माछा(छडी)", "label": "Fresh chhari fish", "unit": "kg"},
]
IDEA_NAMES = {"tomato": "tomato tunnels", "banana": "banana farming", "fish": "fish ponds"}

DIGITS = str.maketrans("०१२३४५६७८९", "0123456789")
BS_MONTHS = ["बैशाख", "वैशाख", "जेठ", "असार", "साउन", "श्रावण", "भदौ", "असोज", "आश्विन", "कात्तिक", "कार्तिक",
             "मंसिर", "मङ्सिर", "पुस", "पौष", "माघ", "फागुन", "चैत", "चैत्र"]
BS_EN = {"बैशाख": "Baisakh", "वैशाख": "Baisakh", "जेठ": "Jestha", "असार": "Asar", "साउन": "Saun", "श्रावण": "Saun",
         "भदौ": "Bhadau", "असोज": "Asoj", "आश्विन": "Asoj", "कात्तिक": "Kartik", "कार्तिक": "Kartik", "मंसिर": "Mangsir",
         "मङ्सिर": "Mangsir", "पुस": "Poush", "पौष": "Poush", "माघ": "Magh", "फागुन": "Falgun", "चैत": "Chaitra", "चैत्र": "Chaitra"}


def fail(msg):
    print("REFUSED: " + msg)
    sys.exit(1)


def money(text):
    """'रू १,२५०.००' -> 1250.0"""
    t = text.translate(DIGITS).replace(",", "")
    m = re.search(r"\d+(?:\.\d+)?", t)
    return float(m.group(0)) if m else None


def parse(page):
    page = re.sub(r"<script.*?</script>|<style.*?</style>", " ", page, flags=re.S)
    rows = {}
    for tr in re.findall(r"<tr[^>]*>(.*?)</tr>", page, flags=re.S):
        cells = [" ".join(unescape(re.sub(r"<[^>]+>", " ", c)).split()) for c in re.findall(r"<td[^>]*>(.*?)</td>", tr, flags=re.S)]
        if len(cells) >= 5 and cells[0] not in rows:
            lo, hi, avg = money(cells[2]), money(cells[3]), money(cells[4])
            if avg and lo and hi and 0 < lo <= avg <= hi < 100000:
                rows[cells[0]] = {"min": lo, "max": hi, "avg": avg}
    bs = None
    m = re.search(r"वि\.?\s*सं\.?\s*(" + "|".join(BS_MONTHS) + r")\s*([०-९0-9]+)\s*,\s*([०-९0-9]{4})", page)
    if m:
        bs = "%s %s, %s" % (BS_EN[m.group(1)], m.group(2).translate(DIGITS), m.group(3).translate(DIGITS))
    return rows, bs


def change_over_4_weeks(history, today):
    """% change against the entry closest to 28 days earlier, if one is 21 to 35 days old."""
    best = None
    for h in history:
        age = (today - date.fromisoformat(h["d"])).days
        if 21 <= age <= 35 and (best is None or abs(age - 28) < abs(best[0] - 28)):
            best = (age, h)
    if not best or not history:
        return None
    old, new = best[1]["avg"], history[-1]["avg"]
    return round((new - old) / old * 100, 1) if old else None


def main():
    ap = argparse.ArgumentParser()
    ap.add_argument("--html")
    ap.add_argument("--today")
    a = ap.parse_args()
    if a.html:
        page = Path(a.html).read_text(encoding="utf-8", errors="replace")
    else:
        req = urllib.request.Request(URL, headers={"User-Agent": "Nepal-in-1 weekly price check (+https://saduanki9.github.io/Nepal-in-1/)"})
        try:
            page = urllib.request.urlopen(req, timeout=60).read().decode("utf-8", errors="replace")
        except Exception as e:  # network, DNS, HTTP error
            fail("could not fetch %s: %s" % (URL, e))
    today = date.fromisoformat(a.today) if a.today else datetime.now(NEPAL_TZ).date()

    rows, bs = parse(page)
    found = [dict(it, **rows[it["name"]]) for it in ITEMS if it["name"] in rows]
    if not found:
        fail("none of the tracked items were in Kalimati's table (%d rows read)" % len(rows))

    data = json.loads(SITE_DATA.read_text(encoding="utf-8"))
    mentor = data.get("mentor")
    if not isinstance(mentor, dict):
        fail("site data has no mentor section")
    market = mentor.get("market") if isinstance(mentor.get("market"), dict) else {}
    history = market.get("history") if isinstance(market.get("history"), dict) else {}

    items = []
    for it in found:
        h = [x for x in history.get(it["key"], []) if x.get("d") != today.isoformat()]
        h.append({"d": today.isoformat(), "bs": bs, "avg": it["avg"], "min": it["min"], "max": it["max"]})
        h = sorted(h, key=lambda x: x["d"])[-26:]
        history[it["key"]] = h
        items.append({"key": it["key"], "idea": it["idea"], "label": it["label"], "unit": it["unit"],
                      "avg": it["avg"], "min": it["min"], "max": it["max"], "change_4w": change_over_4_weeks(h, today)})

    rising = [x for x in items if x["change_4w"] is not None and x["change_4w"] >= 10]
    opportunity = None
    if rising:
        top = max(rising, key=lambda x: x["change_4w"])
        opportunity = {"idea": top["idea"], "key": top["key"], "change_4w": top["change_4w"], "avg": top["avg"], "unit": top["unit"],
                       "headline": "%s prices are up %d%% over 4 weeks at Kalimati" % (top["label"], round(top["change_4w"])),
                       "why": "Good news for %s: farmers selling now get more. Prices can fall again, so plan on the study figures." % IDEA_NAMES[top["idea"]]}

    mentor["market"] = {"as_of": today.isoformat(), "bs_date": bs, "source_name": SOURCE_NAME, "source_url": URL,
                        "note": "Wholesale prices in Kathmandu. Farm-gate prices, which the profit studies use, are lower.",
                        "items": items, "opportunity": opportunity, "history": history}
    SITE_DATA.write_text(json.dumps(data, ensure_ascii=False, separators=(",", ":")), encoding="utf-8")
    print("WROTE mentor.market for %s (%s): %s%s" % (today, bs or "no BS date",
          "; ".join("%s Rs %g/%s%s" % (x["label"], x["avg"], x["unit"], "" if x["change_4w"] is None else " (%+.1f%% in 4 weeks)" % x["change_4w"]) for x in items),
          "; opportunity: " + opportunity["headline"] if opportunity else ""))


if __name__ == "__main__":
    main()
