import re
from urllib.parse import urlparse
from email.utils import parsedate as parse_http_date

import httpx

from .config import CURRENT_YEAR, OUTDATED_YEARS


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
