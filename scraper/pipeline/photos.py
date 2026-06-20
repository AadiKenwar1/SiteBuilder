"""
Photo gathering — the business's REAL photos (exterior, interior, work, food),
not just a logo. The dependable source is the Google Maps photo gallery; FB/IG
galleries are unreliable (obfuscation / login walls) so we lean on Maps.

download_photos() is Phase-2 only (keepers): it scrapes the Maps gallery,
normalizes each URL to high resolution, dedups, and saves into a per-business
folder along with a hero image.
"""
import re
from pathlib import Path

from playwright.async_api import Page

from .config import MAX_PHOTOS
from .models import Lead
from .utils import delay, download_image


def _hi_res(url: str) -> str:
    """
    Maps photo URLs carry a display-size suffix like '=w408-h306-k-no'.
    Strip it and request a large size so the assets are usable for a website.
    """
    url = url.split("?")[0]
    if "=" in url:
        return url.split("=")[0] + "=s1600"
    return url


def _photo_id(url: str) -> str:
    """Stable id = the path before the size '=' param (same photo, any size)."""
    return url.split("?")[0].split("=")[0]


async def scrape_maps_photos(page: Page, lead: Lead) -> list[str]:
    """Return a deduped list of high-res photo URLs from the Maps listing."""
    urls: list[str] = []
    if not lead.maps_url:
        return urls

    try:
        await page.goto(lead.maps_url, wait_until="domcontentloaded", timeout=25_000)
        await delay(2, 3)

        # "See photos" opens the scrollable photo grid (the hero button opens
        # Street View mode instead, which only shows 1-2 panoramic images).
        for sel in [
            'button:has-text("See photos")',
            'button:has-text("See all photos")',
            'button[aria-label*="All photos"]',
        ]:
            try:
                btn = await page.query_selector(sel)
                if btn and await btn.is_visible():
                    await btn.click()
                    await delay(2, 3)
                    break
            except Exception:
                pass

        # Scroll the photo grid to lazy-load thumbnails.
        # After "See photos" Maps opens a grid page; div[role="main"] is the
        # scrollable container there.
        for _ in range(5):
            await page.evaluate("""
                const sc = document.querySelector('div[role="main"]');
                if (sc) sc.scrollTop = sc.scrollHeight;
                else window.scrollTo(0, document.body.scrollHeight);
            """)
            await delay(1.5, 2)

        # Collect photo URLs from:
        #   • <img src> / <img srcset>       — listing page thumbnails
        #   • CSS background-image on divs   — photo grid thumbnails (the common case
        #                                      after "See photos" opens the viewer)
        #   • data-src / data-background     — lazy-loaded variants
        raw = await page.evaluate(r"""() => {
            const CDN = /googleusercontent\.com|ggpht\.com/;
            const seen = new Set();
            const out  = [];

            function add(url) {
                if (!url || !CDN.test(url)) return;
                const id = url.split('?')[0].split('=')[0];
                if (seen.has(id)) return;
                seen.add(id);
                out.push(url);
            }

            // img src / srcset / data-src
            document.querySelectorAll('img').forEach(im => {
                add(im.src);
                add(im.getAttribute('data-src') || '');
                (im.srcset || '').split(',').forEach(s => add(s.trim().split(' ')[0]));
            });

            // CSS background-image on any element (the photo grid uses this)
            document.querySelectorAll('[style]').forEach(el => {
                const m = (el.getAttribute('style') || '')
                    .match(/url\(['"]?(https?:\/\/[^'")\s]+)/i);
                if (m) add(m[1]);
            });

            // data-background (some lazy loaders)
            document.querySelectorAll('[data-background]').forEach(el => {
                add(el.getAttribute('data-background') || '');
            });

            return out;
        }""")

        # _photo_id dedup already happened in JS; rewrite each to hi-res.
        for u in raw:
            urls.append(_hi_res(u))

    except Exception as e:
        print(f"      photos error: {e}")

    return urls[:MAX_PHOTOS]


async def download_photos(page: Page, lead: Lead, http_client, photos_root: str) -> None:
    """
    Save the business's photos into photos_root/<slug>/:
      • hero.jpg   — the social logo if we have one, else the first gallery photo
      • 01.jpg …   — gallery photos
    Sets lead.photo_dir, lead.photo_count, and lead.logo_url (local hero path).
    """
    slug = lead.slug or "biz"
    folder = Path(photos_root) / slug
    folder.mkdir(parents=True, exist_ok=True)
    lead.photo_dir = str(folder)

    gallery = await scrape_maps_photos(page, lead)

    count = 0

    # Hero: use the social logo only when it was verified to belong to this
    # business (find_social_media ran a name check). Otherwise fall back to the
    # first real Maps gallery photo so we never use a stranger's logo as hero.
    hero_url = (lead.logo_url if lead.logo_verified else "") or (gallery[0] if gallery else "")
    if hero_url and await download_image(hero_url, folder / "hero.jpg", http_client):
        lead.logo_url = str(folder / "hero.jpg")
        count += 1
    else:
        lead.logo_url = ""   # nothing downloaded; don't leave a dangling CDN url

    # Gallery photos.
    for idx, url in enumerate(gallery, 1):
        if idx > MAX_PHOTOS:
            break
        if await download_image(url, folder / f"{idx:02d}.jpg", http_client):
            count += 1

    lead.photo_count = count
    if count:
        print(f"      photos saved -> {folder}  ({count} files)")
