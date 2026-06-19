"""
Google Maps scraping:
  collect_place_urls()  — search results page → list of listing URLs
  extract_lead()        — one listing → Lead (or None if filtered)
  scrape_reviews()      — one listing → list of Reviews
"""
import re
from typing import Optional

import httpx
from playwright.async_api import Page

from .config import MAX_PER_SEARCH, MAX_REVIEWS, MAX_REVIEWS_SCRAPE, CURRENT_YEAR
from .models import Lead, Review
from .utils import delay, safe_text, safe_attr, dismiss_consent
from .website_check import check_website_age
from .chain_check import is_big_business


# ══════════════════════════════════════════════════════════════════════════════
#  COLLECT LISTING URLS FROM A SEARCH
# ══════════════════════════════════════════════════════════════════════════════
async def collect_place_urls(page: Page, search_term: str, area: str) -> list[str]:
    query = f"{search_term} in {area}"
    await page.goto(
        f"https://www.google.com/maps/search/{query.replace(' ', '+')}",
        wait_until="domcontentloaded", timeout=30_000,
    )
    await delay(3, 5)
    await dismiss_consent(page)

    feed = 'div[role="feed"]'
    seen: set[str] = set()

    for _ in range(5):
        await page.evaluate(f"""
            const el = document.querySelector('{feed}');
            if (el) el.scrollTop = el.scrollHeight;
        """)
        await delay(1.5, 2.5)
        links = await page.query_selector_all(f'{feed} a[href*="/maps/place/"]')
        batch = {(await l.get_attribute("href") or "") for l in links}
        batch = {u for u in batch if u}
        if batch == seen:
            break
        seen = batch

    return list(seen)[:MAX_PER_SEARCH]


# ══════════════════════════════════════════════════════════════════════════════
#  FIELD EXTRACTORS
# ══════════════════════════════════════════════════════════════════════════════
async def _get_hours(page: Page) -> str:
    try:
        for sel in [
            'button[jsaction*="openhours"]',
            '[data-item-id="oh"] button',
            'div[data-item-id="oh"]',
        ]:
            btn = await page.query_selector(sel)
            if btn:
                try:
                    await btn.click()
                    await delay(0.5, 1.0)
                except Exception:
                    pass
                break

        rows = await page.query_selector_all(
            'table.WgFkxc tr, div[jslog*="openhours"] tr, table tr'
        )
        day_hours = []
        for row in rows:
            cells = await row.query_selector_all('td, th')
            if len(cells) >= 2:
                day  = (await cells[0].inner_text()).strip()
                time = (await cells[1].inner_text()).strip().replace('\n', ', ')
                if day and time and len(day) <= 20:
                    day_hours.append(f"{day}: {time}")
        if day_hours:
            return " | ".join(day_hours)

        summary = await safe_text(page,
            'div[data-item-id="oh"] .OMl5r',
            'div[data-item-id="oh"] span',
        )
        return summary
    except Exception:
        return ""


async def _get_price_range(page: Page) -> str:
    try:
        for sel in [
            'span[aria-label*="Price"]',
            'span[aria-label*="price"]',
            'button[aria-label*="Price"]',
        ]:
            el = await page.query_selector(sel)
            if el:
                label = (await el.get_attribute("aria-label") or "").strip()
                m = re.search(r'(\$+)', label)
                if m:
                    return m.group(1)

        result = await page.evaluate(r"""() => {
            const all = document.querySelectorAll('span, button, div');
            for (const el of all) {
                if (el.children.length > 0) continue;
                const t = (el.innerText || el.textContent || '').trim();
                if (/^\$+$/.test(t) && t.length <= 4) return t;
            }
            return '';
        }""")
        return result or ""
    except Exception:
        return ""


async def _get_about(page: Page) -> str:
    try:
        for sel in [
            'div.PYvSYb',
            'div[jslog*="description"] span',
            'div[aria-label*="About this place"] span',
        ]:
            el = await page.query_selector(sel)
            if el:
                txt = (await el.inner_text()).strip()
                if txt and not re.search(r'\d+:\d+\s*(AM|PM)', txt, re.IGNORECASE):
                    if len(txt) > 20:
                        return txt[:500]

        sections = await page.query_selector_all('div[jsaction*="openpane"] div.fontBodyMedium')
        for sec in sections:
            txt = (await sec.inner_text()).strip()
            if txt and len(txt) > 30 and not re.search(r'\d+:\d+\s*(AM|PM)', txt, re.IGNORECASE):
                return txt[:500]
    except Exception:
        pass
    return ""


async def _get_services(page: Page) -> str:
    """
    Pull services from Google Maps' structured list items.
    Filters out hidden analytics keys (snake_case identifiers).
    """
    _SNAKE = re.compile(r'^[a-z][a-z0-9_]+$')   # e.g. connection_quality, is_ad
    try:
        raw = await page.evaluate(r"""() => {
            const results = [];
            document.querySelectorAll('li[aria-label]').forEach(el => {
                const t = (el.getAttribute('aria-label') || '').trim();
                if (t && t.length > 2 && t.length < 80) results.push(t);
            });
            return [...new Set(results)].slice(0, 20);
        }""")
        if raw:
            # Keep only human-readable labels (not snake_case analytics keys)
            return ", ".join(t for t in raw if not _SNAKE.match(t))
        return ""
    except Exception:
        return ""


async def _get_year_established(page: Page) -> str:
    try:
        content = await page.content()
        for pat in [
            r'[Oo]pened?\s+in\s+(\d{4})',
            r'[Ee]stablished\s+(?:in\s+)?(\d{4})',
            r'[Ss]ince\s+(\d{4})',
            r'[Ff]ounded\s+(?:in\s+)?(\d{4})',
        ]:
            m = re.search(pat, content)
            if m:
                yr = int(m.group(1))
                if 1900 <= yr <= CURRENT_YEAR:
                    return str(yr)
    except Exception:
        pass
    return ""


# ══════════════════════════════════════════════════════════════════════════════
#  EXTRACT ONE LEAD FROM A LISTING PAGE
# ══════════════════════════════════════════════════════════════════════════════
async def extract_lead(
    page: Page,
    url: str,
    area: str,
    http_client: httpx.AsyncClient,
) -> Optional[Lead]:
    try:
        await page.goto(url, wait_until="domcontentloaded", timeout=25_000)
    except Exception as e:
        print(f"      nav error: {e}")
        return None
    await delay(1.5, 2.5)

    # Name
    name = await safe_text(page, "h1.DUwDvf", "h1.fontHeadlineLarge", "h1[jstcache]", "h1")
    if not name:
        return None

    # Review count pre-filter
    review_count = 0
    for sel in [
        'button[jsaction*="reviewChart"] span',
        'span[aria-label*="reviews"]',
        '.F7nice span', 'span.UY7F9',
    ]:
        try:
            el = await page.query_selector(sel)
            if el:
                num = re.sub(r'[^\d]', '', await el.inner_text())
                if num:
                    review_count = int(num)
                    break
        except Exception:
            pass

    if review_count > MAX_REVIEWS:
        print(f"      skip [{name}] -- {review_count} reviews (too popular)")
        return None

    # Rating
    rating = await safe_text(page, 'div.F7nice span[aria-hidden="true"]', '.MW4etd')
    if not re.match(r'^\d+\.?\d*$', rating):
        rating = ""

    # Business type
    biz_type = await safe_text(page,
        "button.DkEaL", ".DkEaL",
        'button[jsaction*="category"]',
        '[aria-label*="Category"]',
    )

    # Website check
    website_url = ""
    el = await page.query_selector('a[data-item-id="authority"]')
    if el:
        website_url = (await el.get_attribute("href") or "").strip()
    if not website_url:
        for sel in [
            'a[href^="http"][data-tooltip*="ebsite" i]',
            'a[aria-label*="ebsite" i][href^="http"]',
        ]:
            el = await page.query_selector(sel)
            if el and await el.is_visible():
                website_url = (await el.get_attribute("href") or "").strip()
                break

    if not website_url:
        lead_reason = "No website"
    else:
        is_outdated, reason = await check_website_age(website_url, http_client)
        if is_outdated:
            lead_reason = f"Outdated -- {reason}"
        else:
            print(f"      skip [{name}] -- active website")
            return None

    # Collect all Maps data BEFORE is_big_business navigates away
    address = ""
    parts = await page.query_selector_all(
        'button[data-item-id="address"] .fontBodyMedium, '
        'button[data-tooltip="Copy address"] .fontBodyMedium'
    )
    if parts:
        texts = [t for p in parts if (t := (await p.inner_text()).strip())]
        address = ", ".join(texts)
    if not address:
        address = await safe_text(page, 'button[data-item-id="address"]')

    phone = ""
    pid = await safe_attr(page, 'button[data-item-id^="phone:tel:"]', "data-item-id")
    if pid.startswith("phone:tel:"):
        phone = pid.replace("phone:tel:", "").strip()
    if not phone:
        phone = await safe_text(page,
            'button[data-tooltip="Copy phone number"]',
            '[aria-label*="Phone"]',
        )

    price_range      = await _get_price_range(page)
    hours            = await _get_hours(page)
    about            = await _get_about(page)
    services         = await _get_services(page)
    year_established = await _get_year_established(page)
    maps_url         = url.split("?")[0]

    # Chain check — navigates to Google, must be LAST
    if await is_big_business(page, name, website_url, http_client):
        print(f"      skip [{name}] -- chain/big business")
        return None

    return Lead(
        business_name    = name,
        business_type    = biz_type,
        area             = area,
        maps_url         = maps_url,
        address          = address,
        phone            = phone,
        rating           = rating,
        review_count     = review_count,
        price_range      = price_range,
        hours            = hours,
        about            = about,
        services         = services,
        year_established = year_established,
        lead_reason      = lead_reason,
        website_url      = website_url,
    )


# ══════════════════════════════════════════════════════════════════════════════
#  SCRAPE REVIEWS
# ══════════════════════════════════════════════════════════════════════════════
async def scrape_reviews(page: Page, lead: Lead) -> list[Review]:
    reviews: list[Review] = []
    seen_texts: set[str]  = set()

    if not lead.maps_url or lead.review_count == 0:
        return reviews

    try:
        await page.goto(lead.maps_url, wait_until="domcontentloaded", timeout=25_000)
        await delay(2, 3)

        # Click the Reviews tab
        for sel in [
            'button[aria-label*="Reviews"]',
            'button[jsaction*="pane.rating.moreReviews"]',
            '[data-tab-index="1"]',
        ]:
            try:
                btn = await page.query_selector(sel)
                if btn and await btn.is_visible():
                    await btn.click()
                    await delay(1.5, 2.5)
                    break
            except Exception:
                pass

        # Scroll to load reviews
        for _ in range(4):
            await page.evaluate("""
                const feed = document.querySelector('div[role="feed"]');
                if (feed) feed.scrollTop = feed.scrollHeight;
            """)
            await delay(1.5, 2.0)

        cards = await page.query_selector_all(
            'div[data-review-id], div[class*="jftiEf"], div[jslog*="review"]'
        )

        for card in cards[:MAX_REVIEWS_SCRAPE]:
            try:
                # Reviewer name
                reviewer = ""
                for sel in ['.d4r55', 'button[class*="reviewer"]', 'div[class*="fontTitleSmall"]']:
                    el = await card.query_selector(sel)
                    if el:
                        reviewer = (await el.inner_text()).strip()
                        if reviewer:
                            break

                # Stars
                stars = ""
                for sel in ['span[role="img"][aria-label*="star"]', 'span[class*="kvMYJc"]']:
                    el = await card.query_selector(sel)
                    if el:
                        aria = (await el.get_attribute("aria-label")) or ""
                        m = re.search(r'(\d)', aria)
                        if m:
                            stars = m.group(1)
                            break

                # Date
                date = ""
                for sel in ['span.rsqaWe', 'span[class*="dehysf"]']:
                    el = await card.query_selector(sel)
                    if el:
                        date = (await el.inner_text()).strip()
                        if date:
                            break

                # Review text — expand "More" first
                for expand_sel in ['button[jsaction*="review.expandReview"]', 'button.w8nwRe']:
                    try:
                        btn = await card.query_selector(expand_sel)
                        if btn:
                            await btn.click()
                            await delay(0.3, 0.5)
                    except Exception:
                        pass

                text = ""
                for sel in ['span.wiI7pd', 'div[class*="review-full-text"]', 'span.HgLrS']:
                    el = await card.query_selector(sel)
                    if el:
                        text = (await el.inner_text()).strip()
                        if text:
                            break

                if not text:
                    continue

                # Deduplicate
                key = text[:100].lower()
                if key in seen_texts:
                    continue
                seen_texts.add(key)

                reviews.append(Review(
                    business_id   = lead.business_id,
                    business_name = lead.business_name,
                    reviewer      = reviewer,
                    stars         = stars,
                    date          = date,
                    text          = text,
                ))

            except Exception:
                continue

    except Exception as e:
        print(f"      reviews error: {e}")

    return reviews
