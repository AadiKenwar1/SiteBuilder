import re
from urllib.parse import urlparse, quote_plus, parse_qs
from email.utils import parsedate as parse_http_date

import httpx

from .config import CURRENT_YEAR, OUTDATED_YEARS
from .utils import delay

# Directory / aggregator / social domains that list a business's address+phone
# but are NOT the business's own website. A match on one of these never means
# the business has a site — otherwise every business would "have a website"
# because Yelp lists them.
_DIRECTORY_DOMAINS = {
    "facebook.com", "instagram.com", "twitter.com", "x.com", "linkedin.com",
    "yelp.com", "mapquest.com", "yellowpages.com", "yellowbook.com",
    "superpages.com", "bbb.org", "healthgrades.com", "zocdoc.com", "vitals.com",
    "wellness.com", "ratemds.com", "tripadvisor.com", "foursquare.com",
    "nextdoor.com", "angi.com", "angieslist.com", "thumbtack.com", "houzz.com",
    "manta.com", "chamberofcommerce.com", "citysearch.com", "local.com",
    "merchantcircle.com", "opendi.us", "ezlocal.com", "patch.com",
    "wikipedia.org", "indeed.com", "glassdoor.com", "ziprecruiter.com",
    "google.com", "gstatic.com", "googleusercontent.com", "youtube.com",
    "tiktok.com", "pinterest.com", "apple.com", "bing.com",
    # Provider-directory / profile platforms — a profile here is NOT the
    # business's own website (the business is still a good lead).
    "tebra.com", "patientpop.com", "kareo.com", "doctor.com", "caredash.com",
    "md.com", "sharecare.com", "webmd.com", "findatopdoc.com", "doximity.com",
    "solv.com", "sesamecare.com", "wellnessliving.com",
    # Booking / scheduling platforms — many salons, barbers, trades use only
    # these instead of a real site, so a listing here means "no website yet".
    "booksy.com", "vagaro.com", "fresha.com", "schedulicity.com",
    "styleseat.com", "mindbodyonline.com", "glossgenius.com", "setmore.com",
    "acuityscheduling.com", "getweave.com", "squareup.com",
}


def _digits(s: str) -> str:
    return re.sub(r"\D", "", s or "")


def registrable_domain(url: str) -> str:
    """'https://www.example.com/x' -> 'example.com' (best-effort, no PSL)."""
    net = urlparse(url).netloc.lower()
    return re.sub(r"^www\.", "", net)


def _is_directory(url: str) -> bool:
    dom = registrable_domain(url)
    if not dom:
        return True
    return any(dom == d or dom.endswith("." + d) for d in _DIRECTORY_DOMAINS)


async def confirm_website(
    page, name: str, area: str, phone: str, address: str,
    http_client: httpx.AsyncClient,
) -> str:
    """Find a business's own website when Google Maps doesn't list one.

    Many businesses have a site they never added to their Maps profile, so a
    missing Maps "website" link doesn't prove they have none. This Googles the
    business, scans the top organic results, skips directories/social pages, and
    returns the first NON-directory site whose page contains the business's
    phone number (most reliable) or street address. Returns '' if none found.

    Navigates the page to Google, so the caller must run it AFTER all Maps-page
    data is scraped (same constraint as the chain check).
    """
    phone_digits = _digits(phone)[-10:]
    m = re.match(r"\s*(\d+)\s+([A-Za-z]+)", address or "")
    street_key = f"{m.group(1)} {m.group(2)}".lower() if m else ""
    if len(phone_digits) < 10 and not street_key:
        return ""  # nothing reliable to match against

    # Collect candidate result URLs (skip directories/social/Google-internal).
    urls: list[str] = []
    try:
        await page.goto(
            f"https://www.google.com/search?q={quote_plus(f'{name} {area}')}",
            wait_until="domcontentloaded", timeout=20_000,
        )
        await delay(1.5, 2.5)
        for link in await page.query_selector_all("a[href]"):
            href = await link.get_attribute("href") or ""
            if href.startswith("/url?") or "google.com/url?" in href:
                href = (parse_qs(urlparse(href).query).get("q") or [""])[0]
            if not href.startswith("http") or _is_directory(href):
                continue
            clean = href.split("#")[0]
            if clean not in urls:
                urls.append(clean)
            if len(urls) >= 8:
                break
    except Exception:
        return ""

    # Fetch each candidate and confirm it's really this business.
    for url in urls:
        try:
            r = await http_client.get(url, timeout=10, follow_redirects=True)
            text = r.text[:200_000]
        except Exception:
            continue
        if len(phone_digits) == 10 and phone_digits in _digits(text):
            return url
        if street_key and street_key in text.lower():
            return url
    return ""


async def check_website_age(url: str, client: httpx.AsyncClient) -> tuple[bool, str]:
    """
    Returns (is_outdated, reason_string).
    Tries three methods in order:
      1. HTTP Last-Modified header
      2. Copyright year in HTML footer
      3. Wayback Machine CDX API
    """
    try:
        domain = urlparse(url).netloc or url.split("/")[0]
        clean  = re.sub(r"^www\.", "", domain)

        # 1. Last-Modified header
        try:
            r  = await client.head(url, timeout=8, follow_redirects=True)
            lm = r.headers.get("Last-Modified", "")
            if lm:
                parsed = parse_http_date(lm)
                if parsed:
                    yr = parsed[0]
                    if 1990 < yr <= CURRENT_YEAR:
                        outdated = CURRENT_YEAR - yr >= OUTDATED_YEARS
                        return outdated, f"Last-Modified: {yr}"
        except Exception:
            pass

        # 2. Copyright year in HTML footer
        try:
            r    = await client.get(url, timeout=12, follow_redirects=True)
            html = r.text[:60_000]
            footer = re.search(r"<footer[^>]*>(.*?)</footer>", html, re.DOTALL | re.IGNORECASE)
            haystack = footer.group(1) if footer else html[-12_000:]
            years = []
            for pat in [
                r"©\s*(?:Copyright\s*)?(\d{4})",
                r"[Cc]opyright\s*(?:©\s*)?(\d{4})",
                r"[Cc]opyright\s+\d{4}\s*[-–]\s*(\d{4})",
            ]:
                for m in re.finditer(pat, haystack):
                    yr = int(m.group(1))
                    if 1990 <= yr <= CURRENT_YEAR:
                        years.append(yr)
            if years:
                latest = max(years)
                outdated = CURRENT_YEAR - latest >= OUTDATED_YEARS
                return outdated, f"© {latest} in footer"
        except Exception:
            pass

        # 3. Wayback Machine CDX
        try:
            cdx = (
                f"https://web.archive.org/cdx/search/cdx"
                f"?url={clean}&output=json&limit=1&fl=timestamp"
                f"&filter=statuscode:200&fastLatest=true"
            )
            r    = await client.get(cdx, timeout=10)
            data = r.json()
            if isinstance(data, list) and len(data) > 1:
                yr = int(str(data[1][0])[:4])
                outdated = CURRENT_YEAR - yr >= OUTDATED_YEARS
                return outdated, f"Wayback last seen: {yr}"
        except Exception:
            pass

        return False, "Age unknown"

    except Exception as e:
        return False, f"Error: {e}"
