# Sites Platform — Implementation Plan

Turning frozen per-business static HTML into **editable, handoffable sites** served
from one shared Next.js app, with a clean per-business eject on purchase.

This plan supersedes the original "each site is its own Next.js app" draft. Read
alongside `CLAUDE.md`, `supabase/schema.sql`, `scraper/promote.py`,
`scraper/pipeline/db.py`, and `crmInterface/`.

---

## 1. Goal

A prospect's preview site should be:
1. **Editable** by the owner (hours, phone, about, services, hero photo) without a redeploy.
2. **Owner-loginable** via passwordless magic link.
3. **Handoffable** — on purchase, transfer that one site (project + domain) to the customer and walk away, while still letting them edit it.

The CRM dashboard (`crmInterface/`) and the scraper are unchanged.

---

## 2. Decisions locked (from discussion)

| Decision | Choice | Why |
|---|---|---|
| Where sites live | **One shared `sites/` Next.js app** (separate from `crmInterface/`) | All previews under one domain, one deploy; clean eject (no CRM code tangled in). |
| Domain | **Subdomains**: `app.<domain>` = CRM, `previews.<domain>/<slug>` = sites | Zero code glue (multi-zones is the fallback if one bare domain is required later). |
| Post-sale backend | **Keep our Supabase** as the backend for sold sites (paid tier, no auto-pause) | Owner keeps editing after handoff; ~$25/mo << profit. |
| Eject trigger | **On purchase only**, one site at a time | Previews stay cheap in the shared app; per-project cost only when paid. |
| Key exposure | Public/ejected sites use **anon key + RLS only**; service-role never ships to Vercel | Vercel Claim transfers env vars to the customer — service role would hand them every lead. |

---

## 3. Architecture overview

```
site-builder/
  crmInterface/                 # private dashboard — UNCHANGED. app.<domain>
  sites/                        # NEW shared app — all business sites. previews.<domain>
    app/
      [slug]/
        page.tsx                # public site: load design, feed it the DB row, ISR 60s
        admin/
          page.tsx              # owner magic-link login + edit form (per slug)
      auth/callback/route.ts    # Supabase OTP callback
      layout.tsx, globals.css
    designs/
      <slug>/
        Site.tsx                # bespoke design Claude writes (look only)
        styles.css
        index.ts                # default export = the design component
    lib/
      supabase.client.ts        # anon, browser
      supabase.server.ts        # anon + cookies (@supabase/ssr) for SSR/actions
      content.ts                # types + read helpers for business_content
    components/Shell.tsx        # shared wrapper (skip-link, footer "Owner login" link)
    next.config.ts, package.json, tailwind.config.ts
  templates/
    business-site/              # standalone starter — used ONLY by eject (one slug)
  scripts/
    eject.mjs                   # build + deploy + claim-URL for one sold site
  businesses/<slug>/            # info.txt, images/, pitch.md — UNCHANGED
                                # (site/ HTML retired; design now in sites/designs/<slug>/)
```

**Request flow (preview):**
```
GET previews.<domain>/poochie-doo
  → sites/app/[slug]/page.tsx (slug = "poochie-doo")
  → read public_business_content WHERE slug = 'poochie-doo'   (content)
  → import designs/poochie-doo                                 (look)
  → render <Design content={row} />, cached via ISR revalidate:60
```

The route is **one file** reused for every business; `designs/<slug>/` holds only
the unique look and reads all content from the row (nothing hardcoded, or owner
edits won't show).

---

## 4. Data model

### 4.1 New table `cold_pitch.business_content`

Separate from `leads` (leads is scraper-churned and fully private; content is
owner-edited and publicly readable — different lifecycle, different access).

```sql
create table if not exists cold_pitch.business_content (
  slug               text primary key,         -- == leads.site_slug == businesses/<slug>
  site_status        text not null default 'preview',  -- 'preview' | 'active'
  business_name      text not null default '',
  business_type      text not null default '',
  phone              text not null default '',
  email              text not null default '',
  address            text not null default '',
  hours              jsonb not null default '{}'::jsonb,   -- UNIFORM fixed keys, see §4.6
  holidays_note      text not null default '',             -- one general holidays line
  about              text not null default '',
  services           jsonb not null default '[]'::jsonb,   -- [{name,description,price}]
  photo_hero_url     text not null default '',
  photo_gallery_urls jsonb not null default '[]'::jsonb,
  facebook_url       text not null default '',
  instagram_url      text not null default '',
  maps_url           text not null default '',
  rating             text not null default '',
  review_count       integer not null default 0,
  reviews            jsonb not null default '[]'::jsonb,    -- genuine reviews [{text,name,stars}]
  owner_email        text not null default '',             -- only email allowed to edit
  created_at         timestamptz not null default now(),
  updated_at         timestamptz not null default now(),
  claimed_at         timestamptz
);

create trigger business_content_touch_updated_at
  before update on cold_pitch.business_content
  for each row execute function cold_pitch.touch_updated_at();  -- reuse existing fn
```

### 4.2 Owner-editable columns (the only ones the admin panel may write)

`hours, holidays_note, phone, about, services, photo_hero_url,
photo_gallery_urls, facebook_url, instagram_url`. Everything else (slug,
site_status, owner_email, business_name, …) is set by us/the scraper and is
read-only to the owner.

### 4.6 Hours — one uniform shape for every site

Hours are **standardized**, not freeform per business. `hours` jsonb always has
the same seven keys in the same order; every site renders them and every admin
panel edits them identically:

```json
{ "mon": "Closed", "tue": "11 AM–5 PM", "wed": "9 AM–5 PM", "thu": "9 AM–5 PM",
  "fri": "9 AM–6 PM", "sat": "9 AM–5 PM", "sun": "Closed" }
```

Each value is a plain time range or the literal `"Closed"`. Holidays are **not**
crammed per-day — `holidays_note` is one general line shown under the table, e.g.
`"Reduced hours on major holidays — call ahead."` The admin form is then always
the same: 7 fixed weekday rows + 1 holidays line.

`promote.py` parses the scraped freeform `leads.Hours` string into this 7-key map
(missing/unparseable days default to `"Closed"`) and seeds a default
`holidays_note`. `intake/server.js` emits the same shape.

### 4.3 Public read without leaking `owner_email`

RLS is row-level, not column-level, so expose a **view** that omits `owner_email`
and grant only the view to `anon`:

```sql
create or replace view cold_pitch.public_business_content
  with (security_invoker = false) as
select slug, site_status, business_name, business_type, phone, email, address,
       hours, about, services, photo_hero_url, photo_gallery_urls,
       facebook_url, instagram_url, maps_url, rating, review_count, reviews
from cold_pitch.business_content;

grant usage on schema cold_pitch to anon, authenticated;
grant select on cold_pitch.public_business_content to anon, authenticated;
```

The `[slug]/page.tsx` reads this view with the **anon** key.

### 4.4 RLS — writes

Table RLS stays **on**. Two narrow policies (plus existing service-role bypass):

```sql
alter table cold_pitch.business_content enable row level security;

-- Owner may UPDATE only their own row. Column restriction enforced by GRANT below.
create policy owner_update on cold_pitch.business_content
  for update to authenticated
  using  (auth.jwt() ->> 'email' = owner_email)
  with check (auth.jwt() ->> 'email' = owner_email);

-- Column-level: authenticated can write ONLY the editable columns.
grant update (hours, phone, about, services, photo_hero_url,
              photo_gallery_urls, facebook_url, instagram_url)
  on cold_pitch.business_content to authenticated;
```

Result: a logged-in owner edits their own row's safe columns with the **anon
key**; they cannot touch `slug`, `site_status`, `owner_email`, or anyone else's
row. Service role (promote.py, CRM) bypasses RLS as today.

### 4.5 Storage — owner hero/gallery uploads

Public bucket `business-photos` (display photos are public anyway). A customer-owned
ejected app holds only the anon key, so the privileged write goes through a
**Postgres RPC / Supabase Edge Function** `security definer` that validates
`auth.email() == owner_email` and returns a signed upload URL — never the service
key. (Seed photos come from the existing `lead-photos` bucket URLs.)

---

## 5. Build order

### Step 1 — Schema migration
- Add §4 to `supabase/schema.sql` (table, view, policies, grants, bucket). Re-runnable.
- Apply in the Supabase SQL editor.
- Add a `business_content` accessor to `scraper/pipeline/db.py`:
  - `_t_content()` → `cold_pitch.business_content`
  - `upsert_content(record: dict)` — service-role upsert keyed on `slug`, writing
    only provided non-empty values (mirror the existing `upsert()` semantics so a
    re-promote never clobbers owner edits — i.e. **don't** overwrite editable
    columns if the row already exists and is `active`; only seed missing/preview rows).

### Step 2 — `sites/` shared app scaffold
- `npx create-next-app` (App Router, TS, Tailwind) to match CRM stack (Next 15, React 19).
- `lib/supabase.client.ts` (anon, browser), `lib/supabase.server.ts` (`@supabase/ssr`, cookies).
- `lib/content.ts`: `BusinessContent` type + `getContent(slug)` (reads the view, anon).
- `app/[slug]/page.tsx`:
  - `export const revalidate = 60`
  - `generateStaticParams()` from the view (optional; ISR covers new slugs on demand)
  - read content; if none → `notFound()`
  - dynamic-import `designs/<slug>`; render `<Design content={row} />`
  - `<meta name="robots" content="noindex,nofollow">` while `site_status='preview'`; allow indexing when `active`.
- `components/Shell.tsx`: shared chrome + a discreet footer "Owner login" link → `/<slug>/admin`.

### Step 3 — Design adapter for existing HTML sites
- Define the contract every `designs/<slug>/Site.tsx` honors: a single
  `content: BusinessContent` prop; no hardcoded business data.
- Port Poochie Doo (our first real one) from `businesses/poochie-doo-pet-grooming/site/`
  into `sites/designs/poochie-doo-pet-grooming/` as the reference: same visuals,
  but phone/hours/about/services/photos read from `content`.
- Update `skills/site-builder/SKILL.md` + `CLAUDE.md` workflow: design output now
  targets `sites/designs/<slug>/Site.tsx` (+ `styles.css`), content-driven. The
  design *skills* (impeccable, variants, measure-images, etc.) are unchanged.

### Step 4 — Owner admin (`/<slug>/admin`)
- `app/[slug]/admin/page.tsx`:
  - Not authed → email input + "Send login link" → `supabase.auth.signInWithOtp({ email })`.
    Pre-check email == owner_email via a server action for UX (RLS is the real gate).
  - `app/auth/callback/route.ts` exchanges the OTP code for a session cookie.
  - Authed → edit form: hours (per day), phone, about, services (add/remove rows),
    hero photo upload (→ Edge Function/RPC signed URL → `business-photos`).
  - Save → `update` editable columns (anon key + RLS), then on-demand
    `revalidatePath('/'+slug)` so the change shows immediately (not just within 60s).
- Tailwind for the admin UI only; public site styling stays Claude-written per business.

### Step 5 — promote.py: seed content + scaffold design folder
At the end of `promote_one`, after writing `info.txt`/photos:
1. `db.upsert_content({...})` from the CRM row — name, type, phone, email, address,
   `hours` (parse the `Hours` string → jsonb map), `about`, `services` (seed list),
   socials, maps, rating, review_count, genuine `reviews`, `photo_hero_url` +
   `photo_gallery_urls` from `leads.photo_urls`. Leave `owner_email` blank (set at onboarding).
2. Create empty `sites/designs/<slug>/` (placeholder `index.ts` + README) for Claude to fill.
3. Keep writing `Site Slug` back to `leads` as today; `business_content.slug` == that slug.
- Keep the field set in sync across `intake/server.js` (`buildInfoTxt`), `promote.py`
  (`_info_txt`), and the new `business_content` seed (per CLAUDE.md's sync rule).

### Step 6 — Eject (on purchase) — `scripts/eject.mjs`
Manual trigger: `node scripts/eject.mjs <slug>`. It:
1. Copies `templates/business-site/` → a build dir, drops in `sites/designs/<slug>/`
   + shared `lib/`+`components/`, and pins `SLUG=<slug>` in its config (reads only that row).
2. The standalone uses **anon key only** (safe to transfer).
3. `vercel deploy --prod` → new Vercel project; capture its URL.
4. Manual SQL: `update business_content set site_status='active', claimed_at=now() where slug=...`
   (flips noindex → indexable on next render).
5. Vercel API → generate a **Claim Deployments** URL.
6. Write the project URL into `leads.preview_url` (CRM "Preview URL" column).
- You send the claim URL to the customer; they create a free Vercel account and the
  project + domain transfer to them. They keep editing via `/<slug>/admin` (our Supabase).

### Step 7 — Docs + reconcile philosophy
- Rewrite the `CLAUDE.md` **Core philosophy** + **Deployment** sections: the per-business
  deliverable is no longer "static only / one combined app." New truth: content-driven
  Next.js design in `sites/designs/<slug>/`, shared preview app, eject on sale. Keep the
  *design process* and skills wording intact. ("Embed, don't build" still holds for
  bookings/ordering; the only "backend" is Supabase + auth, deliberately.)
- Note that `crmInterface/scripts/copy-sites.mjs` and `public/<slug>/` static staging
  are retired for new sites (the combined-app `/<slug>/` path is replaced by the
  `sites/` app). Decide whether to keep them for any legacy static folders or remove.
- Update root `README.md` to describe `sites/`, `templates/business-site/`, `eject.mjs`.

---

## 6. Open items / risks

1. **CLAUDE.md contradiction** (Step 7) — "Static only. No servers, databases, or
   custom backends" becomes false. Must be rewritten before/with this work, or the
   project's stated identity and the code diverge.
2. **Magic-link to any email** — OTP will create a user for any address. RLS blocks
   non-owner writes, so worst case is a useless session; the pre-check is UX only.
   Confirm that's acceptable vs. an allowlist.
3. **Photo upload from a customer-owned app** needs the Edge Function/RPC path
   (§4.5) so the service key never leaves us — the main piece of new complexity.
4. **Per-day hours editing** needs a normalized `hours` jsonb; today it's a freeform
   string in `leads.Hours`. promote.py must parse it (and `intake` should emit the map).
5. **Eject env on transfer** — verify the standalone carries only `NEXT_PUBLIC_SUPABASE_URL`
   + anon key in its Vercel env, nothing else, before generating the claim URL.
6. **Cold starts** — none meaningful on Vercel (ISR is CDN-cached). Real risk is
   Supabase free-tier auto-pause; paid tier removes it (already decided).
7. **`generateStaticParams` vs pure ISR** — pure on-demand ISR avoids rebuilding the
   whole app when a new business is promoted; prefer it.

---

## 7. One-line summary

One `sites/` Next.js app serves every preview from `business_content` (anon key +
RLS, ISR 60s), each look isolated in `designs/<slug>/`; owners edit via magic-link
`/<slug>/admin`; on sale, `eject.mjs` lifts one site into its own Vercel project and
Claim-transfers it to the customer — backend stays our paid Supabase.
