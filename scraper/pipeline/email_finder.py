import re

import httpx
from playwright.async_api import Page

from .config import EMAIL_SKIP_DOMAINS, EMAIL_SKIP_PREFIXES
from .utils import delay

_EMAIL_RE = re.compile(r'\b[a-zA-Z0-9._%+\-]+@[a-zA-Z0-9.\-]+\.[a-zA-Z]{2,}\b')


def clean_emails(text: str) -> list[str]:
    results = []
    for e in _EMAIL_RE.findall(text):
        e = e.lower().rstrip('.')
        if not e or '@' not in e:
            continue
        domain = e.split('@')[1]
        if any(d in domain for d in EMAIL_SKIP_DOMAINS):
            continue
        if any(e.startswith(p) for p in EMAIL_SKIP_PREFIXES):
            continue
        if re.search(r'\.(png|jpg|gif|svg|ico|css|js|woff)$', e):
            continue
        if len(e) > 80 or len(e) < 6:
            continue
        if e not in results:
            results.append(e)
    return results


async def find_email(
    page: Page,
    name: str,
    area: str,
    website_url: str,
    facebook_url: str,
    http_client: httpx.AsyncClient,
) -> str:
    """
    Find a contact email. Tries in order:
      1. Business website (homepage, /contact, /about)
      2. Google search
      3. Facebook About page
    """

    # Method 1: scrape the website
    if website_url:
        base = website_url.rstrip("/")
        for path in ["", "/contact", "/contact-us", "/about", "/about-us"]:
            try:
                r = await http_client.get(base + path, timeout=10, follow_redirects=True)
                # Prefer explicit mailto: links
                mailto = re.search(r'mailto:([^\s"\'<>?&]+)', r.text)
                if mailto:
                    e = mailto.group(1).split("?")[0].lower().strip()
                    cleaned = clean_emails(e)
                    if cleaned:
                        return cleaned[0]
                emails = clean_emails(r.text)
                if emails:
                    return emails[0]
            except Exception:
                pass

    # Method 2: Google search
    try:
        q = f'"{name}" "{area}" email contact'
        await page.goto(
            f"https://www.google.com/search?q={q.replace(' ', '+')}",
            wait_until="domcontentloaded", timeout=15_000,
        )
        await delay(1.0, 2.0)
        emails = clean_emails(await page.content())
        if emails:
            return emails[0]
    except Exception:
        pass

    # Method 3: Facebook About page
    if facebook_url:
        try:
            await page.goto(
                facebook_url.rstrip("/") + "/about",
                wait_until="domcontentloaded", timeout=15_000,
            )
            await delay(1.5, 2.5)
            emails = clean_emails(await page.content())
            if emails:
                return emails[0]
        except Exception:
            pass

    return ""
