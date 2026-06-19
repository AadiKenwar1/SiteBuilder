"""
Supabase-backed CRM data layer (replaces the openpyxl crm.py storage).

The single source of truth is the `cold_pitch.leads` table in Supabase. This
module exposes the same operations the rest of the project already used
(load_rows / get / set_field / upsert / delete / save_crm), keyed and shaped the
same way, so callers (crm_cli.py, promote.py, runner.py, the intake form) barely
change. Rows are returned as {Header Name: value} dicts — the legacy Excel header
shape — so downstream string-keyed access keeps working unchanged.

All access uses the SERVICE-ROLE key (server-side / local only). The table has
RLS enabled with no public policies; the service role bypasses it. See
supabase/schema.sql for the table + bucket definition.
"""
import os
from pathlib import Path

from supabase import create_client, Client

from .models import Lead
from .utils import lead_slug

SCHEMA = os.environ.get("SUPABASE_SCHEMA", "cold_pitch")
BUCKET = "lead-photos"

# (Header name, db column, Lead attribute or None).  attr is set only for
# scraper-owned columns (refreshed every run); None = human/bridge-owned.
# Mirrors CRM_COLS in the old crm.py, minus the Excel-only display columns
# ("Photos", "Preview"). Order is documentation-only here.
COLUMNS = [
    ("Status",         "status",            None),
    ("Score",          "score",             "score"),
    ("Business Name",  "business_name",     "business_name"),
    ("Business Type",  "business_type",     "business_type"),
    ("Area",           "area",              "area"),
    ("Phone",          "phone",             "phone"),
    ("Email",          "email",             "email"),
    ("Address",        "address",           "address"),
    ("Rating",         "rating",            "rating"),
    ("Reviews",        "review_count",      "review_count"),
    ("Lead Reason",    "lead_reason",       "lead_reason"),
    ("Site Slug",      "site_slug",         None),
    ("Preview URL",    "preview_url",       None),
    ("Facebook URL",   "facebook_url",      "facebook_url"),
    ("Instagram URL",  "instagram_url",     "instagram_url"),
    ("Maps URL",       "maps_url",          "maps_url"),
    ("Website",        "website_url",       "website_url"),
    ("Hours",          "hours",             "hours"),
    ("Services",       "services",          "services"),
    ("About",          "about",             "about"),
    ("Year",           "year_established",  "year_established"),
    ("Price",          "price_range",       "price_range"),
    ("Notes",          "notes",             None),
    ("Contacted On",   "contacted_on",      None),
    ("Slug",           "slug",              None),
    ("Photos Path",    "photos_path",       None),
]

HEADER_TO_DB = {h: c for h, c, _ in COLUMNS}
DB_TO_HEADER = {c: h for h, c, _ in COLUMNS}
_INT_COLS = {"score", "review_count"}
_IMG_EXT = {".jpg", ".jpeg", ".png", ".webp", ".avif", ".gif"}
_MIME = {
    ".jpg": "image/jpeg", ".jpeg": "image/jpeg", ".png": "image/png",
    ".webp": "image/webp", ".avif": "image/avif", ".gif": "image/gif",
}

# ── Client (lazy; reads env, falling back to a project-root .env) ──────────────
_client: Client | None = None


def _load_dotenv() -> None:
    """Best-effort: populate SUPABASE_* from a project-root .env if not already
    in the environment (keeps local runs simple without extra deps)."""
    if os.environ.get("SUPABASE_URL"):
        return
    env = Path(__file__).resolve().parents[2] / ".env"
    if not env.exists():
        return
    for line in env.read_text(encoding="utf-8").splitlines():
        line = line.strip()
        if not line or line.startswith("#") or "=" not in line:
            continue
        k, v = line.split("=", 1)
        os.environ.setdefault(k.strip(), v.strip().strip('"').strip("'"))


def _db() -> Client:
    global _client
    if _client is None:
        _load_dotenv()
        url = os.environ.get("SUPABASE_URL")
        key = os.environ.get("SUPABASE_SERVICE_ROLE_KEY")
        if not url or not key:
            raise RuntimeError(
                "SUPABASE_URL and SUPABASE_SERVICE_ROLE_KEY must be set "
                "(env or project-root .env) to reach the CRM."
            )
        _client = create_client(url, key)
    return _client


def _t():
    """The leads table, scoped to the cold_pitch schema."""
    return _db().schema(SCHEMA).table("leads")


def _cast_for_db(col: str, value):
    if col in _INT_COLS:
        try:
            return int(value)
        except (TypeError, ValueError):
            return 0
    return "" if value is None else str(value)


def _row_to_header(row: dict) -> dict:
    """A db row -> {Header Name: str} dict (the legacy Excel row shape)."""
    out = {h: ("" if row.get(c) is None else str(row.get(c, ""))) for h, c, _ in COLUMNS}
    out["Photo URLs"] = row.get("photo_urls") or []
    return out


# ── Reads ─────────────────────────────────────────────────────────────────────
def load_rows() -> dict:
    """slug -> {Header: value} for every lead, or {} if the table is empty."""
    res = _t().select("*").execute()
    return {r["slug"]: _row_to_header(r) for r in (res.data or [])}


def get(slug: str) -> dict | None:
    res = _t().select("*").eq("slug", slug).limit(1).execute()
    return _row_to_header(res.data[0]) if res.data else None


# ── Writes ────────────────────────────────────────────────────────────────────
def set_field(slug: str, field: str, value) -> bool:
    """Set a single column (by Header name) on one row. False if slug not found."""
    col = HEADER_TO_DB.get(field)
    if not col:
        return False
    res = _t().update({col: _cast_for_db(col, value)}).eq("slug", slug).execute()
    return bool(res.data)


def upsert(record: dict) -> str:
    """Insert/update ONE business by merge key (Slug). Provided non-empty values
    win; columns left out are untouched on conflict (so human columns survive),
    and new rows get DB defaults (status='New'). Returns the slug."""
    slug = (record.get("Slug") or "").strip() or lead_slug(
        str(record.get("Business Name", "")), str(record.get("Address", ""))
    )
    payload = {"slug": slug}
    for header, value in record.items():
        col = HEADER_TO_DB.get(header)
        if col and col != "slug" and value not in (None, ""):
            payload[col] = _cast_for_db(col, value)
    _t().upsert(payload, on_conflict="slug").execute()
    return slug


def delete(slug: str) -> dict | None:
    """Delete a row; return its {Header: value} dict (for folder cleanup) or None."""
    res = _t().delete().eq("slug", slug).execute()
    return _row_to_header(res.data[0]) if res.data else None


def _scraper_payload(lead: Lead) -> dict:
    """The columns one scrape refreshes for a lead — SCRAPER-owned only, plus the
    merge key (slug) and photos_path. Human columns are deliberately absent, so an
    upsert preserves them on conflict and new rows fall to the DB defaults
    (status='New')."""
    slug = lead.slug or lead_slug(lead.business_name, lead.address)
    row = {"slug": slug}
    for _, col, attr in COLUMNS:
        if attr:  # scraper-owned only
            row[col] = _cast_for_db(col, getattr(lead, attr, "") or "")
    row["photos_path"] = lead.photo_dir or ""
    return row


def save_crm(leads: list) -> None:
    """Merge this run's keepers in: upsert SCRAPER-owned columns only, keyed on
    slug. Untouched columns (Status/Notes/Contacted On/Site Slug/Preview URL) are
    preserved on conflict; new rows default to Status 'New'. Also uploads each
    lead's photos to Storage and records the public URLs."""
    payloads = []
    for lead in leads:
        row = _scraper_payload(lead)
        urls = upload_lead_photos(row["slug"], lead.photo_dir)
        if urls:
            row["photo_urls"] = urls
        payloads.append(row)

    if payloads:
        _t().upsert(payloads, on_conflict="slug").execute()
    print(f"  CRM   -> Supabase  ({len(payloads)} leads from this run)")


# ── Storage (lead photos for the CRM gallery) ─────────────────────────────────
def upload_lead_photos(slug: str, folder: str) -> list[str]:
    """Upload every image in folder to lead-photos/<slug>/ and return the public
    URLs (hero first). No-op if the folder is missing. Local files stay on disk
    so promote.py can still copy them into a built site's images/."""
    if not folder:
        return []
    p = Path(folder)
    if not p.is_dir():
        return []

    bucket = _db().storage.from_(BUCKET)
    urls: list[str] = []
    for f in sorted(p.iterdir()):
        if not f.is_file() or f.suffix.lower() not in _IMG_EXT:
            continue
        key = f"{slug}/{f.name}"
        try:
            bucket.upload(
                key,
                f.read_bytes(),
                {"content-type": _MIME.get(f.suffix.lower(), "image/jpeg"), "upsert": "true"},
            )
        except Exception as e:
            print(f"      storage upload warning ({f.name}): {e}")
        urls.append(bucket.get_public_url(key))

    urls.sort(key=lambda u: (0 if "/hero" in u else 1, u))
    return urls
