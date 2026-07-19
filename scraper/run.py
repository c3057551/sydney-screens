"""Run every cinema scraper and write docs/data/films.json.

One cinema failing never blocks the others — failures are recorded in the
output so the site can show "Orpheum: last updated 3 days ago" style status.
"""

from __future__ import annotations

import json
import sys
import traceback
from pathlib import Path

sys.path.insert(0, str(Path(__file__).parent))

import flicks
import movingstory
import veezi
from common import norm_title, now_sydney
from config import CINEMAS

SCRAPERS = {"movingstory": movingstory.scrape, "flicks": flicks.scrape,
            "veezi": veezi.scrape}
OUT = Path(__file__).parent.parent / "docs" / "data" / "films.json"


def main() -> int:
    all_films, sources = [], []
    previous = {}
    if OUT.exists():
        try:
            previous = json.loads(OUT.read_text())
        except Exception:
            previous = {}

    prev_by_cinema: dict[str, list] = {}
    for f in previous.get("films", []):
        prev_by_cinema.setdefault(f["cinema_id"], []).append(f)
    prev_sources = {s["id"]: s for s in previous.get("sources", [])}

    for cinema in CINEMAS:
        entry = {"id": cinema["id"], "name": cinema["name"], "short": cinema["short"]}
        try:
            films = SCRAPERS[cinema["source"]](cinema)
            entry.update(ok=True, fetched_at=now_sydney().isoformat(timespec="minutes"),
                         films=len(films))
            all_films.extend(f.to_dict() for f in films)
            print(f"  OK   {cinema['name']}: {len(films)} films")
        except Exception as e:
            # keep yesterday's data for this cinema rather than dropping it
            stale = prev_by_cinema.get(cinema["id"], [])
            all_films.extend(stale)
            prev_fetch = prev_sources.get(cinema["id"], {}).get("fetched_at", "")
            entry.update(ok=False, error=str(e)[:200], fetched_at=prev_fetch,
                         films=len(stale))
            print(f"  FAIL {cinema['name']}: {e}")
            traceback.print_exc(limit=1)
        sources.append(entry)

    for f in all_films:
        f["group"] = norm_title(f["title"])

    OUT.parent.mkdir(parents=True, exist_ok=True)
    OUT.write_text(json.dumps({
        "generated_at": now_sydney().isoformat(timespec="minutes"),
        "sources": sources,
        "films": all_films,
    }, indent=1))

    ok = sum(1 for s in sources if s["ok"])
    print(f"\nWrote {OUT} — {len(all_films)} film entries, {ok}/{len(sources)} sources OK")
    # exit 0 even with partial failures so the workflow still commits fresh data
    return 0 if ok else 1


if __name__ == "__main__":
    raise SystemExit(main())
