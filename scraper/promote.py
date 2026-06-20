"""
promote.py — bridge a scraped lead in the CRM into a buildable
businesses/<slug>/ folder the site-builder workflow can consume.

The scraper (run.py) discovers and ranks leads into leads/crm.xlsx but never
touches ../businesses. Promotion is the deliberate, human-in-the-loop step:
you pick winners from the CRM and turn each into a folder with info.txt,
images/, and an empty site/ — exactly the shape the site-builder skill expects.

What it does for each selected lead:
  • generates a clean site slug from the business name (a numeric suffix is
    added only to dodge a collision) — the live URL path, so it's written back
    to the CRM's "Site Slug" column and reused on every later promote
    (idempotent — re-promoting refreshes, never duplicates).
  • writes ../businesses/<slug>/info.txt from the CRM row (extended schema).
  • copies the real photos from leads/photos/<crm-slug>/ into images/.
  • appends any genuine Google reviews (from leads/reviews.csv) so the site
    can use them as REAL testimonials, clearly labelled as genuine.
  • flips the CRM Status New -> Building (never downgrades a later stage).

Usage
-----
  python promote.py --slug "joe-s-diner-123-main-st"      # one (CRM slug)
  python promote.py --slug a --slug b                      # several
  python promote.py --min-score 80                         # batch by score
  python promote.py --status New --min-score 70 --limit 10
  python promote.py --slug "..." --force                   # re-promote/refresh

Find a CRM slug in the hidden "Slug" column of leads/crm.xlsx (the scraper's
stable name+address key), or just use --min-score to let it pick the top leads.
"""
import argparse
import re
import shutil
import sys
from pathlib import Path

_SCRAPER_DIR = Path(__file__).resolve().parent
sys.path.insert(0, str(_SCRAPER_DIR))

from pipeline.db import load_rows, set_field, upsert_content   # noqa: E402
from pipeline.config import (                           # noqa: E402
    OUTPUT_REVIEWS_CSV, OUTPUT_DIR,
    _PROJECT_ROOT,
)
from pipeline.utils import normalize_name, parse_hours, parse_services  # noqa: E402

PROJECT_ROOT   = _PROJECT_ROOT
BUSINESSES     = PROJECT_ROOT / "businesses"
REVIEWS_PATH   = Path(OUTPUT_REVIEWS_CSV)
PHOTOS_ROOT    = Path(OUTPUT_DIR) / "photos"
SITES_DESIGNS  = PROJECT_ROOT / "sites" / "designs"
SITES_REGISTRY = PROJECT_ROOT / "sites" / "lib" / "designs.ts"


# Slugs that would collide with the CRM app's own routes (see crmInterface).
RESERVED_SLUGS = {"admin", "api", "photos", "_next"}


def _slugify(name: str) -> str:
    cleaned = re.sub(r"[^a-z0-9\s-]", "", name.lower())
    return re.sub(r"[\s-]+", "-", cleaned).strip("-") or "biz"


def _taken_slugs(rows: dict, exclude: str | None = None) -> set[str]:
    """Every Site Slug already in use — other CRM rows plus existing
    businesses/ folders — so a new slug can dodge them."""
    taken = {p.name for p in BUSINESSES.iterdir() if p.is_dir()} if BUSINESSES.is_dir() else set()
    for key, r in rows.items():
        if key == exclude:
            continue
        s = (r.get("Site Slug") or "").strip()
        if s:
            taken.add(s)
    return taken


def site_slug(name: str, taken: set[str]) -> str:
    """Clean business-name slug — the live URL path. Generated once and written
    to the CRM's "Site Slug", then reused unchanged on every later promote.
    Adds a numeric suffix only to dodge a collision with an existing slug or a
    reserved app route. Matches intake/server.js."""
    base = _slugify(name)
    candidate = base
    n = 2
    while candidate in taken or candidate in RESERVED_SLUGS:
        candidate = f"{base}-{n}"
        n += 1
    return candidate


def _resolve_photos(rec: dict) -> Path | None:
    """Locate this lead's photo folder: the stored Photos Path first, else the
    deterministic leads/photos/<Slug> convention (recovers folders from CRMs
    saved before Photos Path existed). Paths may be relative to leads/."""
    candidates = []
    pp = (rec.get("Photos Path") or "").strip()
    if pp:
        candidates.append(Path(pp))
    slug = (rec.get("Slug") or "").strip()
    if slug:
        candidates.append(PHOTOS_ROOT / slug)
    for p in candidates:
        if not p.is_absolute():
            p = PHOTOS_ROOT.parent / p
        if p.is_dir() and any(p.iterdir()):
            return p
    return None


def _reviews_for(business_name: str) -> list[dict]:
    """Genuine reviews for this business from leads/reviews.csv (this run)."""
    if not REVIEWS_PATH.exists():
        return []
    import csv
    target = normalize_name(business_name)
    out = []
    with open(REVIEWS_PATH, newline="", encoding="utf-8") as f:
        for row in csv.DictReader(f):
            if normalize_name(row.get("Business Name", "")) == target:
                text = (row.get("Review Text") or "").strip()
                if text:
                    out.append(row)
    return out


def _info_txt(rec: dict, reviews: list[dict]) -> str:
    g = lambda k: str(rec.get(k, "") or "").strip()
    lines = [
        f"Business name: {g('Business Name')}",
        f"Address: {g('Address')}",
        f"Phone: {g('Phone')}",
        f"Email: {g('Email')}",
        f"Business type (e.g. bakery, plumbing, hair salon): {g('Business Type')}",
        f"Website (their current site, if any): {g('Website')}",
        f"Facebook: {g('Facebook URL')}",
        f"Instagram: {g('Instagram URL')}",
        f"Rating: {g('Rating')}",
        f"Review count: {g('Reviews')}",
        f"Year established: {g('Year')}",
        f"Price range: {g('Price')}",
        f"Hours: {g('Hours')}",
        f"Services: {g('Services')}",
        f"About: {g('About')}",
        f"Lead reason (why they need a site): {g('Lead Reason')}",
        "Notes (anything specific worth referencing on the site): "
        f"{g('Notes')}",
    ]

    if reviews:
        lines += [
            "",
            "Customer reviews (GENUINE — real reviews scraped from Google Maps.",
            "These are real, so they may be used as actual testimonials on the",
            "site. Do NOT label them as samples; only invented quotes get that):",
        ]
        for rv in reviews:
            who   = (rv.get("Reviewer") or "Google reviewer").strip()
            stars = (rv.get("Stars") or "").strip()
            date  = (rv.get("Date") or "").strip()
            text  = " ".join((rv.get("Review Text") or "").split())
            meta  = " — " + ", ".join(p for p in (who, f"{stars}★" if stars else "", date) if p)
            lines.append(f'- "{text}"{meta}')

    return "\n".join(lines) + "\n"


def _copy_photos(src: Path | None, images_dir: Path) -> int:
    if not src:
        return 0
    n = 0
    for f in sorted(src.iterdir()):
        if f.is_file():
            shutil.copy2(f, images_dir / f.name)
            n += 1
    return n


# ── Sites platform: seed editable content + scaffold the design ───────────────
def _content_reviews(reviews: list[dict]) -> list[dict]:
    """Genuine reviews -> business_content shape, keeping only positive (>=4★)
    ones — negative genuine reviews are real but not testimonials."""
    out = []
    for r in reviews:
        stars_raw = (r.get("Stars") or "").strip()
        try:
            stars = int(stars_raw[:1])
        except (ValueError, IndexError):
            stars = 0
        text = " ".join((r.get("Review Text") or "").split())
        if stars >= 4 and text:
            out.append({
                "text": text,
                "name": (r.get("Reviewer") or "").strip(),
                "stars": stars_raw,
                "date": (r.get("Date") or "").strip(),
            })
    return out


def _seed_content(rec: dict, slug: str, name: str, reviews: list[dict]) -> None:
    """Upsert the editable business_content row from the CRM lead (preview state).
    owner_email/site_status are left to onboarding/eject; a re-promote of a live
    site won't clobber owner edits (see db.upsert_content)."""
    g = lambda k: (rec.get(k) or "").strip()
    photo_urls = rec.get("Photo URLs") or []
    if not isinstance(photo_urls, list):
        photo_urls = []
    try:
        review_count = int(str(rec.get("Reviews") or "0").strip() or 0)
    except ValueError:
        review_count = 0

    content = {
        "slug": slug,
        "business_name": name,
        "business_type": g("Business Type"),
        "phone": g("Phone"),
        "email": g("Email"),
        "address": g("Address"),
        "maps_url": g("Maps URL"),
        "rating": g("Rating"),
        "review_count": review_count,
        "reviews": _content_reviews(reviews),
        "hours": parse_hours(g("Hours")),
        "about": g("About"),
        "services": parse_services(g("Services")),
        # Scraped socials are NOT published — name-matching can't fully guarantee a
        # Facebook/Instagram page belongs to this business, so don't risk a wrong
        # link going live. They stay in the lead (info.txt + leads row) for image/
        # logo enrichment only; the owner adds their real socials via /<slug>/admin.
        "facebook_url": "",
        "instagram_url": "",
        "photo_hero_url": photo_urls[0] if photo_urls else "",
        "photo_gallery_urls": photo_urls[1:] if len(photo_urls) > 1 else [],
    }
    try:
        upsert_content(content)
    except Exception as e:                                    # noqa: BLE001
        print(f"      content seed warning: {e}")


_DESIGN_STARTER = '''// Starter design for {{NAME}}. Replace with a bespoke, content-driven design
// per skills/site-builder/SKILL.md. Until then it renders the reference design so
// the preview works. Read every value from `content` — never hardcode business data.
import Reference from "@/designs/_reference"
import type { BusinessContent } from "@/lib/content"

export default function Site({ content }: { content: BusinessContent }) {
  return <Reference content={content} />
}
'''


def _register_design(slug: str) -> None:
    """Add this slug to sites/lib/designs.ts so the [slug] route loads its folder.
    Idempotent; no-op if the registry or marker is missing."""
    if not SITES_REGISTRY.exists():
        return
    text = SITES_REGISTRY.read_text(encoding="utf-8")
    if f'"{slug}":' in text:
        return
    marker = "  // <promote.py inserts"
    if marker not in text:
        return
    line = f'  "{slug}": () => import("@/designs/{slug}"),\n'
    SITES_REGISTRY.write_text(text.replace(marker, line + marker, 1), encoding="utf-8")


def _scaffold_design(slug: str, name: str) -> None:
    """Create sites/designs/<slug>/ with a working starter and register it. Skips
    cleanly when the sites/ app isn't present (legacy/static mode) and never
    clobbers a bespoke Site.tsx that's already been written."""
    if not SITES_DESIGNS.is_dir():
        return
    d = SITES_DESIGNS / slug
    if (d / "Site.tsx").exists():
        _register_design(slug)
        return
    d.mkdir(parents=True, exist_ok=True)
    (d / "Site.tsx").write_text(_DESIGN_STARTER.replace("{{NAME}}", name), encoding="utf-8")
    (d / "index.ts").write_text('export { default } from "./Site"\n', encoding="utf-8")
    _register_design(slug)


def promote_one(rec: dict, rows: dict, force: bool) -> str:
    name = (rec.get("Business Name") or "").strip()
    slug = (rec.get("Site Slug") or "").strip()
    fresh = not slug
    if fresh:
        slug = site_slug(name, _taken_slugs(rows, exclude=rec.get("Slug")))

    biz_dir   = BUSINESSES / slug
    images    = biz_dir / "images"
    images.mkdir(parents=True, exist_ok=True)
    # No legacy site/ folder — the design lives in sites/designs/<slug>/ now.

    reviews = _reviews_for(name)
    (biz_dir / "info.txt").write_text(_info_txt(rec, reviews), encoding="utf-8")
    nphotos = _copy_photos(_resolve_photos(rec), images)

    # Sites platform: seed the editable content row + scaffold the design folder.
    _seed_content(rec, slug, name, reviews)
    _scaffold_design(slug, name)

    # Write the slug back into the CRM. The folder now exists ("promoted"); the
    # dashboard shows that as a badge. Status stays the user's manual sales
    # stage (New until they mark it Built/Emailed/…), so we don't touch it.
    rec["Site Slug"] = slug
    rows[rec["Slug"]] = rec       # keep the in-memory map current for batch runs
    if fresh:
        set_field(rec["Slug"], "Site Slug", slug)

    verb = "promoted" if fresh else ("re-promoted" if force else "refreshed")
    print(f"  {verb}: {name}  ->  businesses/{slug}  "
          f"({nphotos} photos, {len(reviews)} reviews)")
    return slug


def _select(rows: dict, args) -> list[dict]:
    by_slug = {r.get("Slug"): r for r in rows.values()}
    if args.slug:
        picked = []
        for s in args.slug:
            if s in by_slug:
                picked.append(by_slug[s])
            else:
                print(f"  !! no CRM row with Slug '{s}' — skipped")
        return picked

    statuses = {s.strip() for s in args.status.split(",")} if args.status else None

    def score(r):
        try:
            return float(r.get("Score") or 0)
        except (TypeError, ValueError):
            return 0.0

    cands = [
        r for r in rows.values()
        if score(r) >= args.min_score
        and (statuses is None or (r.get("Status") or "").strip() in statuses)
        and (args.force or not (r.get("Site Slug") or "").strip())
    ]
    cands.sort(key=score, reverse=True)
    return cands[: args.limit] if args.limit else cands


def main() -> None:
    ap = argparse.ArgumentParser(description="Promote CRM leads into businesses/ folders.")
    ap.add_argument("--slug", action="append", help="CRM slug to promote (repeatable)")
    ap.add_argument("--min-score", type=float, default=0, help="batch: minimum score")
    ap.add_argument("--status", default="New", help="batch: comma-sep statuses (default New)")
    ap.add_argument("--limit", type=int, default=0, help="batch: cap how many to promote")
    ap.add_argument("--force", action="store_true",
                    help="re-promote rows already promoted / refresh their files")
    args = ap.parse_args()

    rows = load_rows()
    if not rows:
        sys.exit("CRM is empty. Run the scraper first (python run.py).")
    selected = _select(rows, args)
    if not selected:
        print("Nothing to promote (check --slug / --min-score / --status).")
        return

    BUSINESSES.mkdir(exist_ok=True)
    print(f"Promoting {len(selected)} lead(s) into {BUSINESSES} ...")
    for rec in selected:
        promote_one(rec, rows, args.force)

    print("CRM updated -> Supabase")


if __name__ == "__main__":
    main()
