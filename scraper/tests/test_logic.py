"""
Tier 1 — offline, deterministic unit tests.

Covers the pure logic and parsing that does NOT need a real browser:
scoring, slug stability, the CRM merge (human edits must survive a re-run),
email cleaning, photo-URL helpers, and website-age parsing on fake responses.

Run standalone (no extra deps):   python tests/test_logic.py
Or with pytest if installed:       pytest tests/test_logic.py
"""
import asyncio
import os
import sys
import tempfile

# Make the project root importable whether run via `python tests/...` or pytest.
sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

from pipeline.models import Lead
from pipeline.scoring import score_lead
from pipeline.utils import lead_slug
from pipeline.db import _scraper_payload, HEADER_TO_DB
from pipeline.email_finder import clean_emails
from pipeline.photos import _hi_res, _photo_id
from pipeline.website_check import check_website_age
from pipeline.enrichment import scrape_facebook


# ── Test fixtures / helpers ───────────────────────────────────────────────────
class FakeResp:
    def __init__(self, text="", status_code=200, headers=None):
        self.text = text
        self.status_code = status_code
        self.headers = headers or {}
        self.content = text.encode()

    def json(self):
        import json
        return json.loads(self.text)


class FakeClient:
    """Minimal async stand-in for httpx.AsyncClient, matched by URL fragment."""
    def __init__(self, get=None, head=None):
        self._get = get or {}
        self._head = head or {}

    async def get(self, url, **kw):
        for frag, resp in self._get.items():
            if frag in url:
                return resp
        return FakeResp(status_code=404)

    async def head(self, url, **kw):
        for frag, resp in self._head.items():
            if frag in url:
                return resp
        return FakeResp(status_code=404)


def _strong_lead():
    l = Lead(business_name="Acme Barbers", business_type="Barber shop",
             address="1 Main St", lead_reason="No website",
             email="info@acmebarbers.com", phone="555-1212",
             facebook_url="fb", instagram_url="ig",
             review_count=40, rating="4.6", year_established="2008")
    l.slug = lead_slug(l.business_name, l.address)
    return l


def _weak_lead():
    l = Lead(business_name="Quiet Tax LLC", business_type="Accountant",
             address="2 Oak Ave", lead_reason="Outdated -- 2012",
             review_count=2, rating="3.1")
    l.slug = lead_slug(l.business_name, l.address)
    return l


# ── Slug ──────────────────────────────────────────────────────────────────────
def test_slug_is_stable_and_safe():
    a = lead_slug("Acme Barbers", "1 Main St, Newark")
    b = lead_slug("Acme Barbers", "1 Main St, Newark")
    assert a == b, "same input must yield same slug"
    assert all(c.isalnum() or c == "-" for c in a), "slug must be filesystem-safe"
    assert lead_slug("Acme", "1 Main St") != lead_slug("Acme", "9 Other Rd"), \
        "different address must disambiguate same-named businesses"
    assert lead_slug("", "") == "biz", "empty input falls back to a usable slug"


# ── Scoring ───────────────────────────────────────────────────────────────────
def test_scoring_ranks_and_bounds():
    strong, weak = score_lead(_strong_lead()), score_lead(_weak_lead())
    assert strong > weak, "stronger lead must outrank weaker one"
    assert 0 <= strong <= 100 and 0 <= weak <= 100, "score must stay within 0–100"


def test_no_website_beats_outdated():
    base = dict(business_name="X", address="1 St", business_type="cafe")
    no_site  = score_lead(Lead(lead_reason="No website", **base))
    outdated = score_lead(Lead(lead_reason="Outdated -- 2010", **base))
    assert no_site > outdated, "no website is a stronger buy signal than an outdated one"


def test_email_is_a_signal_not_a_gate():
    without = _strong_lead(); without.email = ""
    with_email = _strong_lead()
    assert score_lead(with_email) > score_lead(without), \
        "having an email should raise the score (signal), not be required"


# ── CRM merge (the critical behavior) ─────────────────────────────────────────
# The Supabase merge works by upserting ONLY scraper-owned columns keyed on slug,
# so a conflict updates just those and leaves human columns untouched, while new
# rows fall to the DB defaults. We assert that contract on the payload builder
# (no DB needed) — see scraper/pipeline/db.py::_scraper_payload.
_HUMAN_DB_COLS = {"status", "notes", "contacted_on", "site_slug", "preview_url"}


def test_crm_merge_writes_only_scraper_columns():
    payload = _scraper_payload(_strong_lead())
    # Human-owned columns must be ABSENT, so an upsert can never clobber them.
    assert _HUMAN_DB_COLS.isdisjoint(payload), "human columns must be preserved (absent from upsert)"
    # Every human column is still a real column in the schema map (sanity).
    assert _HUMAN_DB_COLS <= set(HEADER_TO_DB.values())
    # Scraper-owned columns ARE refreshed, keyed by the stable merge slug.
    strong = _strong_lead()
    assert payload["business_name"] == strong.business_name
    assert payload["score"] == strong.score
    assert payload["slug"], "merge key must be present"


def test_crm_new_lead_defaults_to_new():
    # save_crm never writes `status`, so a brand-new row falls to the DB default
    # ('New'); a re-scrape leaves an existing human-set status untouched.
    payload = _scraper_payload(_strong_lead())
    assert "status" not in payload


# ── Email cleaning ────────────────────────────────────────────────────────────
def test_clean_emails_filters_and_dedups():
    text = ("Reach us at INFO@AcmeBarbers.com or info@acmebarbers.com. "
            "noreply@acmebarbers.com webmaster@acmebarbers.com "
            "someone@wix.com tracking@google.com")
    out = clean_emails(text)
    assert "info@acmebarbers.com" in out, "valid email must be kept (and lowercased)"
    assert out.count("info@acmebarbers.com") == 1, "must dedup"
    assert "noreply@acmebarbers.com" not in out, "skip-prefix not filtered"
    assert "webmaster@acmebarbers.com" not in out, "skip-prefix not filtered"
    assert "someone@wix.com" not in out, "skip-domain not filtered"
    assert "tracking@google.com" not in out, "skip-domain not filtered"


# ── Photo URL helpers ─────────────────────────────────────────────────────────
def test_photo_helpers_normalize_and_dedup():
    small = "https://lh3.googleusercontent.com/p/ABC123=w408-h306-k-no"
    large = "https://lh3.googleusercontent.com/p/ABC123=w800-h600-k-no"
    assert _photo_id(small) == _photo_id(large), "same photo at two sizes must share an id"
    assert _hi_res(small) == "https://lh3.googleusercontent.com/p/ABC123=s1600", \
        "size suffix must be rewritten to high-res"


# ── Website-age parsing (offline, via FakeClient) ─────────────────────────────
async def test_website_age_copyright_footer():
    old = FakeClient(get={"oldsite": FakeResp(
        "<html><footer>© 2010 Acme Co. All rights reserved.</footer></html>")})
    outdated, reason = await check_website_age("http://oldsite.test", old)
    assert outdated and "2010" in reason, f"old © year should read as outdated ({reason})"

    new = FakeClient(get={"freshsite": FakeResp(
        "<html><footer>© 2024 Acme Co.</footer></html>")})
    outdated2, _ = await check_website_age("http://freshsite.test", new)
    assert not outdated2, "recent © year should not read as outdated"


async def test_website_age_last_modified_header():
    client = FakeClient(head={"site": FakeResp(
        headers={"Last-Modified": "Mon, 01 Jan 2015 00:00:00 GMT"})})
    outdated, reason = await check_website_age("http://site.test", client)
    assert outdated and "2015" in reason, f"old Last-Modified should read as outdated ({reason})"


# ── Facebook parsing (offline, via FakeClient) ────────────────────────────────
async def test_scrape_facebook_extracts_meta():
    html = ('<meta property="og:image" content="https://cdn.test/logo.jpg">'
            '<meta property="og:description" content="A friendly neighborhood barbershop since 2008">')
    data = await scrape_facebook("https://facebook.com/acme", FakeClient(get={"facebook.com": FakeResp(html)}))
    assert data["logo_url"] == "https://cdn.test/logo.jpg", "og:image not parsed"
    assert "barbershop" in data["about"].lower(), "og:description not parsed"


# ── Standalone runner (works without pytest) ──────────────────────────────────
if __name__ == "__main__":
    import inspect
    tests = sorted((n, f) for n, f in globals().items()
                   if n.startswith("test_") and callable(f))
    passed = failed = 0
    for name, fn in tests:
        try:
            result = fn()
            if inspect.iscoroutine(result):
                asyncio.run(result)
            print(f"PASS  {name}")
            passed += 1
        except Exception as e:
            import traceback
            print(f"FAIL  {name}  ->  {e}")
            traceback.print_exc()
            failed += 1
    print(f"\n{passed} passed, {failed} failed")
    sys.exit(1 if failed else 0)
