"""Scraper for flicks.com.au cinema pages.

One parser covers every cinema Flicks lists (Palace venues, Chauvel, Dendy,
Golden Age, Event George St). Flicks pages are server-rendered and follow:

  https://www.flicks.com.au/cinema/<slug>/            -> today
  https://www.flicks.com.au/cinema/<slug>/?date=YYYY-MM-DD

The parser is deliberately defensive: it looks for JSON-LD ScreeningEvent
structured data first (Flicks embeds it), then falls back to HTML heuristics.
If Flicks change their markup, fix ONE file and every venue comes back.
"""

from __future__ import annotations

import json
import re
from datetime import timedelta

from bs4 import BeautifulSoup

from common import Film, Session, extract_year, http_get, now_sydney, parse_time_12h

BASE = "https://www.flicks.com.au"
DAYS_AHEAD = 14


def _jsonld_events(soup: BeautifulSoup) -> list[dict]:
    events = []
    for tag in soup.find_all("script", type="application/ld+json"):
        try:
            data = json.loads(tag.string or "")
        except Exception:
            continue
        items = data if isinstance(data, list) else [data]
        for item in items:
            graph = item.get("@graph", [item]) if isinstance(item, dict) else []
            for node in graph:
                if isinstance(node, dict) and node.get("@type") in (
                    "ScreeningEvent", "Event"
                ):
                    events.append(node)
    return events


def _from_jsonld(events: list[dict], cinema_id: str) -> dict[str, Film]:
    films: dict[str, Film] = {}
    for ev in events:
        work = ev.get("workPresented") or ev.get("about") or {}
        name = (work.get("name") if isinstance(work, dict) else None) or ev.get("name")
        start = ev.get("startDate", "")
        if not name or not start:
            continue
        title, year = extract_year(name)
        key = title.lower()
        film = films.setdefault(
            key,
            Film(
                title=title,
                year=year,
                cinema_id=cinema_id,
                url=(work.get("url") if isinstance(work, dict) else "") or ev.get("url", ""),
                poster=(work.get("image") if isinstance(work, dict) else "") or "",
            ),
        )
        m = re.match(r"(\d{4}-\d{2}-\d{2})T(\d{2}:\d{2})", start)
        if m:
            dt = f"{m.group(1)}T{m.group(2)}"
            if not any(s.dt == dt for s in film.sessions):
                film.sessions.append(Session(dt=dt, booking_url=ev.get("url", "")))
    return films


def _from_html(soup: BeautifulSoup, cinema_id: str, day) -> dict[str, Film]:
    """Heuristic fallback: film heading followed by time links."""
    films: dict[str, Film] = {}
    for heading in soup.select("h2 a[href*='/movie/'], h3 a[href*='/movie/']"):
        title_text = heading.get_text(" ", strip=True)
        if not title_text:
            continue
        title, year = extract_year(title_text)
        block = heading.find_parent(["section", "article", "div", "li"])
        if block is None:
            continue
        sessions = []
        for a in block.find_all("a"):
            txt = a.get_text(" ", strip=True)
            if re.fullmatch(r"\d{1,2}[:.]\d{2}\s*(am|pm)", txt, re.I):
                hm = parse_time_12h(txt)
                if hm:
                    href = a.get("href", "")
                    if href and not href.startswith("http"):
                        href = BASE + href
                    sessions.append(
                        Session(dt=f"{day.isoformat()}T{hm[0]:02d}:{hm[1]:02d}",
                                booking_url=href)
                    )
        if sessions:
            key = title.lower()
            film = films.setdefault(
                key,
                Film(title=title, year=year, cinema_id=cinema_id,
                     url=BASE + heading.get("href", "") if not heading.get("href", "").startswith("http") else heading["href"]),
            )
            have = {s.dt for s in film.sessions}
            film.sessions.extend(s for s in sessions if s.dt not in have)
    return films


def scrape(cinema: dict) -> list[Film]:
    slug = cinema["flicks_slug"]
    today = now_sydney().date()
    merged: dict[str, Film] = {}
    empty_days = 0

    for offset in range(DAYS_AHEAD):
        day = today + timedelta(days=offset)
        url = f"{BASE}/cinema/{slug}/"
        if offset:
            url += f"?date={day.isoformat()}"
        try:
            soup = BeautifulSoup(http_get(url).text, "lxml")
        except Exception:
            if offset == 0:
                raise          # slug is probably wrong — surface it loudly
            break

        day_films = _from_jsonld(_jsonld_events(soup), cinema["id"])
        # JSON-LD carries its own dates; HTML fallback needs the day we asked for
        if not day_films:
            day_films = _from_html(soup, cinema["id"], day)

        if not day_films:
            empty_days += 1
            if empty_days >= 3 and offset > 4:
                break          # ran past the published schedule
            continue

        for key, film in day_films.items():
            if key in merged:
                have = {s.dt for s in merged[key].sessions}
                merged[key].sessions.extend(s for s in film.sessions if s.dt not in have)
            else:
                merged[key] = film

        # JSON-LD pages usually include the full schedule on page one
        if offset == 0 and any(
            s.dt[:10] != today.isoformat()
            for f in merged.values() for s in f.sessions
        ):
            break

    if not merged:
        raise RuntimeError(f"flicks: no films parsed for slug '{slug}'")
    return list(merged.values())
