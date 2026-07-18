"""Cinema registry.

Each cinema is scraped by exactly one source:
  - "movingstory": direct scrape of the cinema's own site (Ritz / Orpheum platform)
  - "flicks":      scrape of the cinema's page on flicks.com.au (uniform aggregator)

If a Flicks slug is wrong, open https://www.flicks.com.au and search the cinema,
then paste the slug from the URL here. Nothing else needs to change.
"""

CINEMAS = [
    {
        "id": "ritz",
        "name": "Ritz Randwick",
        "short": "Ritz",
        "source": "movingstory",
        "base_url": "https://www.ritzcinemas.com.au",
        "flicks_slug": "randwick-ritz-cinema",  # fallback reference
    },
    {
        "id": "orpheum",
        "name": "Hayden Orpheum Cremorne",
        "short": "Orpheum",
        "source": "movingstory",
        "base_url": "https://www.orpheum.com.au",
        "flicks_slug": "hayden-orpheum-picture-palace-cremorne",
    },
    {
        "id": "palace-moore-park",
        "name": "Palace Moore Park (ex-Verona)",
        "short": "Palace MP",
        "source": "flicks",
        "flicks_slug": "palace-moore-park",
    },
    {
        "id": "palace-norton",
        "name": "Palace Norton St Leichhardt",
        "short": "Norton St",
        "source": "flicks",
        "flicks_slug": "palace-cinema-norton-street-leichhardt",
    },
    {
        "id": "palace-central",
        "name": "Palace Central Chippendale",
        "short": "Central",
        "source": "flicks",
        "flicks_slug": "palace-central",
    },
    {
        "id": "chauvel",
        "name": "Chauvel Cinema Paddington",
        "short": "Chauvel",
        "source": "flicks",
        "flicks_slug": "chauvel-cinema-paddington",
    },
    {
        "id": "dendy-newtown",
        "name": "Dendy Newtown",
        "short": "Dendy",
        "source": "flicks",
        "flicks_slug": "dendy-newtown",
    },
    {
        "id": "golden-age",
        "name": "Golden Age Cinema & Bar",
        "short": "Golden Age",
        "source": "flicks",
        "flicks_slug": "golden-age-cinema-and-bar",
    },
    {
        "id": "event-george",
        "name": "Event Cinemas George St",
        "short": "Event Geo St",
        "source": "flicks",
        "flicks_slug": "event-cinemas-george-st",
    },
]

USER_AGENT = (
    "Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 "
    "(KHTML, like Gecko) Chrome/126.0 Safari/537.36 SydneyScreens/1.0 (personal use)"
)

REQUEST_TIMEOUT = 30
TZ = "Australia/Sydney"
