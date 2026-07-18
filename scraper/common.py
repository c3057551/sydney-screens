"""Shared data model + helpers."""

from __future__ import annotations

import re
import unicodedata
from dataclasses import dataclass, field
from datetime import datetime
from zoneinfo import ZoneInfo

import requests

from config import USER_AGENT, REQUEST_TIMEOUT, TZ

SYDNEY = ZoneInfo(TZ)


@dataclass
class Session:
    dt: str                      # ISO local datetime "2026-07-18T19:30"
    booking_url: str = ""
    tags: list[str] = field(default_factory=list)   # e.g. ["70MM", "RETRO"]


@dataclass
class Film:
    title: str
    cinema_id: str
    url: str = ""
    poster: str = ""
    rating: str = ""             # G / PG / M / MA15+ / R18+
    year: int | None = None
    coming_soon: bool = False
    sessions: list[Session] = field(default_factory=list)

    def to_dict(self) -> dict:
        return {
            "title": self.title,
            "cinema_id": self.cinema_id,
            "url": self.url,
            "poster": self.poster,
            "rating": self.rating,
            "year": self.year,
            "coming_soon": self.coming_soon,
            "sessions": [
                {"dt": s.dt, "booking_url": s.booking_url, "tags": s.tags}
                for s in self.sessions
            ],
        }


def http_get(url: str, **kw) -> requests.Response:
    headers = kw.pop("headers", {})
    headers.setdefault("User-Agent", USER_AGENT)
    headers.setdefault("Accept-Language", "en-AU,en;q=0.9")
    resp = requests.get(url, headers=headers, timeout=REQUEST_TIMEOUT, **kw)
    resp.raise_for_status()
    return resp


def now_sydney() -> datetime:
    return datetime.now(SYDNEY)


YEAR_IN_TITLE = re.compile(r"\((19|20)\d{2}\)\s*$")


def extract_year(title: str) -> tuple[str, int | None]:
    """'Come and See (1985)' -> ('Come and See', 1985)."""
    m = YEAR_IN_TITLE.search(title)
    if m:
        return title[: m.start()].strip(), int(m.group(0).strip("() "))
    return title.strip(), None


def norm_title(title: str) -> str:
    """Normalised key used to group the same film across cinemas."""
    t = unicodedata.normalize("NFKD", title).encode("ascii", "ignore").decode()
    t = t.lower()
    t = re.sub(r"\((19|20)\d{2}\)", "", t)          # strip year
    t = re.sub(r"\b(70mm|35mm|4k|imax|digital|restoration|extended)\b", "", t)
    t = re.sub(r"[^a-z0-9]+", " ", t).strip()
    return t


def parse_time_12h(text: str) -> tuple[int, int] | None:
    """'8:00 pm' -> (20, 0); '11:30am' -> (11, 30)."""
    m = re.search(r"(\d{1,2})[:.](\d{2})\s*(am|pm)", text, re.I)
    if not m:
        m2 = re.search(r"(\d{1,2})\s*(am|pm)", text, re.I)
        if not m2:
            return None
        h, mnt, ap = int(m2.group(1)), 0, m2.group(2).lower()
    else:
        h, mnt, ap = int(m.group(1)), int(m.group(2)), m.group(3).lower()
    if ap == "pm" and h != 12:
        h += 12
    if ap == "am" and h == 12:
        h = 0
    if not (0 <= h < 24 and 0 <= mnt < 60):
        return None
    return h, mnt
