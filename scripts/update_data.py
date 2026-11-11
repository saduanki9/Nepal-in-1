#!/usr/bin/env python3
"""Refresh site/data.json from the daily research file.

Usage:
    python3 scripts/update_data.py SOURCE.json

SOURCE.json is the file the daily research task writes:
    {"generated_at", "feed", "business", "nepse", "watch", "invest", "places"}

What it does:
- keeps only public parts: the news (not any "ideas" list), business, NEPSE,
  watchlist, investment rates and places
- removes any "local" flags and internal updated_by fields
- never touches the Mentor, which lives in site/mentor.json
- refuses to go backwards: if the source is not newer than the last update,
  nothing is written

It never writes text that speaks to one person. If a news or business item
says "you" or "your", it stops and lists them, so they can be reworded in
SOURCE.json first.

Exit codes: 0 = data.json written, 3 = nothing new (no change),
1 = refused (problem printed).
"""
import json
import re
import sys
from datetime import datetime
from pathlib import Path

SITE_DATA = Path(__file__).resolve().parent.parent / "site" / "data.json"
SECTIONS = {"feed": "feed", "business": "business", "nepse": "nepse",
            "watch": "watch", "invest": "invest", "places": "places"}
SECOND_PERSON = re.compile(r"\b(you|your|yours|yourself)\b", re.I)


def fail(msg):
    print("REFUSED: " + msg)
    sys.exit(1)


def parse_time(value):
    try:
        return datetime.fromisoformat(str(value).replace("Z", "+00:00"))
    except ValueError:
        return None


def strip(obj):
    """Drop internal bookkeeping fields everywhere."""
    if isinstance(obj, dict):
        obj.pop("updated_by", None)
        for v in obj.values():
            strip(v)
    elif isinstance(obj, list):
        for v in obj:
            strip(v)


def main():
    if len(sys.argv) != 2:
        fail("usage: update_data.py SOURCE.json")
    src = json.loads(Path(sys.argv[1]).read_text(encoding="utf-8"))
    cur = json.loads(SITE_DATA.read_text(encoding="utf-8"))

    if not isinstance(src, dict):
        fail("source is not a JSON object")
    missing = [k for k in SECTIONS if not isinstance(src.get(k), dict)]
    if missing:
        fail("source is missing sections: " + ", ".join(missing))

    new_time = parse_time(src.get("generated_at"))
    if new_time is None:
        fail("source has no valid generated_at")
    old_time = parse_time(cur.get("source_generated_at"))
    if old_time is not None and new_time <= old_time:
        print("NO CHANGE: source generated_at %s is not newer than %s" % (new_time.isoformat(), old_time.isoformat()))
        sys.exit(3)

    out = {"generated_at": datetime.now().astimezone().isoformat(timespec="seconds"),
           "source_generated_at": src["generated_at"]}
    for key, src_key in SECTIONS.items():
        out[key] = json.loads(json.dumps(src[src_key]))

    out["feed"].pop("ideas", None)
    for place in out["places"].get("places", []) or []:
        if isinstance(place, dict):
            place.pop("local", None)
    strip(out)

    news = out["feed"].get("news")
    if not isinstance(news, list) or len(news) < 3:
        fail("feed has fewer than 3 news stories")

    flagged = []
    for section, items in (("feed.news", news), ("business.news", out["business"].get("news") or []),
                           ("business.events", out["business"].get("events") or [])):
        for i, item in enumerate(items):
            text = " ".join(str(item.get(f, "")) for f in ("headline", "why_it_matters", "title"))
            if SECOND_PERSON.search(text):
                flagged.append("%s[%d]: %s" % (section, i, text[:160]))
    if flagged:
        fail("these items speak to one person; reword them in the source and run again:\n  " + "\n  ".join(flagged))


    SITE_DATA.write_text(json.dumps(out, ensure_ascii=False, separators=(",", ":")), encoding="utf-8")
    print("WROTE site/data.json: %d news, %d business stories, NEPSE close of %s"
          % (len(news), len(out["business"].get("news") or []), out["nepse"].get("as_of", "?")))


if __name__ == "__main__":
    main()
