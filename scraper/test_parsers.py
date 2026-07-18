"""Fixture tests for the two parsers. Run: python test_parsers.py"""
import sys
from pathlib import Path
sys.path.insert(0, str(Path(__file__).parent))

from datetime import date
from bs4 import BeautifulSoup
import movingstory, flicks

RITZ_DAY_HTML = """
<html><body><ul>
<li>
  <a href="/movies/70mm-the-odyssey"><img src="https://img/odyssey.jpg"></a>
  <span>M</span>
  <a href="/movies/70mm-the-odyssey">70mm The Odyssey</a>
  <ul>
    <li><a href="/tickets?c=0000000004&s=79971">12:00 pm 70MM, NFT</a></li>
    <li><a href="/tickets?c=0000000004&s=79970">3:45 pm 70MM, NFT Selling Fast</a></li>
    <li><a href="/tickets?c=0000000004&s=79969">7:30 pm 70MM, NFT Selling Fast</a></li>
  </ul>
</li>
<li>
  <a href="/movies/come-and-see-1985"><img src="https://img/cas.jpg"></a>
  <span>M</span>
  <a href="/movies/come-and-see-1985">Come and See (1985)</a>
  <ul><li><a href="/tickets?c=0000000004&s=85996">8:00 pm RETRO</a></li></ul>
</li>
<li>
  <a href="/movies/the-philadelphia-story-1940"><img src="https://img/ps.jpg"></a>
  <span>PG</span>
  <a href="/movies/the-philadelphia-story-1940">The Philadelphia Story (1940)</a>
  <ul><li><a href="/tickets?c=0000000004&s=77049">2:00 pm MATINEES, RETRO</a></li></ul>
</li>
</ul></body></html>
"""

FLICKS_JSONLD = """
<html><head><script type="application/ld+json">
[{"@type":"ScreeningEvent","name":"Saving Private Ryan",
  "workPresented":{"name":"Saving Private Ryan (1998)","url":"https://www.flicks.com.au/movie/saving-private-ryan/","image":"https://img/spr.jpg"},
  "startDate":"2026-07-24T19:00:00+10:00","url":"https://book/1"},
 {"@type":"ScreeningEvent","name":"Saving Private Ryan",
  "workPresented":{"name":"Saving Private Ryan (1998)"},
  "startDate":"2026-07-25T15:30:00+10:00","url":"https://book/2"}]
</script></head><body></body></html>
"""


def test_movingstory():
    films = movingstory._parse_day_page(
        RITZ_DAY_HTML, "https://www.ritzcinemas.com.au", "ritz", date(2026, 7, 18)
    )
    assert len(films) == 3, f"expected 3 films, got {len(films)}"
    ody = films["/movies/70mm-the-odyssey"]
    assert len(ody.sessions) == 3
    assert ody.sessions[0].dt == "2026-07-18T12:00"
    assert "70MM" in ody.sessions[0].tags and "NFT" not in ody.sessions[0].tags
    assert ody.rating == "M" and ody.poster == "https://img/odyssey.jpg"
    assert ody.sessions[1].booking_url.endswith("s=79970")
    cas = films["/movies/come-and-see-1985"]
    assert cas.title == "Come and See" and cas.year == 1985
    assert cas.sessions[0].tags == ["RETRO"]
    ps = films["/movies/the-philadelphia-story-1940"]
    assert ps.sessions[0].dt == "2026-07-18T14:00"
    assert set(ps.sessions[0].tags) == {"MATINEES", "RETRO"}
    print("movingstory parser: OK")


def test_flicks():
    soup = BeautifulSoup(FLICKS_JSONLD, "lxml")
    films = flicks._from_jsonld(flicks._jsonld_events(soup), "golden-age")
    assert len(films) == 1
    f = next(iter(films.values()))
    assert f.title == "Saving Private Ryan" and f.year == 1998
    assert [s.dt for s in f.sessions] == ["2026-07-24T19:00", "2026-07-25T15:30"]
    assert f.poster == "https://img/spr.jpg"
    print("flicks parser: OK")


if __name__ == "__main__":
    test_movingstory()
    test_flicks()
    print("All parser tests passed.")
