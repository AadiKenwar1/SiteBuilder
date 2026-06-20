# Cold-Pitch Site Generator

Find local businesses that don't have a website, automatically build each one a
clean one-page site, and draft a short cold-outreach pitch (email + Facebook DM)
to send them. Each site is **content-driven and editable** — the design is
bespoke, but the words and photos come from a Supabase row the owner can edit
themselves. Sites are previewed under one shared domain and, when a business buys,
handed off to them as their own deployment. Every business flows through a single
tracker — the CRM.

> **Migration in progress.** The project is moving from frozen static
> `businesses/<slug>/site/index.html` to the shared `sites/` Next.js app described
> below. The full plan + build order is in **SITES-PLATFORM-PLAN.md**; house rules
> are in **CLAUDE.md**.

## The pipeline

```
scraper/run.py         →  Supabase cold_pitch.leads                 (discover + rank → New)
scraper/promote.py     →  businesses/<slug>/ + business_content row  (chosen → Building)
Claude (per CLAUDE.md) →  sites/designs/<slug>/Site.tsx + pitch.md
vercel deploy (sites/) →  all previews at previews.<domain>/<slug>   (ISR, owner-editable)
scripts/eject.mjs      →  on sale: standalone Vercel project, claimed by the owner
```

1. **Scrape** — `scraper/` crawls Google Maps for businesses with no/outdated
   website, ranks them by likelihood to buy, and downloads their real photos +
   reviews into the CRM (Supabase `cold_pitch.leads`).
2. **Promote** — pick winners from the CRM; `scraper/promote.py` writes a buildable
   `businesses/<slug>/` folder (`info.txt` + `images/`), seeds the editable
   `cold_pitch.business_content` row, and scaffolds `sites/designs/<slug>/`.
3. **Build** — Claude reads `info.txt` and writes a bespoke, content-driven design
   into `sites/designs/<slug>/Site.tsx` using the guides in `skills/`. Full
   workflow in **CLAUDE.md**.
4. **Pitch** — a cold email + Facebook DM are drafted in `businesses/<slug>/pitch.md`.
5. **Preview** — the `sites/` app serves every business at
   `previews.<domain>/<slug>`, reading its content row (ISR). Owners edit hours,
   phone, about, services, and photos via a magic-link login at `/<slug>/admin`.
6. **Hand off** — when a business buys, `scripts/eject.mjs <slug>` lifts that one
   site into its own Vercel project and transfers it (Claim Deployments) to the
   owner, who keeps editing it.

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
  schema.sql       cold_pitch schema: leads + business_content tables, view, RLS,
                   lead-photos + business-photos buckets
leads/             local scrape outputs (raw snapshot + downloaded photos)
  photos/          real photos downloaded per lead (<crm-slug>/), also uploaded to Storage
businesses/        one folder per promoted business
  <slug>/
    info.txt       raw scrape dump Claude reads to design (prose; not rendered)
    images/        logo + real photos
    content.json   optional structured content to fix/enrich the business_content
                   row (pushed via scraper/content_cli.py); skip when scrape is clean
    pitch.md       drafted email + DM
                   (no site/ — the design lives in sites/designs/<slug>/)
sites/             shared Next.js app: every business site, one domain (previews.<domain>)
  app/[slug]/      one route for all sites — reads business_content, renders the design (ISR)
  app/[slug]/admin/  owner magic-link login + edit form
  designs/<slug>/  the bespoke per-business design Claude writes (Site.tsx + styles.css)
  lib/ components/  anon Supabase clients, content reader, design registry, shared chrome
templates/
  business-site/   eject overlay (root rewrite) copied into a standalone on handoff
scripts/
  eject.mjs        build + deploy + claim a sold site into its own Vercel project
crmInterface/      Next.js dashboard for viewing and managing leads
  src/app/admin/   dashboard pages (login-gated) + /api route handlers
  src/lib/         Supabase data layer (cold_pitch.leads) + auth clients
  src/             React + Tailwind + shadcn/ui frontend
intake/            localhost web form to add a business by hand → CRM
skills/            design + copy + SEO + outreach guides used during the build
CLAUDE.md          full build workflow and house rules (read this to build sites)
SITES-PLATFORM-PLAN.md   architecture + build order for the sites platform
```

## Setup

```bash
# Supabase (one-time): create a project, run supabase/schema.sql in the SQL
# editor, add `cold_pitch` to Settings → API → Exposed schemas, create CRM login
# users, then fill in credentials:
#   .env                    (project root)   → SUPABASE_URL, SUPABASE_ANON_KEY,
#                                               SUPABASE_SERVICE_ROLE_KEY
#   crmInterface/.env.local                  → NEXT_PUBLIC_SUPABASE_URL,
#                                               NEXT_PUBLIC_SUPABASE_ANON_KEY,
#                                               SUPABASE_SERVICE_ROLE_KEY
# (copy the .env.example templates).
#
# For the sites/ app and owner logins, also in the Supabase dashboard:
#   • Authentication → Providers → Email: enable, with "Email OTP / magic link".
#   • Authentication → URL Configuration → Redirect URLs: add
#       http://localhost:3001/auth/callback
#       https://previews.<your-domain>/auth/callback
#   • schema.sql already creates the public `business-photos` Storage bucket.

# Scraper (Python)
pip install -r scraper/requirements.txt
playwright install chromium

# CRM Dashboard (Node)
cd crmInterface && npm install && npm run build

# Sites app (Node) — serves every business preview; ANON key only
cd sites && npm install && npm run build
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

## Sites platform (`sites/`)

The shared Next.js app that serves every business preview from one deploy, and the
editor each owner uses.

```bash
cd sites
npm run dev             # → http://localhost:3001/<slug>   (reads cold_pitch.business_content)
npm run build           # production build
```

- **One route, many sites.** `app/[slug]/page.tsx` reads the business's row and
  renders its design from `designs/<slug>/` (falling back to `designs/_reference/`
  until Claude writes a bespoke one). ISR (`revalidate: 60`) keeps it fast and
  current.
- **Anon key only.** The public site reads a column-filtered view with the anon
  key; it never holds the service-role key. Owner edits go through a
  security-definer RPC gated on `auth.email() = owner_email`, and photo uploads
  through a storage policy — both anon-safe.
- **Owner editor.** A discreet "Owner login" link → `/<slug>/admin`, a passwordless
  magic-link login restricted to the row's `owner_email`. Saves revalidate the live
  page within ~a minute.
- **Eject on sale.** `node scripts/eject.mjs <slug>` builds a standalone copy
  (anon-only) under `.eject/<slug>/`, ready to `vercel deploy` as its own project
  and transfer to the customer. Then flip `business_content.site_status` to
  `active` (drops the noindex). The script prints the exact follow-up steps.

Deploy the previews as one Vercel project (Root Directory = `sites`, env =
`NEXT_PUBLIC_SUPABASE_URL` + `NEXT_PUBLIC_SUPABASE_ANON_KEY` only), pointed at the
`previews.<domain>` subdomain. The CRM (`crmInterface/`) deploys separately to
`app.<domain>`.

## Docs

- **CLAUDE.md** — the build workflow, naming/URL rules, and house rules.
- **SITES-PLATFORM-PLAN.md** — sites platform architecture, data model, build order.
- **scraper/README.md** — scraper configuration, scoring weights, and tuning.
