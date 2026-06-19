from datetime import datetime
from pathlib import Path
import os

# ── Directory layout ──────────────────────────────────────────────────────────
# pipeline/ lives inside scraper/; project root is two levels up.
_PIPELINE_DIR  = Path(__file__).resolve().parent   # site-builder/scraper/pipeline/
_SCRAPER_DIR   = _PIPELINE_DIR.parent              # site-builder/scraper/
_PROJECT_ROOT  = _SCRAPER_DIR.parent               # site-builder/
_LEADS_DATA    = _PROJECT_ROOT / "leads"           # site-builder/leads/  (CRM + photos)

# ── Run settings ──────────────────────────────────────────────────────────────
HEADLESS           = True   # False → watch browser / solve CAPTCHAs manually
TARGET_LEADS       = 50      # Keepers (top-N) enriched + pushed to the CRM
SCREEN_TARGET      = 100     # Candidates screened & scored before ranking (>= TARGET_LEADS)
OUTDATED_YEARS     = 10     # Website older than this = outdated
MAX_REVIEWS        = 200    # Skip businesses with more reviews (chains)
MAX_PER_SEARCH     = 5      # Listings to inspect per category per city (including rejects)
MAX_REVIEWS_SCRAPE = 10     # Max reviews to scrape per business
MAX_PHOTOS         = 8      # Real photos to download per kept lead

# ── Output files (absolute paths so the script works from any cwd) ────────────
OUTPUT_DIR         = str(_LEADS_DATA)
OUTPUT_XLSX        = str(_LEADS_DATA / "leads_no_website.xlsx")
OUTPUT_CSV         = str(_LEADS_DATA / "leads_no_website.csv")
OUTPUT_REVIEWS_CSV = str(_LEADS_DATA / "reviews.csv")
OUTPUT_CRM         = str(_LEADS_DATA / "crm.xlsx")
STATES_DIR         = str(_SCRAPER_DIR / "states")

# ── Misc ──────────────────────────────────────────────────────────────────────
CURRENT_YEAR  = datetime.now().year
NOMINATIM_UA  = "LeadScraper/6.0 contact@example.com"

# ── Google Maps search terms ──────────────────────────────────────────────────
CATEGORY_SEARCHES = [
    "hair salon", "barbershop", "nail salon", "auto repair", "mechanic",
    "plumber", "electrician", "hvac contractor", "roofer", "landscaping",
    "house cleaning", "painter", "handyman", "locksmith", "pest control",
    "dentist", "chiropractor", "veterinarian", "physical therapy",
    "accountant", "tax preparer", "notary", "insurance agent",
    "restaurant", "cafe", "bakery", "diner", "deli", "pizza place",
    "florist", "photographer", "pet grooming", "tailor", "shoe repair",
    "martial arts", "yoga studio", "tutoring center",
    "flooring contractor", "dry cleaner", "alterations", "jewelry store",
]

# ── Chain / big-business detection ───────────────────────────────────────────
BIG_BIZ_TEXT_SIGNALS = [
    r'chain (restaurant|store|of restaurants|of stores)',
    r'fast[- ]food chain',
    r'retail chain',
    r'locations (nationwide|across the (us|country|united states))',
    r'\d{3,}[\+]?\s+(locations|stores|restaurants|outlets)',
    r'publicly traded',
    r'\bnyse\s*:\s*[A-Z]',
    r'\bnasdaq\s*:\s*[A-Z]',
    r'\bfortune 500\b',
    r'\bs&p 500\b',
    r'multinational (corporation|company)',
]

SITE_CHAIN_SIGNALS = [
    'store locator', 'store-locator', 'find a location', 'find-a-location',
    'find a store', 'find-a-store', 'franchise opportunities',
    'become a franchisee', 'franchise inquiry',
]

# ── Email filtering ───────────────────────────────────────────────────────────
EMAIL_SKIP_DOMAINS = {
    "sentry.io", "example.com", "schema.org", "wix.com", "wordpress.com",
    "squarespace.com", "godaddy.com", "google.com", "facebook.com",
    "instagram.com", "twitter.com", "w3.org", "adobe.com", "cloudflare.com",
    "amazonaws.com", "jquery.com", "bootstrapcdn.com",
}
EMAIL_SKIP_PREFIXES = {
    "noreply", "no-reply", "donotreply", "webmaster", "postmaster",
    "abuse", "spam", "test", "privacy",
}

# ── Lead scoring (likelihood to buy a website) ────────────────────────────────
# Tune these freely — they are intentionally guesses with no ground truth yet.
# Max possible sum is capped to 100 in scoring.py.
SCORE_WEIGHTS = {
    "no_website":         30,   # strongest pain point
    "outdated_website":   15,   # weaker pain than none at all
    "has_email":          12,   # reachable by the channel we sell through
    "has_phone":           8,   # reachable, fallback channel
    "has_facebook":       10,   # owner already invests in being found
    "has_instagram":       8,
    "reviews_sweet_spot": 12,   # established but not a chain
    "good_rating":         8,   # a liked business is worth more
    "visual_business":    10,   # benefits most from a website
    "established":         5,   # has a track record
    "has_photos":          5,   # we gathered usable assets to build with
}

# Review count range that earns full "established but not a chain" points.
REVIEW_SWEET_SPOT = (5, 100)

# business_type substrings that mark a visually-driven business.
VISUAL_BUSINESS_TYPES = [
    "salon", "barber", "restaurant", "cafe", "bakery", "diner", "pizza",
    "florist", "photographer", "grooming", "studio", "jewelry", "tattoo",
    "spa", "gym", "landscaping", "interior", "bar", "deli", "caterer",
    "detailing", "boutique", "yoga", "martial",
]
