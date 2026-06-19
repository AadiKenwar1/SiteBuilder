"""
Tier 2 — single-listing debug harness for the fragile, DOM-dependent code.

Runs ONLY Phase-2 scraping (photo gallery + reviews) against one Google Maps
listing, so you can iterate on selectors in ~10 seconds instead of running the
whole screening crawl. Browser is visible by default so you can watch it.

Usage:
    python tests/debug_listing.py "<maps_url>" [name] [address]

Example:
    python tests/debug_listing.py "https://www.google.com/maps/place/..." "Joe's Diner" "12 Main St"

Output: prints what was found and writes photos to outputs/photos/<slug>/.
"""
import asyncio
import os
import sys

# Make the project root importable when run as `python tests/debug_listing.py`.
sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

import httpx
from playwright.async_api import async_playwright

from pipeline.models import Lead
from pipeline.utils import make_browser, lead_slug
from pipeline.photos import download_photos, scrape_maps_photos
from pipeline.maps import scrape_reviews


async def main(maps_url: str, name: str, address: str) -> None:
    lead = Lead(
        business_id="BIZ_DEBUG",
        business_name=name or "Debug Business",
        address=address,
        maps_url=maps_url,
        review_count=10,   # non-zero so scrape_reviews actually runs
    )
    lead.slug = lead_slug(lead.business_name, lead.address)
    print(f"slug      : {lead.slug}")
    print(f"maps_url  : {maps_url}\n")

    async with httpx.AsyncClient(
        headers={"User-Agent": "Mozilla/5.0 (compatible; LeadScraper/6.0)"},
        verify=False,
        timeout=httpx.Timeout(15.0),
    ) as http_client:
        async with async_playwright() as pw:
            browser, page = await make_browser(pw, headless=False)   # watch it work
            try:
                # 1. Photo gallery (URLs only first, so you can see what matched)
                print("── scraping Maps photo URLs ──")
                urls = await scrape_maps_photos(page, lead)
                print(f"  {len(urls)} photo URLs found")
                for u in urls[:5]:
                    print(f"    {u}")

                # 2. Download into the per-business folder
                print("\n── downloading photos ──")
                await download_photos(page, lead, http_client, "outputs/photos")
                print(f"  photo_dir   : {lead.photo_dir}")
                print(f"  photo_count : {lead.photo_count}")
                print(f"  hero        : {lead.logo_url}")

                # 3. Reviews
                print("\n── scraping reviews ──")
                reviews = await scrape_reviews(page, lead)
                print(f"  {len(reviews)} reviews")
                for r in reviews[:3]:
                    print(f"    [{r.stars}★] {r.reviewer}: {r.text[:70]}")

                print("\nDone. Check outputs/photos/" + lead.slug + "/")
            finally:
                await browser.close()


if __name__ == "__main__":
    if len(sys.argv) < 2:
        sys.exit('usage: python tests/debug_listing.py "<maps_url>" [name] [address]')
    url     = sys.argv[1]
    name    = sys.argv[2] if len(sys.argv) > 2 else ""
    address = sys.argv[3] if len(sys.argv) > 3 else ""
    asyncio.run(main(url, name, address))
