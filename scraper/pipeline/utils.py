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


# Weekday short key -> full name, in calendar order. The uniform shape every
# business_content.hours map uses (see SITES-PLATFORM-PLAN.md §4.6).
_DAYS = [
    ("mon", "monday"), ("tue", "tuesday"), ("wed", "wednesday"),
    ("thu", "thursday"), ("fri", "friday"), ("sat", "saturday"), ("sun", "sunday"),
]


def parse_hours(raw: str) -> dict:
    """Freeform Google-Maps hours string -> uniform {mon..sun} map.

    Each value is a cleaned time range or "Closed". Days not found default to
    "Closed". Parenthetical notes ("(Juneteenth)") and trailing noise
    ("Hours might differ") are stripped. Used to seed business_content.hours so
    every site renders and edits hours the same way.
    """
    out = {key: "Closed" for key, _ in _DAYS}
    if not raw:
        return out
    for chunk in re.split(r"[|\n;]+", raw):
        seg = chunk.strip()
        if not seg:
            continue
        low = seg.lower()
        key = next(
            (k for k, full in _DAYS if full in low or re.search(rf"\b{k}\b", low)),
            None,
        )
        if not key:
            continue
        val = seg.split(":", 1)[1] if ":" in seg else seg
        val = re.sub(r"\([^)]*\)", " ", val)                       # drop "(Juneteenth)"
        val = re.sub(r"hours?\s+might\s+differ", " ", val, flags=re.I)
        val = re.sub(r"\s+", " ", val).strip(" .-")
        out[key] = "Closed" if (not val or "closed" in val.lower()) else val
    return out


# Snake_case identifiers (connection_quality, is_ad, content_category, …) are
# scraper/internal metadata that occasionally leaks into the Services field —
# never a real menu item. Drop them so they don't seed business_content.
_METADATA_TOKEN = re.compile(r"^[a-z][a-z0-9]*(_[a-z0-9]+)+$")


def parse_services(raw: str) -> list[dict]:
    """Comma/newline/pipe-separated services string -> [{name,description,price}].

    Deduplicates case-insensitively and preserves order. Drops snake_case
    metadata tokens that aren't real services. Empty/all-junk input -> []. Seeds
    business_content.services; the owner (or the site builder) refines it later.
    """
    if not raw:
        return []
    out, seen = [], set()
    for item in re.split(r"[,\n;|]+", raw):
        name = re.sub(r"\s+", " ", item).strip(" .-")
        if not name:
            continue
        if _METADATA_TOKEN.match(name):     # e.g. "connection_quality", "is_ad"
            continue
        key = name.lower()
        if key in seen:
            continue
        seen.add(key)
        out.append({"name": name, "description": "", "price": ""})
    return out


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
