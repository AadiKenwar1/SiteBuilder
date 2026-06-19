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
from .utils import delay

_SKIP_FB = {"search", "sharer", "l.facebook", "login", "help", "about", "groups", "watch"}
_SKIP_IG = {"/p/", "/reel/", "/explore", "/stories", "login", "help", "tags", "/tv/"}


# ══════════════════════════════════════════════════════════════════════════════
#  FINDING SOCIAL PAGES
# ══════════════════════════════════════════════════════════════════════════════
def _unwrap_google_url(href: str, domain: str) -> str:
    m = re.search(rf"url\?q=(https?://(?:www\.)?{re.escape(domain)}/[^&\s]+)", href)
    if m:
        return m.group(1)
    return href if (domain in href and href.startswith("http")) else ""


async def find_social_media(page: Page, name: str, area: str) -> tuple[str, str]:
    """Returns (facebook_url, instagram_url) by Googling site: searches."""
    facebook = instagram = ""

    for platform, domain, skip_set, pattern in [
        ("facebook",  "facebook.com",  _SKIP_FB, r'facebook\.com/(?!sharer|search|l\.|watch)[\w.]+/?$'),
        ("instagram", "instagram.com", _SKIP_IG, r'instagram\.com/@?[\w.]+/?$'),
    ]:
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
                if re.search(pattern, url):
                    if platform == "facebook":
                        facebook = url.split("?")[0]
                    else:
                        instagram = url.split("?")[0]
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
                filtered = [s for s in svcs if not any(
                    kw in s.lower() for kw in
                    ["facebook", "instagram", "twitter", "home", "about",
                     "photos", "reviews", "menu"]
                )]
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
            if cleaned and len(cleaned) > 10:
                result["about"] = cleaned[:500]

    except Exception:
        pass

    return result


# ══════════════════════════════════════════════════════════════════════════════
#  ENRICHMENT ORCHESTRATOR
# ══════════════════════════════════════════════════════════════════════════════
async def enrich_from_social(lead: Lead, http_client: httpx.AsyncClient) -> None:
    """Fills gaps in lead fields by scraping Facebook and Instagram in-place."""
    fb_data = await scrape_facebook(lead.facebook_url, http_client)
    ig_data = await scrape_instagram(lead.instagram_url, http_client)

    if not lead.about:
        lead.about = fb_data["about"] or ig_data["about"]
    elif ig_data["about"] and len(ig_data["about"]) > len(lead.about):
        lead.about = ig_data["about"]

    if not lead.hours and fb_data["hours"]:
        lead.hours = fb_data["hours"]

    if not lead.services and fb_data["services"]:
        lead.services = fb_data["services"]

    # Set CDN url -- photos.download_photos() turns it into the local hero image.
    if not lead.logo_url:
        lead.logo_url = fb_data["logo_url"] or ig_data["logo_url"]
