# Cold-Pitch Site Generator

Find local businesses that don't have a website, automatically build each one a
clean one-page site mockup, and draft a short cold-outreach pitch (email +
Facebook DM) to send them. Everything the sites need is static HTML/CSS, and
every business flows through a single tracker — the CRM.

## The pipeline

```
scraper/run.py        →  Supabase cold_pitch.leads   (discover + rank → status: New)
scraper/promote.py    →  businesses/<slug>/          (chosen leads → status: Building)
Claude (per CLAUDE.md)→  businesses/<slug>/site + pitch.md
vercel deploy         →  one Next.js app: CRM at /admin, sites at /<slug>/
```

1. **Scrape** — `scraper/` crawls Google Maps for businesses with no/outdated
   website, ranks them by likelihood to buy, and downloads their real photos +
   reviews into the CRM (Supabase `cold_pitch.leads`).
2. **Promote** — pick winners from the CRM; `scraper/promote.py` turns each into
   a buildable `businesses/<slug>/` folder (`info.txt` + `images/`).
3. **Build** — Claude reads `info.txt` and designs a one-page site using the
   guides in `skills/`. The full build workflow lives in **CLAUDE.md**.
4. **Pitch** — a cold email + Facebook DM are drafted in `businesses/<slug>/pitch.md`.
5. **Deploy** — the CRM and all sites ship together as one Next.js app on Vercel:
   the dashboard at `/admin`, each business site at `https://<your-domain>/<slug>/`.

## Project structure

```
scraper/           automated lead scraper (standalone Python/Playwright project)
  pipeline/        the package: maps, scoring, crm, photos, enrichment, …
  run.py           entry point — crawl + rank + enrich into the CRM
  promote.py       turn a chosen CRM lead into a businesses/<slug>/ folder
  crm_cli.py       JSON bridge so non-Python tools can read/write the CRM
  states/          target cities (nj.csv, ny.csv, …)
  tests/           offline logic suite + single-listing debug harness
supabase/
  schema.sql       THE tracker's schema: cold_pitch.leads table + lead-photos bucket
leads/             local scrape outputs (raw snapshot + downloaded photos)
  photos/          real photos downloaded per lead (<crm-slug>/), also uploaded to Storage
businesses/        one folder per promoted business
  <slug>/
    info.txt       business details (see root info.txt for the template)
    images/        logo + real photos
    site/          generated website (index.html, styles.css)
    pitch.md       drafted email + DM
crmInterface/      Next.js dashboard for viewing and managing leads
  src/app/admin/   dashboard pages (login-gated) + /api route handlers
  src/lib/         Supabase data layer (cold_pitch.leads) + auth clients
  src/             React + Tailwind + shadcn/ui frontend
  .next/           build output (npm run build)
intake/            localhost web form to add a business by hand → CRM
skills/            design + copy + SEO + outreach guides used during the build
CLAUDE.md          full build workflow and house rules (read this to build sites)
```

## Setup

```bash
# Supabase (one-time): create a project, run supabase/schema.sql in the SQL
# editor, add `cold_pitch` to Settings → API → Exposed schemas, create login
# users, then fill in credentials:
#   .env                    (project root)   → SUPABASE_URL, SUPABASE_SERVICE_ROLE_KEY
#   crmInterface/.env.local                  → NEXT_PUBLIC_SUPABASE_URL,
#                                               NEXT_PUBLIC_SUPABASE_ANON_KEY,
#                                               SUPABASE_SERVICE_ROLE_KEY
# (copy the .env.example templates).

# Scraper (Python)
pip install -r scraper/requirements.txt
playwright install chromium

# Intake form (Node, optional)
cd intake && npm install

# CRM Dashboard (Node)
cd crmInterface && npm install && npm run build
```

## Quick start

```bash
# 1. Discover and rank leads into Supabase cold_pitch.leads
python scraper/run.py
#   …or filter the crawl:
python scraper/run.py --state nj --cities "Newark,Edison" --categories "hair salon,barbershop"
#   (or run it from the dashboard's Scrape tab — local-only)

# 2. Review and manage leads in the dashboard
cd crmInterface && npm run dev               # → http://localhost:3000

# 3. Promote the best leads into buildable businesses/ folders
#    (or click "Build Directory" in the dashboard)
python scraper/promote.py --min-score 80          # batch by score
python scraper/promote.py --slug "<crm-slug>"     # or one at a time

# 4. Build a site — see CLAUDE.md (Claude reads businesses/<slug>/info.txt)

# Manual entry instead of scraping:
cd intake && node server.js                        # → http://localhost:3000
```

All commands run from the project root; the scraper resolves its own paths, so
downloaded photos always land in `leads/photos/` regardless of where you run from.

## CRM Dashboard (`crmInterface/`)

A web UI for managing your lead pipeline. The `/admin` dashboard is behind a
Supabase Auth login (create users in the Supabase dashboard); the public business
sites at `/<slug>/` need no login.

```bash
cd crmInterface
npm run dev              # dev server → http://localhost:3000
# or, production build:
npm run build && npm run start   # → http://localhost:3000 (set PORT to change)
```

| Feature | What it does |
|---|---|
| **Pipeline table** | Every lead with colored status chip, business name, and editable URL field |
| **Scrape tab** | Run the scraper by state + business type with a live log (local-only) |
| **Status dropdown** | Click to change: New / Built / Emailed / Emailed+Called / Won / Lost |
| **Build Directory** | Runs `promote.py` for that lead — creates `businesses/<slug>/` and sets Site Slug in the CRM |
| **Delete** | Removes the CRM row + the `businesses/<slug>/` folder (with confirmation) |
| **Detail page** | Click any row → all 25+ scraped fields, photo gallery (Storage), external links |
| **Search** | Filter by name, type, area, or email |

The Next.js `/api` route handlers query Supabase directly (service-role,
server-side). The **Build** button shells to `scraper/promote.py` — a local-only
action, since it creates folders on disk.

## The CRM (Supabase `cold_pitch.leads`)

The single source of truth — a Postgres table in Supabase (schema `cold_pitch`,
defined in `supabase/schema.sql`). Status pipeline:
`New → Contacted → Building → Sent → Won/Lost`. You own the `Status`, `Notes`,
`Contacted On`, `Site Slug`, and `Preview URL` columns (a re-scrape never
overwrites them); the scraper owns everything else and refreshes it each run.
Edit in the `/admin` dashboard, or via `python scraper/crm_cli.py {add|list|set}`.

## Docs

- **CLAUDE.md** — the build workflow, naming/URL rules, and house rules.
- **scraper/README.md** — scraper configuration, scoring weights, and tuning.
