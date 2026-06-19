from __future__ import annotations

import asyncio, random, re
from pathlib import Path
from typing import TYPE_CHECKING

if TYPE_CHECKING:                      # Page is only used for type hints; importing
    from playwright.async_api import Page   # it lazily lets crm/promote tooling run
                                            # without Playwright installed.


async def delay(lo: float = 1.5, hi: float = 3.5):
    await asyncio.sleep(random.uniform(lo, hi))


def lead_slug(name: str, address: str = "") -> str:
    """
    Stable, filesystem-safe identity for a business.
    Same name + address always yields the same slug, so it works as the
    dedup key, the CRM merge key, and the photo-folder name everywhere.
    """
    base = f"{name} {address[:20]}".lower()
    s = re.sub(r"[^a-z0-9]+", "-", base).strip("-")
    return s[:60] or "biz"


async def download_image(url, dest, http_client) -> bool:
    """Download an image to dest. Returns True on success."""
    if not url:
        return False
    try:
        r = await http_client.get(str(url), timeout=15, follow_redirects=True)
        if r.status_code == 200 and len(r.content) > 500:
            dest = Path(dest)
            dest.parent.mkdir(parents=True, exist_ok=True)
            dest.write_bytes(r.content)
            return True
    except Exception:
        pass
    return False


async def safe_text(page: Page, *selectors: str) -> str:
    for sel in selectors:
        try:
            el = await page.query_selector(sel)
            if el:
                txt = (await el.inner_text()).strip()
                if txt:
                    return txt
        except Exception:
            pass
    return ""


async def safe_attr(page: Page, selector: str, attr: str) -> str:
    try:
        el = await page.query_selector(selector)
        val = await el.get_attribute(attr) if el else None
        return (val or "").strip()
    except Exception:
        return ""


def normalize_name(name: str) -> str:
    return re.sub(r'[^a-z0-9\s]', '', name.lower()).strip()


async def dismiss_consent(page: Page):
    for sel in [
        'button[aria-label*="Accept all"]',
        'button[aria-label*="Agree"]',
        '#L2AGLb',
        'form[action*="consent"] button',
    ]:
        try:
            btn = await page.query_selector(sel)
            if btn and await btn.is_visible():
                await btn.click()
                await delay(0.8, 1.5)
                return
        except Exception:
            pass


async def make_browser(pw, headless: bool = True):
    browser = await pw.chromium.launch(
        headless=headless,
        args=["--no-sandbox", "--disable-blink-features=AutomationControlled"],
    )
    ctx = await browser.new_context(
        viewport={"width": 1280, "height": 900},
        locale="en-US",
        user_agent=(
            "Mozilla/5.0 (Windows NT 10.0; Win64; x64) "
            "AppleWebKit/537.36 (KHTML, like Gecko) "
            "Chrome/125.0.0.0 Safari/537.36"
        ),
    )
    page = await ctx.new_page()
    await page.add_init_script(
        "Object.defineProperty(navigator, 'webdriver', {get: () => undefined});"
    )
    return browser, page
