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
