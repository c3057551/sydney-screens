# Sydney Screens

One page showing every film — now playing and coming soon — across Sydney's
big-screen cinemas: Ritz Randwick, Hayden Orpheum, Palace Moore Park / Norton
St / Central, Chauvel, Dendy Newtown, Golden Age, and Event George St.

Filter by day, this week, or next week. Search any title to see if it's
playing or coming soon anywhere. Tap a session time to book on the cinema's
own site.

## Setup (once, ~10 minutes)

1. Create a new GitHub repo (e.g. `sydney-screens`) and push this folder to it.
2. In the repo: **Settings → Pages → Source: Deploy from a branch →
   Branch: `main`, folder: `/docs`** → Save.
3. **Settings → Actions → General → Workflow permissions →
   Read and write permissions** → Save. (Lets the scraper commit fresh data.)
4. Go to the **Actions** tab → *Scrape session times* → **Run workflow**.
   This replaces the bundled sample data with live sessions.
5. Open `https://<your-username>.github.io/sydney-screens/` and add it to
   your phone's home screen.

From then on it refreshes itself daily at ~4am Sydney time.

## How it works

```
scraper/
  config.py       cinema registry — which venue, which source, which slug
  movingstory.py  direct scraper for Ritz + Orpheum (their shared platform)
  flicks.py       one scraper covering all other venues via flicks.com.au
  run.py          runs everything, tolerates failures, writes docs/data/films.json
docs/
  index.html      the site (no build step, plain HTML/JS)
  data/films.json the aggregated data the site reads
.github/workflows/scrape.yml   daily schedule
```

Each cinema is scraped independently. If one breaks, the others keep
updating and the site footer shows which venue is stale — it keeps serving
that venue's last good data rather than dropping it.

## When something breaks

- **Footer says a venue is stale** → open the latest run in the Actions tab
  and read the `FAIL` line.
- **A Flicks-sourced venue fails on its first run** → the slug in
  `scraper/config.py` is probably wrong. Search the cinema on flicks.com.au
  and copy the slug from the URL (`flicks.com.au/cinema/<slug>/`).
- **Ritz or Orpheum fail** → they've changed their markup; the fix lives in
  `scraper/movingstory.py`. Run `python scraper/test_parsers.py` after editing.
- **Palace Verona → Moore Park move (Feb 2027)** — both are in the config;
  delete whichever stops screening.

## Running locally

```
pip install requests beautifulsoup4 lxml
python scraper/run.py
cd docs && python -m http.server 8000    # open http://localhost:8000
```
