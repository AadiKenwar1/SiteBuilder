# Cold-Pitch Site Generator

## What this project does
For each small business in `businesses/`, design a clean one-page website and a
short cold-outreach pitch (email + Facebook DM), to send to businesses that don't
have a website yet. Each site is **content-driven and editable**: the design is
bespoke per business, but the words and photos come from a Supabase row the owner
can later edit themselves. Sites are previewed under one shared domain and, when a
business buys, handed off to them as their own deployment.

> **Migration status (read this).** The project is moving from frozen static
> `businesses/<slug>/site/index.html` to a shared **`sites/` Next.js app** that
> renders each business from the `cold_pitch.business_content` table. The full
> plan and build order live in `SITES-PLATFORM-PLAN.md`. This file already
> describes the **target** architecture. Until the `sites/` app and the
> `business_content` table actually exist, fall back to the legacy static build
> (`businesses/<slug>/site/` + `crmInterface` static staging) — check whether
> `sites/` is present before assuming the new path. Don't build a business into
> `sites/designs/<slug>/` until step 2 of the plan has landed.

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
    info.txt        - raw scrape dump Claude READS to design (prose; not rendered)
    images/         - logo + real photos (from Google Maps / Facebook; may be empty)
    content.json    - OPTIONAL: structured content Claude WRITES to fix/enrich the
                      business_content row when the auto-seed is thin/wrong; pushed
                      via scraper/content_cli.py. Skip it when the scrape is clean.
    pitch.md        - drafted email + DM
    preview.png     - screenshot of the site (if a headless browser is available)
    (no site/ folder - the bespoke design lives in sites/designs/<slug>/ now)
sites/             - shared Next.js app: every business site, one domain (previews.<domain>)
  app/[slug]/      - one route reused for all sites: reads business_content, renders the design
  app/[slug]/admin/- owner magic-link login + edit form (per business)
  designs/<slug>/  - the bespoke per-business design Claude writes (Site.tsx + styles.css)
  lib/             - Supabase clients (anon) + content read helpers
  components/      - shared shell/chrome
templates/
  business-site/   - standalone starter copied on eject (one business -> its own Vercel project)
scripts/
  eject.mjs        - build + deploy + Claim-URL a sold site into its own Vercel project
skills/
  site-builder/      - how to design and build the site + extract-colors.py + measure-images.py
  impeccable/        - primary aesthetic guide, avoids generic AI output
  high-end-visual-design/ - agency-tier layout and motion (premium/upscale businesses)
  minimalist-ui/     - editorial clean style (professional services, consultants)
  industrial-brutalist-ui/ - mechanical/Swiss grid style (trades, auto, industrial)
  full-output-enforcement/ - prevents truncated code output — always active
  ui-ux-pro-max/     - color palettes and font pairings (reference only)
  emil-design-eng/   - micro-interaction craft (easing, springs, press feedback) for designs
  review-animations/ - motion QA gate run before delivery (manual; not auto-invoked)
  canvas-design/     - generate visual assets when images/ is empty
  image/             - AI image generation/editing (Higgsfield) when photos are weak (optional)
  copywriting/       - write compelling site copy
  cro/               - optimize CTAs and page flow for conversion
  marketing-psychology/ - persuasion principles for copy and pitch
  schema/            - structured data markup for SEO readiness
  seo-audit/         - SEO check before delivering the site
  ai-seo/            - make the page citable by AI search (ChatGPT/Perplexity/AI Overviews)
  cold-email/        - write the cold outreach email in pitch.md
  social/            - write the Facebook DM in pitch.md
  copy-editing/      - polish and tighten pitch.md copy
  prospecting/       - find businesses without websites
scraper/           - automated lead scraper (Google Maps -> ranked CRM)
  pipeline/        - Python package: maps, scoring, CRM, photos, etc.
  promote.py       - turn a chosen CRM lead into a businesses/<slug>/ folder + seed business_content
  crm_cli.py       - JSON bridge so non-Python tools can read/write the CRM (leads)
  content_cli.py   - JSON bridge to author business_content (the editable site row) from content.json
  run.py           - entry point: python scraper/run.py
  states/          - target cities (nj.csv, ny.csv, …)
supabase/
  schema.sql       - cold_pitch schema: leads + business_content tables, views, RLS, Storage buckets
leads/             - local data outputs (raw scrape snapshot + downloaded photos)
  photos/          - real photos downloaded per lead (<crm-slug>/), also uploaded to Storage
intake/            - localhost web form to add a business by hand -> CRM
crmInterface/      - Next.js dashboard: view leads, change status, build/delete folders
  src/app/admin/   - dashboard pages (/admin, /admin/b/[slug], /admin/login)
  src/app/api/*    - API route handlers (Supabase-backed)
  src/lib/crm.server.ts   - server data layer (queries Supabase cold_pitch.leads)
  src/lib/supabase.server.ts - service-role client; middleware.ts gates /admin + /api
  src/             - React + Tailwind + shadcn/ui frontend
```

The CRM dashboard (`crmInterface/`) and the public sites (`sites/`) are **separate
apps on the same root domain** (e.g. `app.<domain>` and `previews.<domain>`), so a
single site can later be ejected cleanly without dragging dashboard code with it.

## Core philosophy
- **One bespoke design per business, content from data.** Each site looks like it
  was designed only for that business (see the design skills). But it never
  hardcodes the business's details — name, phone, hours, about, services, and
  photos are read from the `cold_pitch.business_content` row so the owner can edit
  them later. The look lives in code (`sites/designs/<slug>/`); the words and
  photos live in the database.
- **Self-contained designs.** A design in `sites/designs/<slug>/` imports only its
  own files plus the shared `lib/` and `components/`. No cross-imports between
  businesses — on eject, one folder is lifted out intact.
- **Thin backend, anon key only on the public site.** The only "backend" is
  Supabase (data + magic-link auth + Storage). The public/ejected site uses the
  **anon key + RLS** exclusively — never the service-role key, which would transfer
  to the customer on a Vercel Claim handoff and expose every lead. Privileged
  writes (photo upload) go through a `security definer` RPC/Edge Function that
  checks `auth.email() == owner_email`.
- **Embed, don't build.** If a business would benefit from bookings, online
  ordering, or a contact form, that's a third-party embed (see
  `skills/site-builder/SKILL.md`), not something built from scratch. Don't add an
  embed to the site unless `info.txt` says they already use that service —
  otherwise note it as a suggestion in `pitch.md`.
- **Real info, placeholder content.** Use the real name, address, phone, email, and
  type from `info.txt` as-is. Any testimonial, review, or anecdote not sourced from
  `info.txt` must be clearly invented and labeled as a sample (e.g. "Sample review
  - replace with a real one"). Exception: a "Customer reviews (GENUINE ...)"
  section in `info.txt` holds real reviews the scraper pulled from Google Maps —
  those may be used as actual testimonials, verbatim, and must NOT be labeled
  samples.
- **Use real photos when they help.** If `images/` has a usable logo or photos, use
  them. If it's empty or low quality, design with typography/color/CSS instead of
  generic stock imagery.
- **One page is the default.** A single scrolling page (hero, about, services,
  contact, footer) is enough. Don't build multi-page sites unless `info.txt`
  specifically calls for it.

## Naming and URLs
- Each business folder is named with a slug derived from the business name, e.g.
  `janes-bakery`. `promote.py` and the intake form generate this automatically and
  record it in the CRM's `Site Slug` column; it is also the primary key of the
  `business_content` row and the live URL path (`previews.<domain>/<slug>`). A
  numeric suffix is added only to dodge a collision — another business with the same
  slug, or a reserved app route (`admin`, `api`, `photos`, `_next`) — giving e.g.
  `janes-bakery-2`. If you ever create a folder by hand, generate the slug once and
  set `Site Slug` in the CRM. Never change it afterward — it's the live URL. (Older
  folders may still carry a random 4-char suffix like `-7f2k`; leave them as-is.)
- The public site route must render `<meta name="robots" content="noindex,
  nofollow">` while `site_status = 'preview'`, and allow indexing once
  `site_status = 'active'` (the business has bought and been handed off — it's their
  real site now).
- Never create a page that links to or lists other businesses' sites.

## Design skills
When making visual design decisions, consult these in order:
- `skills/impeccable/SKILL.md` — **primary guide and final authority**. Read this
  first. Its rules override the style variant skills below when they conflict — in
  particular: impeccable's font ban list always wins. Skip the
  `node .claude/skills/impeccable/scripts/context.mjs` step — the script path
  assumes global install; read `PRODUCT.md` directly instead (it's at the project
  root). Let the business type, photos, and real content drive every color and
  style decision — do not force a distinctive or bold direction for its own sake.
- `skills/full-output-enforcement/SKILL.md` — **always active**. Read before
  generating any code to prevent truncated or placeholder-filled output.
- **Pick one style variant** based on the business type. Read its SKILL.md for
  layout structure and motion rules — use its font/color suggestions only if they
  don't conflict with impeccable's ban lists:
  - `skills/high-end-visual-design/SKILL.md` — premium/upscale businesses (real
    estate, salons, restaurants, spas, boutiques). Agency-tier.
  - `skills/minimalist-ui/SKILL.md` — professional services, consultants,
    accountants, lawyers. Editorial/clean.
  - `skills/industrial-brutalist-ui/SKILL.md` — trades, auto repair, manufacturing,
    construction. Raw/mechanical.
  - If none of the three fit, skip them and rely on impeccable alone.
- `skills/ui-ux-pro-max/SKILL.md` — use it only to pick a color palette and font
  pairing that fits the business type (161 curated options, so you don't invent
  from scratch). Cross-check any font against impeccable's reflex-reject list
  before committing. Ignore everything else in this skill.
- `skills/emil-design-eng/SKILL.md` — micro-interaction craft: easing curves,
  durations, spring config, button press feedback (`scale(0.97)`), `@starting-style`,
  GPU-only properties, stagger. Read it as a reference (don't invoke cold — it has a
  canned "Initial Response" gate). Use it to make the motion in `sites/designs/<slug>/`
  feel intentional rather than generic. (The `motion` library is installed in
  `sites/`; the actual animation patterns and the intensity-tier-by-business-type
  rule live in `skills/site-builder/SKILL.md` under "Motion and animation".)
- `skills/review-animations/SKILL.md` — manual motion QA gate. Run it before
  delivery only if the design has any animation; it returns a Block/Approve verdict.

**Font availability note:** Only use fonts available on Google Fonts. Clash Display,
PP Editorial New, and other premium/paid fonts are not installed in `sites/` and
require self-hosting. Stick to Google Fonts or native system stacks.

The skills decide the **look**. The output target is a content-driven
`sites/designs/<slug>/Site.tsx` (+ `styles.css`), not a static HTML file — same
craft, but every business detail is read from the `content` prop, never typed in.

## Workflow for a new business
1. Read `info.txt` and look through `images/`. Run
   `python3 skills/site-builder/measure-images.py businesses/<slug>/images` so the
   layout is built around the real photo dimensions, not guessed ones.
2. Read `skills/impeccable/SKILL.md` and `skills/full-output-enforcement/SKILL.md`.
   Commit to a specific aesthetic direction for this business. Pick a style variant
   (high-end-visual-design / minimalist-ui / industrial-brutalist-ui) based on
   business type and read its SKILL.md. Then consult
   `skills/ui-ux-pro-max/SKILL.md` for palette and font pairing only.
3. Build the design into `sites/designs/<slug>/` — follow
   `skills/site-builder/SKILL.md` for structure and technical requirements. The
   component takes a single `content: BusinessContent` prop and reads every
   business detail (name, phone, hours, about, services, photos, socials, reviews)
   from it — nothing hardcoded, or owner edits won't show. Apply as you write:
   - `skills/copywriting/SKILL.md` — taglines, about, service descriptions, CTAs.
   - `skills/marketing-psychology/SKILL.md` — persuasion in copy and structure.
   - `skills/cro/SKILL.md` — optimize CTAs, hierarchy, and page flow to convert.
   - `skills/canvas-design/SKILL.md` — if `images/` is empty/unusable, generate a
     hero visual or background asset instead of leaving it bare.
   - `skills/image/SKILL.md` (optional, only if needed) — AI image generation/editing
     for a hero or brand asset when the real photos are missing or too weak, or to
     clean up an existing one (background removal, crop, recolor). Use the Higgsfield
     MCP tools (`generate_image`, `outpaint_image`, `remove_background`, `upscale_image`,
     `reframe`) as the generator. Stay within impeccable's rules — no generic stock
     look; prefer real photos when they exist, and label any AI-made imagery in the
     handoff so the owner can swap it. Skip entirely if the real photos are good.
   - `skills/site-builder/SKILL.md` ("Motion and animation") + `skills/emil-design-eng/SKILL.md`
     — when adding animation/interaction, follow site-builder's `motion` patterns
     and intensity-tier-by-business-type rule, and apply emil-design-eng's craft
     rules (easing, durations, press feedback, GPU-only).
   (Until the `sites/` app exists, build the legacy static `site/index.html` per
   `SITES-PLATFORM-PLAN.md`'s fallback — see the migration note at the top.)
3b. **Author the content row — don't hand-write SQL.** `promote.py` seeds
   `business_content` from the raw scrape, which is often thin or wrong (e.g. a
   `Services` field full of scraper metadata). While building you know the real
   menu/about/reviews from `info.txt` + photos, so write them to
   `businesses/<slug>/content.json` (snake_case `business_content` columns: about,
   services `[{name,description,price}]`, reviews, hours, etc. — only the fields
   you're correcting) and push it:
   ```
   python scraper/content_cli.py set <slug> --file businesses/<slug>/content.json
   ```
   It upserts via the same path as promote (never clobbers an owner's edits on a
   live row, never touches `owner_email`/`site_status`). Leave invented prices
   blank — the owner fills those in `/<slug>/admin`. This is the standard fix for a
   bad row; never write per-business SQL.
4. Add structured data, then run the pre-delivery quality gates:
   - `skills/schema/SKILL.md` — add LocalBusiness JSON-LD to every site.
   - `skills/seo-audit/SKILL.md` — verify meta tags, heading hierarchy, image alt
     text, and page speed basics.
   - `skills/ai-seo/SKILL.md` — make the page citable by AI search (ChatGPT,
     Perplexity, Google AI Overviews): clear question-style headings, concise factual
     answers (hours, services, area served, prices), and entity clarity (name +
     location stated plainly). Builds on schema + seo-audit — local prospects
     increasingly find businesses through AI answers, not just blue links.
   - `skills/review-animations/SKILL.md` — if the design has any motion, run this
     manual QA pass over it (it's not auto-invoked). It scores the animation code
     against a craft bar and returns a Block/Approve verdict; fix anything it blocks.
5. Write `pitch.md` using:
   - `skills/cold-email/SKILL.md` — outreach email: subject, hook, body, CTA.
   - `skills/social/SKILL.md` — Facebook DM: shorter, casual, same core pitch.
   - `skills/marketing-psychology/SKILL.md` — frame both around what the owner cares
     about (more customers, look legitimate).
   - `skills/copy-editing/SKILL.md` — final pass to tighten both messages.
6. If a headless browser is available, capture `preview.png` (~1200x800) by running
   the `sites/` app and screenshotting `/<slug>`. If not, skip.
7. The lead is already in the CRM at `Building` (from promote/intake) and its
   `business_content` row is seeded. Leave the status there; a human advances it
   after review.
8. Stop. Don't deploy or eject automatically — deployment, the CRM status change to
   `Sent`, and any handoff happen after a human review.

## Where leads come from
Every lead lives in the CRM (Supabase `cold_pitch.leads`) before any site is built.
Three ways one gets there:

1. **Scraper (primary).** `python scraper/run.py` crawls Google Maps, finds
   businesses with no/outdated website, ranks them by likelihood to buy, downloads
   their real photos + reviews, and writes them to the CRM with status `New`. See
   `scraper/README.md` for config and tuning.
2. **Intake form.** `cd intake && node server.js`, open http://localhost:3000, and
   add a business by hand. It creates the `businesses/<slug>/` folder and registers
   the lead in the CRM (status `Building`).
3. **Prospecting skill.** Use `skills/prospecting/SKILL.md` to find/qualify
   businesses manually, then add them via the intake form.

**Promote = scraper lead -> buildable folder + seeded content.** A scraped lead is
just a CRM row until you promote it. Pick winners and run:
```
python scraper/promote.py --slug "<crm-slug>"        # one (from the CRM's Slug column)
python scraper/promote.py --min-score 80             # batch the top leads
```
Promotion creates `businesses/<slug>/` (extended `info.txt`, copied photos, genuine
reviews), **upserts the `cold_pitch.business_content` row** (the editable content
the site renders), creates an empty `sites/designs/<slug>/` for the design, writes
`Site Slug` back to the CRM, and moves the lead to `Building`. It's idempotent —
re-running refreshes scraper-seeded fields but never clobbers an owner's edits on an
`active` row, and never duplicates. Then build the site with the workflow above.
(Intake-entered businesses are already promoted — skip straight to the build.)

## Deployment & handoff (manual)
**Previews — one shared app.** Every business site is served by the `sites/`
Next.js app, deployed once to Vercel as a single project on the previews subdomain.
Each site renders at `previews.<domain>/<slug>` via the `app/[slug]` route, reading
its `business_content` row with the anon key and **ISR (`revalidate: 60`)** so owner
edits appear within ~a minute. There is no per-business deploy and no static staging
step — `crmInterface/scripts/copy-sites.mjs` and `crmInterface/public/<slug>/` are
**retired** for new sites (kept only for any legacy static folders until migrated).

```
cd sites && vercel deploy        # one project; serves every business under /<slug>
```
Set on the project: `NEXT_PUBLIC_SUPABASE_URL` + `NEXT_PUBLIC_SUPABASE_ANON_KEY`
only. Never put the service-role key on the `sites/` project.

**Owner editing.** A discreet "Owner login" link in each site's footer goes to
`/<slug>/admin`: a passwordless Supabase magic-link login restricted (by RLS) to the
row's `owner_email`. The owner edits hours, phone, about, services, and the hero
photo; saves write the editable columns with the anon key and trigger an on-demand
revalidate so the change shows immediately. You set `owner_email` when you onboard a
business that has bought.

**Handoff on purchase (eject).** Run `node scripts/eject.mjs <slug>`. It scaffolds a
standalone app from `templates/business-site/` containing just that business's
design, deploys it as its own Vercel project (anon key only), flips
`business_content.site_status` to `active` (which drops the noindex), and generates a
Vercel **Claim Deployments** URL. Send that URL to the customer; they create a free
Vercel account and the project + domain transfer to them permanently. The site keeps
reading our Supabase, so the owner can still edit it. Record the project URL in the
CRM's `Preview URL` column.

## The CRM and content (Supabase `cold_pitch`)
Two tables in the `cold_pitch` schema, both defined in `supabase/schema.sql`:

- **`leads`** — the sales tracker, source of truth for where every lead stands.
  Service-role only (the scraper, `crm_cli.py`, `promote.py`, the CRM `/api`
  routes); RLS on with no public policies. Replaces the old `leads/crm.xlsx`.
  - **Status pipeline:** `New` -> `Contacted` -> `Building` -> `Sent` -> `Won` /
    `Lost`. (`New` = scraped, not yet promoted; `Building` = has a buildable folder;
    `Sent` = pitch sent.)
  - **You own** `Status`, `Notes`, `Contacted On`, `Site Slug`, `Preview URL` — a
    re-scrape never overwrites them (`save_crm` upserts scraper-owned columns only).
  - **The scraper owns** everything else (score, contact, photos, hours, services,
    reviews count, ...) and refreshes it each run.
  - Edit it in the `/admin` dashboard, or via `scraper/crm_cli.py` (`add` / `list` /
    `set`) — the intake form uses that same bridge.

- **`business_content`** — the editable content each site renders, keyed by `slug`
  (== `leads.site_slug`). Public-readable (via the `public_business_content` view,
  which hides `owner_email`) with the anon key; owner-writable on the editable
  columns only, gated by RLS (`auth.email() = owner_email`). Seeded by `promote.py`
  from the lead, then edited by the owner. A re-promote must not clobber an owner's
  edits on an `active` row. Hero/gallery photos live in a public Storage bucket.
  - **Hours are uniform across every site:** the `hours` jsonb always has the same
    seven keys (`mon`…`sun`), each a time range or `"Closed"`, plus a single
    `holidays_note` line shown under the table. Same shape, same editor, every
    business — `promote.py`/`intake` parse the scraped freeform hours into it. See
    `SITES-PLATFORM-PLAN.md` §4.6.

Credentials: `SUPABASE_URL` + `SUPABASE_SERVICE_ROLE_KEY` (project-root `.env` for
Python; `crmInterface/.env.local` for the dashboard). The `sites/` app gets only the
URL + anon key.

## Maintaining the scraper
`scraper/` is a standalone Python/Playwright project (its own `README.md` and
tests). When asked to change scraping behavior, tune `scraper/pipeline/config.py`
(search terms, score weights, targets) or the modules in `scraper/pipeline/`. Run
`python scraper/tests/test_logic.py` (offline) after logic changes. The CRM schema
lives in `scraper/pipeline/db.py` (`COLUMNS`) + `supabase/schema.sql`. Keep the
business field set in sync across **three** places now: `intake/server.js`
(`buildInfoTxt`), `scraper/promote.py` (`_info_txt` **and** the `business_content`
seed), and the `business_content` columns in `supabase/schema.sql` /
`scraper/pipeline/db.py`.
