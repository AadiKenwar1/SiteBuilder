# Lead Scraper

Finds local businesses without websites (or with outdated ones), ranks them by how likely they are to buy, downloads their real photos, and writes a persistent CRM (Supabase `cold_pitch.leads`) you work in via the `/admin` dashboard.

Requires Supabase credentials in a project-root `.env` (`SUPABASE_URL`, `SUPABASE_SERVICE_ROLE_KEY` — see `.env.example`). Run `supabase/schema.sql` once to create the table + `lead-photos` bucket.

---

## How it works

**Phase 1 — Screen**
Searches Google Maps across every category × city combination in your `states/` folder. For each listing it checks whether the business has no website or an outdated one, filters out chains and over-popular businesses, finds their Facebook and Instagram, and scores them on how likely they are to buy a website.

**Rank**
Sorts all screened candidates by score. Only the top `TARGET_LEADS` move forward.

**Phase 2 — Enrich (keepers only)**
For the top-ranked leads only: downloads the real photo gallery from Google Maps, scrapes reviews, deep-searches for a contact email, then recomputes the final score with all data in hand.

**Output**
- Supabase `cold_pitch.leads` — your working CRM. Persistent across runs: new businesses are inserted, existing ones refreshed, your hand-entered Status/Notes never touched (`save_crm` upserts scraper-owned columns only).
- `leads/photos/<business-slug>/` — real photos per business (hero + gallery), also uploaded to the public `lead-photos` Storage bucket.
- `leads/leads_no_website.xlsx` — raw snapshot of this run (overwritten each time).
- `leads/leads_no_website.csv` / `leads/reviews.csv` — CSV versions.

---

## Setup

**1. Install dependencies**
```
pip install -r requirements.txt
```

**2. Install Playwright's browser**
```
playwright install chromium
```

**3. Add your target cities**

Drop a CSV file into the `states/` folder named by state code (e.g. `nj.csv`). It needs one column called `city`:

```
city
Newark
Jersey City
Paterson
```

You can have multiple state files — all cities across all files are loaded and shuffled each run.

---

## Configuration

All settings are in `scraper/config.py`.

| Setting | Default | What it does |
|---|---|---|
| `TARGET_LEADS` | 5 | Leads fully enriched and pushed to the CRM per run |
| `SCREEN_TARGET` | 20 | Candidates screened and scored before ranking. Keep at ~4× `TARGET_LEADS` |
| `HEADLESS` | `True` | `False` = visible browser (use this for your first run) |
| `MAX_PHOTOS` | 8 | Photos downloaded per kept lead |
| `MAX_REVIEWS_SCRAPE` | 10 | Reviews scraped per kept lead |
| `MAX_REVIEWS` | 150 | Skip businesses with more reviews than this (likely chains) |
| `OUTDATED_YEARS` | 10 | Websites last updated more than this many years ago count as outdated |
| `CATEGORY_SEARCHES` | 40 categories | Business types to search on Maps |
| `SCORE_WEIGHTS` | see config | Tune how each signal affects the likelihood-to-buy score |

**Recommended settings for a real run:**
```python
HEADLESS      = False   # keep visible for your first run to handle any CAPTCHAs
TARGET_LEADS  = 50
SCREEN_TARGET = 200
```

For overnight runs flip `HEADLESS` back to `True`.

---

## Running

```
python scraper/run.py
```

The terminal shows live progress through both phases:

```
PHASE 1 — screening candidates ...
[screen 0/200] 'restaurant' in Jersey City, NJ
  12 listings found
  + [ 88] [NO SITE] Joe's Diner
  + [ 72] [OUTDATED] Mama Rosa Kitchen
...
RANKED 200 candidates -> enriching top 50

[1/50] BIZ_001 [88] Joe's Diner
      photos saved -> outputs\photos\joe-s-diner-123-main-st  (7 files)
      [+] [91] joe@joesdiner.com | 7 photos | 8 reviews
```

---

## The CRM (Supabase `cold_pitch.leads`)

A Postgres table in Supabase (schema `cold_pitch`); view/edit it live in the `/admin` dashboard. Schema + photo bucket are defined in `supabase/schema.sql`.

| Column | Who owns it |
|---|---|
| Status, Notes, Contacted On | **You** — never overwritten by re-runs |
| Everything else | Scraper — refreshed on each run |

**Status values:** `New` → `Contacted` → `Building` → `Sent` → `Won` / `Lost`

Each row has:
- An embedded thumbnail of the business's hero photo
- A clickable **"open folder"** link that opens the full photo gallery in Explorer
- Score (0–100) — sorted highest first

---

## Testing

**Tier 1 — Offline logic suite** (fast, no browser, run any time):
```
python scraper/tests/test_logic.py
```
Covers scoring, CRM merge behavior, email cleaning, slug stability, photo URL helpers, and website-age parsing.

**Tier 2 — Single-listing debug harness** (browser, one Maps URL):
```
python scraper/tests/debug_listing.py "<google_maps_place_url>" "Business Name" "Address"
```
Runs only Phase 2 (photo gallery + reviews) against one listing so you can debug selectors without running a full crawl. Find the URL by searching the business on Google Maps, clicking its panel, and copying the address bar URL.

---

## Scoring

Each lead gets a score from 0–100 based on signals already collected in Phase 1. Weights are in `config.SCORE_WEIGHTS` and can be tuned freely.

| Signal | Default weight |
|---|---|
| No website | 30 |
| Has email | 12 |
| Has Facebook | 10 |
| Visual business type (salon, restaurant, etc.) | 10 |
| Outdated website | 15 |
| Reviews in sweet spot (5–100) | 12 |
| Good rating (4.0+) | 8 |
| Has phone | 8 |
| Has Instagram | 8 |
| Year established found | 5 |
| Photos downloaded | 5 |

Email and social are **signals**, not gates — a no-email lead with strong other signals still makes the top-N and gets fully enriched.

---

## Adding more cities or states

Add a new CSV to `states/` named by state code:

```
states/
  nj.csv
  ny.csv
  pa.csv
```

Each file just needs a `city` column. All cities across all files are loaded, shuffled, and iterated in a different order every run so coverage spreads evenly over time.

---

## Project structure

```
run.py                  entry point
scraper/
  config.py             all settings and tunable weights
  runner.py             two-phase orchestration loop
  models.py             Lead and Review dataclasses
  maps.py               Google Maps scraping (search + listing extraction + reviews)
  photos.py             Maps photo gallery downloader
  enrichment.py         Facebook / Instagram scraping
  email_finder.py       email search (website → Google → Facebook)
  website_check.py      outdated-site detection
  chain_check.py        chain / big-business filter
  scoring.py            likelihood-to-buy scorer
  export.py             raw Excel / CSV output
  db.py                 Supabase CRM data layer (merge upsert + photo upload)
  utils.py              shared helpers (slug, delay, download_image, browser)
states/
  nj.csv                target cities
outputs/
  leads_no_website.xlsx raw snapshot (overwritten each run)
  photos/               one folder per kept lead
tests/
  test_logic.py         Tier 1 offline test suite
  debug_listing.py      Tier 2 single-listing debug harness
```
