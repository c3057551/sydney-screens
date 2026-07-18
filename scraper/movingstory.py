"""Scraper for cinemas on the Moving Story platform (Ritz Randwick, Hayden Orpheum).

Page structure (verified against ritzcinemas.com.au, July 2026):

/now-showing            -> today's films
/now-showing/tomorrow   -> tomorrow
/now-showing/monday ... -> named weekdays for the rest of the week
/coming-soon            -> future titles (no session times)

Each film block:
  <a href="/movies/<slug>"><img src=poster></a> RATING <a href="/movies/<slug>">Title</a>
  session links: <a href="/tickets?c=...&s=...">8:00 pm RETRO</a>
Session link text = time followed by optional tags (70MM, NFT, RETRO, MATINEES,
JUNIOR, Selling Fast ...).
"""

from __future__ import annotations

from datetime import timedelta

from bs4 import BeautifulSoup

from common import Film, Session, extract_year, http_get, now_sydney, parse_time_12h

# words in session-link text that are status noise, not format tags worth keeping
NOISE = {"selling", "fast", "sold", "out", "nft", "final"}
KEEP_TAGS = {"70MM", "35MM", "RETRO", "MATINEES", "JUNIOR", "CULT", "OPEN", "CAPTIONS", "Q&A"}


def _day_urls(base_url: str) -> list[tuple[str, "date"]]:
    """Map the 7 day-filter pages to concrete dates."""
    today = now_sydney().date()
    out = [(f"{base_url}/now-showing", today),
           (f"{base_url}/now-showing/tomorrow", today + timedelta(days=1))]
    for offset in range(2, 7):
        d = today + timedelta(days=offset)
        out.append((f"{base_url}/now-showing/{d.strftime('%A').lower()}", d))
    return out


def _parse_session_text(text: str) -> tuple[tuple[int, int] | None, list[str]]:
    hm = parse_time_12h(text)
    tags = []
    for word in text.replace(",", " ").split():
        w = word.strip().upper()
        if w in KEEP_TAGS:
            tags.append(w)
    return hm, tags


def _parse_day_page(html: str, base_url: str, cinema_id: str, day) -> dict[str, Film]:
    soup = BeautifulSoup(html, "lxml")
    films: dict[str, Film] = {}

    for movie_link in soup.select("a[href*='/movies/']"):
        title_text = movie_link.get_text(" ", strip=True)
        if not title_text:            # poster image link — skip, text link follows
            continue
        href = movie_link["href"]
        # Sessions are sibling list items after the title link's parent block.
        container = movie_link.find_parent(["li", "div", "article"]) or movie_link.parent
        session_links = container.select("a[href*='/tickets']") if container else []
        if not session_links:
            continue

        title, year = extract_year(title_text)
        key = href
        film = films.get(key)
        if film is None:
            poster = ""
            img_a = container.select_one("a[href*='/movies/'] img") if container else None
            if img_a and img_a.get("src"):
                poster = img_a["src"]
            rating = ""
            # rating sits as loose text just before the title link
            prev = movie_link.previous_sibling
            while prev is not None and rating == "":
                txt = prev.get_text(strip=True) if hasattr(prev, "get_text") else str(prev).strip()
                if txt in {"G", "PG", "M", "MA15+", "R18+", "CTC", "E"}:
                    rating = txt
                prev = getattr(prev, "previous_sibling", None)
            film = Film(title=title, year=year, cinema_id=cinema_id,
                        url=href if href.startswith("http") else base_url + href,
                        poster=poster, rating=rating)
            films[key] = film

        for s in session_links:
            hm, tags = _parse_session_text(s.get_text(" ", strip=True))
            if hm is None:
                continue
            dt = f"{day.isoformat()}T{hm[0]:02d}:{hm[1]:02d}"
            burl = s["href"]
            if not burl.startswith("http"):
                burl = base_url + burl
            if not any(x.dt == dt for x in film.sessions):
                film.sessions.append(Session(dt=dt, booking_url=burl, tags=tags))

    return films


def _parse_coming_soon(html: str, base_url: str, cinema_id: str) -> list[Film]:
    soup = BeautifulSoup(html, "lxml")
    seen, films = set(), []
    for link in soup.select("a[href*='/movies/']"):
        text = link.get_text(" ", strip=True)
        href = link["href"]
        if not text or href in seen:
            continue
        seen.add(href)
        title, year = extract_year(text)
        films.append(Film(title=title, year=year, cinema_id=cinema_id,
                          url=href if href.startswith("http") else base_url + href,
                          coming_soon=True))
    return films


def scrape(cinema: dict) -> list[Film]:
    base = cinema["base_url"]
    merged: dict[str, Film] = {}

    for url, day in _day_urls(base):
        try:
            html = http_get(url).text
        except Exception:
            continue                     # a missing weekday page is fine
        for key, film in _parse_day_page(html, base, cinema["id"], day).items():
            if key in merged:
                existing = merged[key]
                have = {s.dt for s in existing.sessions}
                existing.sessions.extend(s for s in film.sessions if s.dt not in have)
            else:
                merged[key] = film

    films = list(merged.values())

    try:
        cs_html = http_get(f"{base}/coming-soon").text
        showing_urls = {f.url for f in films}
        films.extend(f for f in _parse_coming_soon(cs_html, base, cinema["id"])
                     if f.url not in showing_urls)
    except Exception:
        pass

    if not films:
        raise RuntimeError(f"movingstory: no films parsed from {base}")
    return films
