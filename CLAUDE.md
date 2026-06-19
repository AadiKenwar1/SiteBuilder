# Cold-Pitch Site Generator

## What this project does
For each small business in `businesses/`, generate a clean one-page website
mockup and a short cold-outreach pitch (email + Facebook DM), to send to
businesses found in Facebook groups that don't have a website yet.

## Your info (fill this in once)
- Name:
- Email:
- Phone (optional):
- Preview domain (e.g. previews.yourname.com):

Use this in `pitch.md` sign-offs and anywhere a "from" identity is needed.

## Folder structure
```
businesses/
  <slug>/
    info.txt        - business details (extended schema; root info.txt = template)
    images/         - logo + real photos (from Google Maps / Facebook; may be empty)
    site/           - generated website (index.html, styles.css, etc.)
    preview.png     - screenshot of the site (if a headless browser is available)
    pitch.md        - drafted email + DM
skills/
  site-builder/      - how to design and build the site + extract-colors.py
  impeccable/        - primary aesthetic guide, avoids generic AI output
  high-end-visual-design/ - agency-tier layout and motion (premium/upscale businesses)
  minimalist-ui/     - editorial clean style (professional services, consultants)
  industrial-brutalist-ui/ - mechanical/Swiss grid style (trades, auto, industrial)
  full-output-enforcement/ - prevents truncated code output — always active
  ui-ux-pro-max/     - color palettes and font pairings (reference only)
  canvas-design/     - generate visual assets when images/ is empty
  copywriting/       - write compelling site copy
  cro/               - optimize CTAs and page flow for conversion
  marketing-psychology/ - persuasion principles for copy and pitch
  schema/            - structured data markup for SEO readiness
  seo-audit/         - SEO check before delivering the site
  cold-email/        - write the cold outreach email in pitch.md
  social/            - write the Facebook DM in pitch.md
  copy-editing/      - polish and tighten pitch.md copy
  prospecting/       - find businesses without websites
scraper/           - automated lead scraper (Google Maps -> ranked CRM)
  pipeline/        - Python package: maps, scoring, CRM, photos, etc.
  promote.py       - turn a chosen CRM lead into a businesses/<slug>/ folder
  crm_cli.py       - JSON bridge so non-Python tools can read/write the CRM
  run.py           - entry point: python scraper/run.py
  states/          - target cities (nj.csv, ny.csv, …)
supabase/
  schema.sql       - THE tracker's schema: cold_pitch.leads table + lead-photos bucket
leads/             - local data outputs (raw scrape snapshot + downloaded photos)
  photos/          - real photos downloaded per lead (<crm-slug>/), also uploaded to Storage
intake/            - localhost web form to add a business by hand -> CRM
crmInterface/      - Next.js dashboard: view leads, change status, build/delete folders
  src/app/admin/   - dashboard pages (/admin, /admin/b/[slug], /admin/login)
  src/app/api/*    - API route handlers (Supabase-backed)
  src/lib/crm.server.ts   - server data layer (queries Supabase cold_pitch.leads)
  src/lib/supabase.server.ts - service-role client; middleware.ts gates /admin + /api
  src/             - React + Tailwind + shadcn/ui frontend
  .next/           - build output (npm run build inside crmInterface/)
```

## Core philosophy
- **Static only.** Every generated site is plain HTML/CSS/(minimal vanilla
  JS). No servers, databases, or custom backends.
- **Embed, don't build.** If a business would benefit from bookings, online
  ordering, or a contact form, that's a third-party embed (see
  `skills/site-builder/SKILL.md`), never something you build from scratch.
  Don't add an embed to the mockup unless `info.txt` says they already use
  that service - otherwise just note it as a suggestion in `pitch.md`.
- **Real info, placeholder content.** Use the real name, address, phone,
  email, and type from `info.txt` as-is. Any testimonial, review, or
  anecdote not sourced from `info.txt` must be clearly invented and labeled
  as a sample (e.g. "Sample review - replace with a real one"). Exception:
  a "Customer reviews (GENUINE ...)" section in `info.txt` holds real reviews
  the scraper pulled from Google Maps - those may be used as actual
  testimonials, verbatim, and must NOT be labeled samples.
- **Use real photos when they help.** If `images/` has a usable logo or
  photos, use them. If it's empty or the photos are low quality, design with
  typography/color/CSS instead of falling back to generic stock imagery.
- **One page is the default.** A single scrolling page (hero, about,
  services, contact, footer) is enough. Don't build multi-page sites unless
  `info.txt` specifically calls for it.

## Naming and URLs
- Each business folder is named with a slug derived from the business name,
  e.g. `janes-bakery`. `promote.py` and the intake form generate this
  automatically and record it in the CRM's `Site Slug` column. A numeric
  suffix is added only to dodge a collision — another business with the same
  slug, or a reserved app route (`admin`, `api`, `photos`, `_next`) — giving
  e.g. `janes-bakery-2`. If you ever create a folder by hand, generate the
  slug once and set `Site Slug` in the CRM. Never change it afterward - it
  becomes part of the live URL. (Older folders may still carry a random
  4-char suffix like `-7f2k` from before this change; leave them as-is.)
- Every `site/index.html` must include
  `<meta name="robots" content="noindex, nofollow">` in `<head>`.
- Never create a page that links to or lists other businesses' folders.

## Design skills
When making visual design decisions, consult these in order:
- `skills/impeccable/SKILL.md` — **primary guide**. Read this first and
  commit to a bold, specific aesthetic direction before writing any code.
  This is what makes each site look genuinely designed, not templated.
- `skills/full-output-enforcement/SKILL.md` — **always active**. Read before
  generating any HTML/CSS to prevent truncated or placeholder-filled output.
- **Pick one style variant** based on the business type. Read its SKILL.md
  for specific typography, color, layout, and motion rules:
  - `skills/high-end-visual-design/SKILL.md` — premium/upscale businesses
    (real estate, salons, restaurants, spas, boutiques). Agency-tier.
  - `skills/minimalist-ui/SKILL.md` — professional services, consultants,
    accountants, lawyers. Editorial/clean.
  - `skills/industrial-brutalist-ui/SKILL.md` — trades, auto repair,
    manufacturing, construction. Raw/mechanical.
  - If none of the three fit, skip them and rely on impeccable alone.
- `skills/ui-ux-pro-max/SKILL.md` — use it only to pick a color palette and
  font pairing that fits the business type. 161 options — don't invent from
  scratch. Ignore everything else in that skill.

## Workflow for a new business
1. Read `info.txt` and look through `images/`.
2. Read `skills/impeccable/SKILL.md` and `skills/full-output-enforcement/SKILL.md`.
   Commit to a specific aesthetic direction for this business. Pick a style
   variant (high-end-visual-design / minimalist-ui / industrial-brutalist-ui)
   based on business type and read its SKILL.md. Then consult
   `skills/ui-ux-pro-max/SKILL.md` for palette and font pairing only.
3. Build the site — follow `skills/site-builder/SKILL.md` for structure and
   technical requirements, and apply these skills as you write:
   - `skills/copywriting/SKILL.md` — for all site copy: taglines, about
     sections, service descriptions, CTAs. Don't write generic filler.
   - `skills/marketing-psychology/SKILL.md` — apply persuasion principles to
     copy and page structure (social proof placement, framing, anchoring).
   - `skills/cro/SKILL.md` — optimize CTAs, visual hierarchy, and page flow
     so the site is built to convert from the start.
   - `skills/canvas-design/SKILL.md` — if `images/` is empty or unusable,
     generate a hero visual or background asset instead of leaving it bare.
4. Add structured data and run an SEO check:
   - `skills/schema/SKILL.md` — add LocalBusiness JSON-LD schema to every
     site so it's rich-result ready the moment the business goes live.
   - `skills/seo-audit/SKILL.md` — verify meta tags, heading hierarchy,
     image alt text, and page speed basics are solid.
5. Write `pitch.md` using:
   - `skills/cold-email/SKILL.md` — for the outreach email: subject line,
     opening hook, body, and CTA.
   - `skills/social/SKILL.md` — for the Facebook DM: shorter, more casual,
     same core pitch.
   - `skills/marketing-psychology/SKILL.md` — frame both around what the
     business owner actually cares about (more customers, look legitimate).
   - `skills/copy-editing/SKILL.md` — final pass to tighten both messages.
6. If a headless browser is available, capture `preview.png` (~1200x800).
   If not, skip.
7. The lead is already in the CRM at `Building` (from promote/intake). Leave
   it there; a human advances it after review.
8. Stop. Don't deploy automatically - deployment and the CRM status change to
   `Sent` happen after a human review.

## Where leads come from
Every lead lives in the CRM (Supabase `cold_pitch.leads`) before any site is
built. Three ways one gets there:

1. **Scraper (primary).** `python scraper/run.py` crawls Google Maps,
   finds businesses with no/outdated website, ranks them by likelihood to
   buy, downloads their real photos + reviews, and writes them to the CRM
   with status `New`. See `scraper/README.md` for config and tuning.
2. **Intake form.** `cd intake && node server.js`, open http://localhost:3000,
   and add a business by hand. It creates the `businesses/<slug>/` folder
   and registers the lead in the CRM (status `Building`).
3. **Prospecting skill.** Use `skills/prospecting/SKILL.md` to find/qualify
   businesses manually, then add them via the intake form.

**Promote = scraper lead -> buildable folder.** A scraped lead is just a CRM
row until you promote it. Pick winners and run:
```
python scraper/promote.py --slug "<crm-slug>"        # one (from the CRM's Slug column)
python scraper/promote.py --min-score 80             # batch the top leads
```
Promotion creates `businesses/<slug>/` (extended `info.txt`, copied photos,
genuine reviews), writes `Site Slug` back to the CRM, and moves the lead to
`Building`. It's idempotent — re-running refreshes a folder, never duplicates.
Then build the site with the workflow below. (Intake-entered businesses are
already promoted — their folder exists, so skip straight to the build.)

## Deployment (manual for now)
The CRM dashboard and every business site ship together as **one Next.js app**
(`crmInterface/`), deployed to Vercel. The CRM lives under `/admin`; each
business site gets the clean root path `https://<your-domain>/<slug>/`.

At build time, `crmInterface/scripts/copy-sites.mjs` (a `prebuild` hook) stages
every built site from `businesses/<slug>/site/` (+ its `images/`) into
`crmInterface/public/<slug>/`, rewriting `../images/` → `images/`. `info.txt`
is never copied. `businesses/` stays the source of truth; `public/<slug>/` is a
gitignored build artifact. Then deploy the app:

```
cd crmInterface && vercel deploy        # Root Directory = crmInterface, with
                                        # "Include files outside the root
                                        # directory" enabled so the build can
                                        # read ../businesses
```

The `/api` routes are now serverless-ready (Supabase, no Python/filesystem), so
Vercel go-live is unblocked. Set the env vars on the Vercel project
(`NEXT_PUBLIC_SUPABASE_URL`, `NEXT_PUBLIC_SUPABASE_ANON_KEY`,
`SUPABASE_SERVICE_ROLE_KEY`). The `/admin` dashboard sits behind a Supabase Auth
login (create users in the Supabase dashboard); business sites at `/<slug>/` stay
public. The Build button (promote) is local-only — it shells to `promote.py`.
After deploying, fill in the `Preview URL` column in the CRM for that business.

## The CRM (Supabase `cold_pitch.leads`)
The single source of truth for where every lead stands — a Postgres table in
Supabase (schema `cold_pitch`). It replaces the old `leads/crm.xlsx`. All access
uses the **service-role key** server-side (the scraper, `crm_cli.py`, `promote.py`,
and the Next.js `/api` routes); RLS is on with no public policies. Schema +
Storage bucket live in `supabase/schema.sql`. Lead photos are uploaded to the
public `lead-photos` Storage bucket and their URLs stored on each row.

- **Status pipeline:** `New` -> `Contacted` -> `Building` -> `Sent` ->
  `Won` / `Lost`. (`New` = scraped, not yet promoted; `Building` = has a
  buildable folder; `Sent` = pitch sent.)
- **You own** the `Status`, `Notes`, `Contacted On`, `Site Slug`, and
  `Preview URL` columns — a re-scrape never overwrites them (`save_crm` upserts
  scraper-owned columns only).
- **The scraper owns** everything else (score, contact, photos, hours,
  services, reviews count, ...) and refreshes it on each run.
- Edit it in the `/admin` dashboard, or programmatically via `scraper/crm_cli.py`
  (`add` / `list` / `set`) — the intake form uses that same bridge.
- Credentials: `SUPABASE_URL` + `SUPABASE_SERVICE_ROLE_KEY` (project-root `.env`
  for Python; `crmInterface/.env.local` for the app, plus the anon key for auth).

## Maintaining the scraper
`scraper/` is a standalone Python/Playwright project (its own `README.md` and
tests). When asked to change scraping behavior, tune `scraper/pipeline/config.py`
(search terms, score weights, targets) or the modules in `scraper/pipeline/`.
Run `python scraper/tests/test_logic.py` (offline) after logic changes. The CRM
schema lives in `scraper/pipeline/db.py` (`COLUMNS`) + `supabase/schema.sql`; keep
the `info.txt` field set in sync across `intake/server.js` (`buildInfoTxt`) and
`scraper/promote.py` (`_info_txt`).
