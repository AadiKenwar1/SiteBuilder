-- Cold-Pitch CRM — Supabase schema (Phase 3)
-- Run this once in the Supabase SQL editor for a fresh project. Re-runnable.
--
-- Design notes:
--   • Everything lives in a dedicated `cold_pitch` schema so one Supabase
--     project can host multiple apps. After running this, add `cold_pitch` to
--     Settings → API → "Exposed schemas" so the API can reach it.
--   • The Next.js server and the local scraper both talk to this table with the
--     SERVICE-ROLE key (server-side only), which bypasses RLS. RLS is enabled
--     with no public policies, so the anon key can read/write nothing.
--   • Column names are snake_case; the app/scraper map them to/from the legacy
--     header names ("Business Name", "Site Slug", …) at the boundary.

create schema if not exists cold_pitch;

-- ── leads ────────────────────────────────────────────────────────────────────
create table if not exists cold_pitch.leads (
  -- merge key: stable lead_slug(business_name, address) from the scraper
  slug              text primary key,

  -- human-owned (never overwritten by a re-scrape)
  status            text not null default 'New',
  notes             text not null default '',
  contacted_on      text not null default '',
  site_slug         text not null default '',
  preview_url       text not null default '',

  -- scraper-owned (refreshed every run)
  score             integer not null default 0,
  business_name     text not null default '',
  business_type     text not null default '',
  area              text not null default '',
  phone             text not null default '',
  email             text not null default '',
  address           text not null default '',
  rating            text not null default '',
  review_count      integer not null default 0,
  lead_reason       text not null default '',
  facebook_url      text not null default '',
  instagram_url     text not null default '',
  maps_url          text not null default '',
  website_url       text not null default '',
  hours             text not null default '',
  services          text not null default '',
  about             text not null default '',
  year_established  text not null default '',
  price_range       text not null default '',

  -- bridge/system
  photos_path       text not null default '',          -- local photo folder (scraper machine)
  photo_urls        jsonb not null default '[]'::jsonb, -- public Storage URLs for the CRM gallery

  created_at        timestamptz not null default now(),
  updated_at        timestamptz not null default now()
);

create index if not exists leads_score_idx     on cold_pitch.leads (score desc);
create index if not exists leads_site_slug_idx on cold_pitch.leads (site_slug);

-- keep updated_at fresh
create or replace function cold_pitch.touch_updated_at()
returns trigger language plpgsql as $$
begin
  new.updated_at = now();
  return new;
end $$;

drop trigger if exists leads_touch_updated_at on cold_pitch.leads;
create trigger leads_touch_updated_at
  before update on cold_pitch.leads
  for each row execute function cold_pitch.touch_updated_at();

-- ── RLS: locked down. Only the service-role key (server-side) gets in. ────────
alter table cold_pitch.leads enable row level security;
-- (intentionally no policies → anon/authenticated are denied all access)

-- ── Grants. Data access is service-role only; anon/authenticated get nothing. ─
grant usage on schema cold_pitch to anon, authenticated, service_role;
grant all on all tables in schema cold_pitch to service_role;
grant all on all sequences in schema cold_pitch to service_role;
alter default privileges in schema cold_pitch grant all on tables to service_role;
alter default privileges in schema cold_pitch grant all on sequences to service_role;

-- ── Storage: public bucket for lead photos (CRM gallery). ─────────────────────
-- Public bucket → anyone with the URL can view (these are public business photos
-- from Google Maps). The scraper uploads with the service-role key.
insert into storage.buckets (id, name, public)
values ('lead-photos', 'lead-photos', true)
on conflict (id) do nothing;


-- ════════════════════════════════════════════════════════════════════════════
-- business_content — the editable content each PUBLIC site renders (Phase 4).
--
-- Separate from `leads` on purpose: `leads` is scraper-churned and service-role
-- only; `business_content` is owner-edited and publicly readable. It is seeded by
-- promote.py from the lead, then edited by the business owner through the sites/
-- app. The public site reads it with the ANON key only (never the service role,
-- which would transfer to a customer on a Vercel Claim handoff). See
-- SITES-PLATFORM-PLAN.md and CLAUDE.md.
-- ════════════════════════════════════════════════════════════════════════════
create table if not exists cold_pitch.business_content (
  slug               text primary key,                 -- == leads.site_slug == businesses/<slug>
  site_status        text not null default 'preview',  -- 'preview' | 'active'

  -- identity / contact (we + the scraper own these; not owner-editable)
  business_name      text not null default '',
  business_type      text not null default '',
  phone              text not null default '',
  email              text not null default '',
  address            text not null default '',
  maps_url           text not null default '',
  rating             text not null default '',
  review_count       integer not null default 0,
  reviews            jsonb not null default '[]'::jsonb,    -- genuine reviews [{text,name,stars,date}]

  -- owner-editable content
  hours              jsonb not null default '{}'::jsonb,    -- {mon..sun}: "9 AM–5 PM" | "Closed"
  holidays_note      text not null default '',              -- one general holidays line
  about              text not null default '',
  services           jsonb not null default '[]'::jsonb,    -- [{name,description,price}]
  photo_hero_url     text not null default '',
  photo_gallery_urls jsonb not null default '[]'::jsonb,
  facebook_url       text not null default '',
  instagram_url      text not null default '',

  -- handoff / auth
  owner_email        text not null default '',              -- ONLY email allowed to edit (set at onboarding)

  created_at         timestamptz not null default now(),
  updated_at         timestamptz not null default now(),
  claimed_at         timestamptz
);

drop trigger if exists business_content_touch_updated_at on cold_pitch.business_content;
create trigger business_content_touch_updated_at
  before update on cold_pitch.business_content
  for each row execute function cold_pitch.touch_updated_at();

-- ── Public read surface ───────────────────────────────────────────────────────
-- Every column EXCEPT owner_email. The sites/ app reads this view with the anon
-- key; owner_email never leaves the server. The view is owner-defined (not
-- security_invoker), so anon can read it even though the base table's RLS denies
-- direct anon access.
create or replace view cold_pitch.public_business_content as
select slug, site_status, business_name, business_type, phone, email, address,
       maps_url, rating, review_count, reviews, hours, holidays_note, about,
       services, photo_hero_url, photo_gallery_urls, facebook_url, instagram_url
from cold_pitch.business_content;

-- ── RLS: base table locked; owners reach it only through the functions below ──
alter table cold_pitch.business_content enable row level security;
-- (no anon/authenticated policies on the base table → no direct read/write;
--  reads go through the view, owner writes through update_business_content().)

-- ── Ownership helpers (security definer; can see the otherwise-hidden owner_email)
create or replace function cold_pitch.owns_slug(p_email text, p_slug text)
returns boolean
language sql security definer set search_path = cold_pitch as $$
  select exists (
    select 1 from cold_pitch.business_content
    where slug = p_slug and owner_email <> '' and owner_email = p_email
  );
$$;

-- Nice-UX check the login form calls before sending a magic link (RLS-equivalent
-- functions are the real gate). Returns true if this email owns this slug.
create or replace function cold_pitch.is_owner(p_slug text, p_email text)
returns boolean
language sql security definer set search_path = cold_pitch as $$
  select cold_pitch.owns_slug(p_email, p_slug);
$$;

-- ── The only owner write path: whitelisted patch, gated on the JWT email ──────
create or replace function cold_pitch.update_business_content(p_slug text, p_patch jsonb)
returns cold_pitch.public_business_content
language plpgsql security definer set search_path = cold_pitch as $$
declare
  v_email text := auth.jwt() ->> 'email';
  v_row   cold_pitch.public_business_content;
begin
  if not cold_pitch.owns_slug(v_email, p_slug) then
    raise exception 'not authorized to edit %', p_slug using errcode = '42501';
  end if;
  update cold_pitch.business_content c set
    hours              = coalesce(p_patch->'hours',              c.hours),
    holidays_note      = coalesce(p_patch->>'holidays_note',     c.holidays_note),
    phone              = coalesce(p_patch->>'phone',             c.phone),
    about              = coalesce(p_patch->>'about',             c.about),
    services           = coalesce(p_patch->'services',          c.services),
    photo_hero_url     = coalesce(p_patch->>'photo_hero_url',    c.photo_hero_url),
    photo_gallery_urls = coalesce(p_patch->'photo_gallery_urls', c.photo_gallery_urls),
    facebook_url       = coalesce(p_patch->>'facebook_url',      c.facebook_url),
    instagram_url      = coalesce(p_patch->>'instagram_url',     c.instagram_url)
  where c.slug = p_slug;
  select * into v_row from cold_pitch.public_business_content where slug = p_slug;
  return v_row;
end;
$$;

-- ── Grants ────────────────────────────────────────────────────────────────────
grant select on cold_pitch.public_business_content to anon, authenticated;
grant execute on function cold_pitch.is_owner(text, text)                to anon, authenticated;
grant execute on function cold_pitch.owns_slug(text, text)               to anon, authenticated;
grant execute on function cold_pitch.update_business_content(text, jsonb) to authenticated;
grant all on cold_pitch.business_content to service_role;  -- scraper/promote/CRM bypass RLS

-- ── Storage: public bucket for owner-uploaded hero/gallery photos ─────────────
insert into storage.buckets (id, name, public)
values ('business-photos', 'business-photos', true)
on conflict (id) do nothing;

-- Owners may upload/replace objects only under <their-slug>/ in business-photos.
drop policy if exists "business photos owner insert" on storage.objects;
create policy "business photos owner insert" on storage.objects
  for insert to authenticated
  with check (bucket_id = 'business-photos'
              and cold_pitch.owns_slug(auth.jwt() ->> 'email', split_part(name, '/', 1)));

drop policy if exists "business photos owner update" on storage.objects;
create policy "business photos owner update" on storage.objects
  for update to authenticated
  using (bucket_id = 'business-photos'
         and cold_pitch.owns_slug(auth.jwt() ->> 'email', split_part(name, '/', 1)));

drop policy if exists "business photos public read" on storage.objects;
create policy "business photos public read" on storage.objects
  for select to anon, authenticated
  using (bucket_id = 'business-photos');
