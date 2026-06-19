import re

import httpx
from playwright.async_api import Page

from .config import BIG_BIZ_TEXT_SIGNALS, SITE_CHAIN_SIGNALS
from .utils import delay


async def is_big_business(
    page: Page,
    name: str,
    website_url: str,
    http_client: httpx.AsyncClient,
) -> bool:
    """
    Googles the business name to detect chains and large corporations.
    Returns True if it should be skipped.

    Three signals checked:
      1. Wikipedia article closely matching the business name
      2. Chain/corporate language in Google search snippets
      3. Store-locator or franchise pages on the business's own website
    """
    try:
        await page.goto(
            f"https://www.google.com/search?q={name.replace(' ', '+')}+business",
            wait_until="domcontentloaded",
            timeout=15_000,
        )
        await delay(1.0, 1.5)
        content = await page.content()
        lower   = content.lower()

        # Signal 1: Wikipedia article matching this business name
        wiki_slugs = re.findall(r'wikipedia\.org/wiki/([A-Za-z0-9_\-]+)"', content)
        name_words = [w for w in name.lower().split() if len(w) > 3]
        for slug in wiki_slugs[:5]:
            slug_clean = slug.replace('_', ' ').replace('-', ' ').lower()
            matches = sum(1 for w in name_words if w in slug_clean)
            if matches >= min(2, len(name_words)):
                print(f"      -> Wikipedia: {slug}")
                return True

        # Signal 2: Chain language in search results
        for pattern in BIG_BIZ_TEXT_SIGNALS:
            if re.search(pattern, lower):
                print(f"      -> Chain signal: '{pattern}'")
                return True

        # Signal 3: Store locator on the business website
        if website_url:
            try:
                resp = await http_client.get(website_url, timeout=8, follow_redirects=True)
                site_lower = resp.text.lower()
                for signal in SITE_CHAIN_SIGNALS:
                    if signal in site_lower:
                        print(f"      -> Site chain signal: '{signal}'")
                        return True
            except Exception:
                pass

    except Exception:
        pass

    return False
