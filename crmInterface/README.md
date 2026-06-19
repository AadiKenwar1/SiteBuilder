# crmInterface

One Next.js app that serves both the CRM dashboard **and** every generated
business site. The dashboard (view leads, change status, edit preview URLs,
build/rebuild a lead's `businesses/<slug>/` folder, delete leads) lives under
`/admin`; each business site is served at the clean root path `/<slug>/`. Built
with **Next.js (App Router) + React + Tailwind + shadcn/ui**.

## How it works
The single source of truth is the Supabase `cold_pitch.leads` table. The Next.js
route handlers under `src/app/api/` query Supabase directly with the
**service-role** key (`src/lib/crm.server.ts` → `src/lib/supabase.server.ts`).
The one exception is **Build**, which shells out to `scraper/promote.py` (a
local-only action — it creates `businesses/<slug>/` folders on disk). The browser
calls the `/api/*` routes (see `src/lib/api.ts`); it never holds the service-role
key.

The `/admin` dashboard is gated by Supabase Auth (`src/middleware.ts` →
`/admin/login`); business sites at `/<slug>/` stay public. Lead photos are served
from the public `lead-photos` Storage bucket (URLs stored on each row).

Env (`.env.local`, see `.env.example`): `NEXT_PUBLIC_SUPABASE_URL`,
`NEXT_PUBLIC_SUPABASE_ANON_KEY`, `SUPABASE_SERVICE_ROLE_KEY`.

## Routes
- `/` — redirects to `/admin`
- `/admin/login` — Supabase Auth sign-in (public)
- `/admin` — the pipeline dashboard, login-gated (`src/app/admin/page.tsx`)
- `/admin/b/[slug]` — a single lead's detail page (`src/app/admin/b/[slug]/page.tsx`)
- `/admin/scrape` — run the scraper with state + business-type filters (local-only, `src/app/admin/scrape/page.tsx`)
- `/<slug>/` — a generated business site (static, served from `public/<slug>/`, public)
- `GET /api/leads` — list every lead
- `GET|PATCH|DELETE /api/leads/[slug]` — read / set a field / delete a lead
- `POST /api/leads/[slug]/build` — promote the lead into a buildable folder (local-only)
- `GET|POST /api/scrape` — scrape job status+log / start a run (local-only)
- `GET /api/scrape/options` — states, cities, and business types for the filters
- `POST /api/scrape/stop` — kill the running scrape

Reserved words a business slug can't use (they're real routes): `admin`,
`api`, `photos`, `_next`. The slug generators enforce this.

## Scrape tab (local-only)
`/admin/scrape` runs `scraper/run.py` as a background process for the state +
business types you pick, streaming a live log tail. Like the
Build button it shells to Python + Playwright + the local filesystem, so it only
works when the app runs locally — `src/lib/scrape.server.ts` guards on
`process.env.VERCEL`, so the routes return 503 (and the tab shows a notice) when
deployed. Dropdown options come from `scraper/options.py` (the single source of
truth for cities + categories). Only one scrape runs at a time; its log lives at
`scraper/.run/scrape.log`.

## Business sites in `public/`
`scripts/copy-sites.mjs` runs as a `prebuild`/`predev` hook. It stages every
built site from `../businesses/<slug>/site/` (plus its sibling `images/`) into
`public/<slug>/`, rewriting `../images/` → `images/` so assets resolve, and
skips `info.txt`. `../businesses/` stays the source of truth; everything under
`public/` except `favicon.svg`/`icons.svg` is a gitignored build artifact.
After building a new site, re-run `npm run copy-sites` (or just `npm run dev`).

## Run it
```
npm install
npm run dev          # http://localhost:3000 (Next dev server)
```
Or a production build:
```
npm run build
$env:PORT=4000; npm run start   # PowerShell — serve on port 4000
```
Set `.env.local` (see `.env.example`) first. `python` on PATH is needed only for
the local **Build** button (it shells to `promote.py`); all other data ops are
pure Supabase.

## Deployment note
The `/api` data routes are serverless-ready (Supabase, no Python/filesystem), so
this deploys to Vercel. Deploy with Root Directory = `crmInterface` and the
**"Include files outside the root directory"** option enabled so the build's
`copy-sites` step can read `../businesses`. `vercel.json` pins the framework and
build command. Set the three Supabase env vars on the Vercel project. The Build
button won't work in the deployed app (no Python) — promotion stays a local step.
