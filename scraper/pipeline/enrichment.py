"""
Social media finding + Facebook / Instagram profile scraping.

find_social_media()  -- Googles for FB and IG pages
scrape_facebook()    -- Gets description, hours, services, logo from a FB page
scrape_instagram()   -- Gets bio and logo from an IG profile
enrich_from_social() -- Calls both and fills gaps in a Lead

Photo/logo downloading lives in photos.py (Phase 2, keepers only).
"""
import re
import html as html_lib

import httpx
from playwright.async_api import Page

from .models import Lead
from .utils import delay, _METADATA_TOKEN

# Minimum length of the shorter normalized name for a containment match to
# count. Below this, generic short names ("joes", "maria") would be a substring
# of unrelated businesses, so we demand a longer, more distinctive overlap.
_MIN_MATCH_LEN = 5

_SKIP_FB = {"search", "sharer", "l.facebook", "login", "help", "about", "groups", "watch"}
_SKIP_IG = {"/p/", "/reel/", "/explore", "/stories", "login", "help", "tags", "/tv/"}


# ══════════════════════════════════════════════════════════════════════════════
#  FINDING SOCIAL PAGES
# ══════════════════════════════════════════════════════════════════════════════
async def _fetch_og_title(url: str, http_client: httpx.AsyncClient) -> str:
    """Fetch a page and return its og:title value, or '' on any error."""
    try:
        r = await http_client.get(url, timeout=10, follow_redirects=True)
        m = re.search(
            r'<meta\s+(?:property|name)="og:title"\s+content="([^"]+)"', r.text
        ) or re.search(
            r'content="([^"]+)"\s+(?:property|name)="og:title"', r.text
        )
        if m:
            return html_lib.unescape(m.group(1))
    except Exception:
        pass
    return ""


def _normalize(s: str) -> str:
    """Lowercase and strip everything but letters/digits.

    "Joe's Pizzeria!" -> "joespizzeria", so spacing and punctuation differences
    between a Maps name and a social handle don't break the comparison.
    """
    return re.sub(r"[^a-z0-9]", "", s.lower())


def _handle_from_url(url: str) -> str:
    """The profile handle out of a FB/IG URL: instagram.com/joespizza/ -> 'joespizza'."""
    m = re.search(r"(?:facebook|instagram)\.com/@?([\w.]+)", url)
    return m.group(1) if m else ""


def _display_name_from_title(og_title: str) -> str:
    """The business name out of a social og:title, dropping the platform noise.

    "This is Yoga NJ (@thisisyoganj) • Instagram photos..." -> "This is Yoga NJ"
    """
    return re.split(r"\s*[(•·|]", og_title, maxsplit=1)[0].strip()


def _contains_match(business_name: str, candidate: str) -> bool:
    """True when one normalized name is a substring of the other.

    "joespizzeria" vs handle "joespizzeria1974" -> True (the shorter sits inside
    the longer). "njanimalchiro" vs "thisisyoganj" -> False. The shorter string
    must be at least _MIN_MATCH_LEN chars so a generic short name doesn't match
    an unrelated business.
    """
    a, b = _normalize(business_name), _normalize(candidate)
    if not a or not b:
        return False
    shorter, longer = (a, b) if len(a) <= len(b) else (b, a)
    if len(shorter) < _MIN_MATCH_LEN:
        return False
    return shorter in longer


async def _verify_match(
    url: str, business_name: str, http_client: httpx.AsyncClient
) -> bool:
    """True when a social page plausibly belongs to this business.

    Tries containment against the URL handle first (always present, no network),
    then against the page's og:title display name (catches handles that
    abbreviate the real name). Fails CLOSED — an unverifiable page is dropped,
    because attaching the wrong business is far worse than attaching none.
    """
    if _contains_match(business_name, _handle_from_url(url)):
        return True
    og_title = await _fetch_og_title(url, http_client)
    if og_title and _contains_match(business_name, _display_name_from_title(og_title)):
        return True
    return False


def _unwrap_google_url(href: str, domain: str) -> str:
    m = re.search(rf"url\?q=(https?://(?:www\.)?{re.escape(domain)}/[^&\s]+)", href)
    if m:
        return m.group(1)
    return href if (domain in href and href.startswith("http")) else ""


async def find_social_media(
    page: Page, name: str, area: str,
    http_client: httpx.AsyncClient | None = None,
    known_facebook: str = "", known_instagram: str = "",
) -> tuple[str, str]:
    """Returns (facebook_url, instagram_url) by Googling site: searches.

    A URL already supplied via known_facebook/known_instagram (e.g. the Maps
    "website" link was itself a social page) is trusted as-is and that platform
    is skipped — Google Maps already vouched the association.

    Each searched candidate is verified by name containment (see _verify_match)
    so a same-category business in the same area isn't accepted when the target
    has no social presence.
    """
    facebook  = known_facebook
    instagram = known_instagram

    for platform, domain, skip_set, pattern in [
        ("facebook",  "facebook.com",  _SKIP_FB, r'facebook\.com/(?!sharer|search|l\.|watch)[\w.]+/?$'),
        ("instagram", "instagram.com", _SKIP_IG, r'instagram\.com/@?[\w.]+/?$'),
    ]:
        if (platform == "facebook" and facebook) or (platform == "instagram" and instagram):
            continue  # already have a Maps-vouched URL for this platform
        try:
            q = f'"{name}" "{area}" site:{domain}'
            await page.goto(
                f"https://www.google.com/search?q={q.replace(' ', '+')}",
                wait_until="domcontentloaded", timeout=20_000,
            )
            await delay(1.5, 2.5)

            for link in await page.query_selector_all(f'a[href*="{domain}"]'):
                href = await link.get_attribute("href") or ""
                url  = _unwrap_google_url(href, domain)
                if not url or any(kw in url for kw in skip_set):
                    continue
                if not re.search(pattern, url):
                    continue

                # Verify the page actually belongs to this business.
                if http_client is not None and not await _verify_match(url, name, http_client):
                    continue  # wrong business — keep searching

                clean = url.split("?")[0]
                if platform == "facebook":
                    facebook = clean
                else:
                    instagram = clean
                break
        except Exception:
            pass

    return facebook, instagram


# ══════════════════════════════════════════════════════════════════════════════
#  FACEBOOK PROFILE SCRAPING
# ══════════════════════════════════════════════════════════════════════════════
async def scrape_facebook(facebook_url: str, http_client: httpx.AsyncClient) -> dict:
    result = {"about": "", "hours": "", "services": "", "logo_url": ""}
    if not facebook_url:
        return result

    for url in [facebook_url, facebook_url.rstrip("/") + "/about"]:
        try:
            r    = await http_client.get(url, timeout=12, follow_redirects=True)
            html = r.text

            # og:image -- profile photo
            if not result["logo_url"]:
                m = re.search(r'<meta\s+(?:property|name)="og:image"\s+content="([^"]+)"', html)
                if not m:
                    m = re.search(r'content="([^"]+)"\s+(?:property|name)="og:image"', html)
                if m:
                    result["logo_url"] = html_lib.unescape(m.group(1))

            # og:description -- business description
            if not result["about"]:
                m = re.search(r'<meta\s+(?:property|name)="og:description"\s+content="([^"]+)"', html)
                if not m:
                    m = re.search(r'content="([^"]+)"\s+(?:property|name)="og:description"', html)
                if m:
                    raw = html_lib.unescape(m.group(1))
                    cleaned = re.sub(r'^\d[\d,]*\s+(?:likes?|followers?).*?[|\xb7]\s*', '', raw).strip()
                    if cleaned and len(cleaned) > 20:
                        result["about"] = cleaned[:600]

            # Hours -- JSON Facebook embeds
            if not result["hours"]:
                hours_match = re.search(r'"hours":\s*\{([^}]+)\}', html)
                if hours_match:
                    hours_raw = hours_match.group(1)
                    days = {"mon": "Mon", "tue": "Tue", "wed": "Wed", "thu": "Thu",
                            "fri": "Fri", "sat": "Sat", "sun": "Sun"}
                    slots = {}
                    for day_key, day_label in days.items():
                        opens  = re.findall(rf'"{day_key}_\d_open":"([^"]+)"', hours_raw)
                        closes = re.findall(rf'"{day_key}_\d_close":"([^"]+)"', hours_raw)
                        if opens and closes:
                            slots[day_label] = f"{opens[0]}-{closes[0]}"
                    if slots:
                        result["hours"] = " | ".join(f"{d}: {t}" for d, t in slots.items())

            # Services -- "name" keys in page JSON
            if not result["services"]:
                svcs = re.findall(r'"name"\s*:\s*"([^"]{3,50})"', html)
                filtered = [s for s in svcs
                            if not _METADATA_TOKEN.match(s)   # drop snake_case metadata
                            and not any(kw in s.lower() for kw in
                                ["facebook", "instagram", "twitter", "home", "about",
                                 "photos", "reviews", "menu"])]
                if filtered:
                    result["services"] = ", ".join(dict.fromkeys(filtered[:8]))

        except Exception:
            pass

        if result["about"]:
            break

    return result


# ══════════════════════════════════════════════════════════════════════════════
#  INSTAGRAM PROFILE SCRAPING
# ══════════════════════════════════════════════════════════════════════════════
def _is_ig_placeholder(text: str) -> bool:
    """Instagram's logged-out og:description boilerplate, not a real bio."""
    return text.lower().startswith("see instagram photos and videos from")


async def scrape_instagram(instagram_url: str, http_client: httpx.AsyncClient) -> dict:
    result = {"about": "", "logo_url": ""}
    if not instagram_url:
        return result

    try:
        r    = await http_client.get(instagram_url, timeout=12, follow_redirects=True)
        html = r.text

        # og:image -- profile photo
        m = re.search(r'<meta\s+property="og:image"\s+content="([^"]+)"', html)
        if not m:
            m = re.search(r'content="([^"]+)"\s+property="og:image"', html)
        if m:
            result["logo_url"] = html_lib.unescape(m.group(1))

        # Biography from embedded JSON
        m = re.search(r'"biography"\s*:\s*"([^"]{5,})"', html)
        if m:
            bio = m.group(1).replace('\\n', ' ').replace('\\u0026', '&').strip()
            if bio:
                result["about"] = bio[:500]
                return result

        # Fallback: og:description
        m = re.search(r'<meta\s+property="og:description"\s+content="([^"]+)"', html)
        if not m:
            m = re.search(r'content="([^"]+)"\s+property="og:description"', html)
        if m:
            raw = html_lib.unescape(m.group(1))
            cleaned = re.sub(
                r'^\d[\d,K.]*\s+Followers?,\s*\d[\d,K.]*\s+Following,.*?[-]\s*',
                '', raw
            ).strip()
            # "See Instagram photos and videos from X (@x)" is Instagram's
            # logged-out placeholder, not a real bio — never store it as copy.
            if cleaned and len(cleaned) > 10 and not _is_ig_placeholder(cleaned):
                result["about"] = cleaned[:500]

    except Exception:
        pass

    return result


# ══════════════════════════════════════════════════════════════════════════════
#  ENRICHMENT ORCHESTRATOR
# ══════════════════════════════════════════════════════════════════════════════
async def enrich_from_social(lead: Lead, http_client: httpx.AsyncClient) -> None:
    """Fills gaps in lead fields by scraping Facebook and Instagram in-place.

    logo_verified is only True when find_social_media() already confirmed the
    page name-matched this business. photos.download_photos() uses that flag to
    decide whether the social logo is trustworthy enough to use as hero.jpg.
    """
    fb_data = await scrape_facebook(lead.facebook_url, http_client)
    ig_data = await scrape_instagram(lead.instagram_url, http_client)

    # Maps-first: only fill about from social when Maps gave us nothing. Don't
    # let a longer social blurb overwrite the Maps description (the old "longer
    # wins" rule pulled in whichever page had more marketing fluff).
    if not lead.about:
        lead.about = fb_data["about"] or ig_data["about"]

    if not lead.hours and fb_data["hours"]:
        lead.hours = fb_data["hours"]

    if not lead.services and fb_data["services"]:
        lead.services = fb_data["services"]

    # Set CDN url -- photos.download_photos() uses it as hero only when
    # logo_verified is True (i.e. the social page passed the name check).
    logo = fb_data["logo_url"] or ig_data["logo_url"]
    if logo and not lead.logo_url:
        lead.logo_url = logo
        # logo_verified was already set by find_social_media() if the page
        # matched; don't override it here — just leave it as-is.
