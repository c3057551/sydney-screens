"""Scraper for cinemas on the Veezi ticketing platform.

Veezi hosts a per-site JSON feed keyed by a public siteToken. This is a
structured data source — far more robust than HTML scraping — and returns
the full forward schedule in one request.

Region + token live in config.py (veezi_region, veezi_token). For the
Hayden Orpheum:  region "oz", token "r8mwhyjp18cvqve5jnf7456pcr", found in
its ticketing.oz.veezi.com/purchase/... booking URL.

Feed shape (Veezi V-Tix public sessions JSON): a list of session objects,
each roughly:
  {
    "Id": "...", "FilmId": "...", "Title": "The Odyssey",
    "PreShowStartTime": "2026-07-19T19:30:00",   # local
    "Rating": "M", "FilmFormat": "70mm", "Duration": 210,
    "Attributes": ["70mm", "No Free Tickets"], ...
  }
Field names vary slightly by Veezi version, so every access is defensive:
we try several known keys and skip anything we can't parse rather than
crashing the whole run.
"""

from __future__ import annotations

import json
import re
from datetime import datetime

from common import Film, Session, extract_year, http_get, now_sydney

# Candidate feed URLs, tried in order. The first that returns usable JSON wins.
FEED_TEMPLATES = [
    "https://ticketing.{region}.veezi.com/sessions/?siteToken={token}&format=json",
    "https://ticketing.{region}.veezi.com/api/v1/sessions/?siteToken={token}",
    "https://ticketing.{region}.veezi.com/sessions/?siteToken={token}",
]

PURCHASE_URL = "https://ticketing.{region}.veezi.com/purchase/{film}?siteToken={token}"

# Attribute strings worth surfacing as badges (upper-cased on match)
KEEP_ATTRS = {
    "70MM": "70MM", "35MM": "35MM", "4K": "4K", "IMAX": "IMAX",
    "RETRO": "RETRO", "CULT": "CULT", "Q&A": "Q&A",
    "SUBTITLED": "SUBTITLED", "SILVER SCREEN": "RETRO",
    "MET OPERA": "EVENT", "PARENTS": "PARENTS",
}


def _first(d: dict, *keys, default=None):
    for k in keys:
        if k in d and d[k] not in (None, ""):
            return d[k]
    return default


def _parse_dt(raw: str) -> str | None:
    """Veezi times are local ISO-ish. Return 'YYYY-MM-DDTHH:MM' or None."""
    if not raw:
        return None
    m = re.match(r"(\d{4})-(\d{2})-(\d{2})[T ](\d{2}):(\d{2})", str(raw))
    if not m:
        return None
    y, mo, d, h, mi = m.groups()
    return f"{y}-{mo}-{d}T{h}:{mi}"


def _attrs_to_tags(session: dict) -> list[str]:
    raw = _first(session, "Attributes", "SessionAttributes", "attributes", default=[]) or []
    fmt = _first(session, "FilmFormat", "Format", default="")
    pool = []
    if isinstance(raw, list):
        pool.extend(str(x) for x in raw)
    elif isinstance(raw, str):
        pool.append(raw)
    if fmt:
        pool.append(str(fmt))
    tags = []
    for item in pool:
        key = item.strip().upper()
        for needle, tag in KEEP_ATTRS.items():
            if needle in key and tag not in tags:
                tags.append(tag)
    return tags


def _load_feed(region: str, token: str) -> list:
    last_err = None
    for tmpl in FEED_TEMPLATES:
        url = tmpl.format(region=region, token=token)
        try:
            resp = http_get(url, headers={"Accept": "application/json"})
        except Exception as e:
            last_err = e
            continue
        text = resp.text.strip()
        if not text or text[0] not in "[{":
            last_err = RuntimeError(f"non-JSON from {url}")
            continue
        try:
            data = json.loads(text)
        except Exception as e:
            last_err = e
            continue
        # Feed may be a bare list or wrapped, e.g. {"Sessions":[...]}
        if isinstance(data, dict):
            for key in ("Sessions", "sessions", "data", "Data", "items"):
                if isinstance(data.get(key), list):
                    return data[key]
            # single object — wrap it
            return [data]
        if isinstance(data, list):
            return data
    raise RuntimeError(f"veezi: no usable feed ({last_err})")


def scrape(cinema: dict) -> list[Film]:
    region = cinema["veezi_region"]
    token = cinema["veezi_token"]
    base = cinema.get("base_url", "")

    sessions_raw = _load_feed(region, token)
    today = now_sydney().date().isoformat()

    films: dict[str, Film] = {}
    for s in sessions_raw:
        if not isinstance(s, dict):
            continue
        title_raw = _first(s, "Title", "FilmTitle", "Name", "ShortName")
        dt = _parse_dt(_first(s, "PreShowStartTime", "StartTime", "SessionTime",
                              "ScheduledFilmStartTime", "Showtime"))
        if not title_raw or not dt:
            continue
        if dt[:10] < today:            # skip past sessions
            continue

        title, year = extract_year(str(title_raw).strip())
        key = title.lower()
        film = films.get(key)
        if film is None:
            film = Film(
                title=title,
                year=year,
                cinema_id=cinema["id"],
                rating=str(_first(s, "Rating", "Classification", default="")).strip(),
                url=base,
            )
            films[key] = film

        film_id = _first(s, "FilmId", "ScheduledFilmId", "Id", default="")
        booking = PURCHASE_URL.format(region=region, film=film_id, token=token) if film_id else base
        if not any(x.dt == dt for x in film.sessions):
            film.sessions.append(Session(dt=dt, booking_url=booking, tags=_attrs_to_tags(s)))

    result = [f for f in films.values() if f.sessions]
    if not result:
        raise RuntimeError("veezi: feed returned no future sessions")
    return result
