"""
Main orchestration loop — two-phase pipeline.

  Phase 1 (SCREEN):  scan a candidate POOL with cheap signals, score each.
  RANK:              sort the pool by score, keep the top TARGET_LEADS.
  Phase 2 (ENRICH):  for keepers only, download real photos, scrape reviews,
                     deep-search email, then recompute the final score.

Expensive work (photos / reviews / email deep-search) runs only for keepers,
so ranking is meaningful and we never gather assets for businesses we discard.
Email and social are SIGNALS that feed the score, not hard drop gates — the
only true drops are the core filters in extract_lead (active website, chain,
too popular).
"""
import csv, random, sys
from pathlib import Path

import httpx
from playwright.async_api import async_playwright

from .config import (
    HEADLESS, TARGET_LEADS, SCREEN_TARGET, MAX_REVIEWS,
    CATEGORY_SEARCHES, STATES_DIR,
    OUTPUT_DIR, OUTPUT_XLSX, OUTPUT_CSV, OUTPUT_REVIEWS_CSV,
    MAX_PER_SEARCH,
)
from .models import Lead, Review
from .utils import delay, lead_slug, make_browser
from .maps import collect_place_urls, extract_lead, scrape_reviews
from .enrichment import find_social_media, enrich_from_social
from .photos import download_photos
from .email_finder import find_email
from .scoring import score_lead
from .export import save_excel, save_csv
from .db import save_crm


def _load_areas() -> list[str]:
    states_dir = Path(STATES_DIR)
    if not states_dir.exists():
        sys.exit(f"Error: '{STATES_DIR}' folder not found.")
    areas = []
    for state_file in sorted(states_dir.glob("*.csv")):
        state_code = state_file.stem.upper()
        with open(state_file, newline="", encoding="utf-8") as f:
            for row in csv.DictReader(f):
                city = (row.get("city") or row.get("City") or "").strip()
                if city:
                    areas.append(f"{city}, {state_code}")
    return areas


async def run(areas=None, categories=None, screen_target=None, target_leads=None):
    """Crawl + rank + enrich into the CRM.

    All args optional — when omitted, falls back to the config defaults so the
    bare `python run.py` keeps working. The Scrape tab passes explicit subsets.
      areas        : list of "City, ST" strings (default: every states/*.csv city)
      categories   : list of search terms       (default: CATEGORY_SEARCHES)
      screen_target: candidates to screen        (default: SCREEN_TARGET)
      target_leads : keepers to enrich           (default: TARGET_LEADS)
    """
    areas = areas if areas else _load_areas()
    if not areas:
        sys.exit(f"No cities found in '{STATES_DIR}/' folder.")

    category_terms = categories if categories else CATEGORY_SEARCHES
    target_leads = target_leads or TARGET_LEADS

    Path(OUTPUT_DIR).mkdir(exist_ok=True)
    photos_root = str(Path(OUTPUT_DIR) / "photos")
    screen_target = max(screen_target or SCREEN_TARGET, target_leads)

    print(f"Cities   : {len(areas)} loaded")
    print(f"Searches : {len(category_terms)} category terms x {MAX_PER_SEARCH} listings each")
    print(f"Screen   : {screen_target} candidates  ->  keep top {target_leads}")
    print(f"Filters  : skip active sites, chains, >{MAX_REVIEWS} reviews")
    print(f"Outputs  : {OUTPUT_DIR}/\n")

    candidates: list[Lead] = []
    seen_keys: set[str]    = set()

    async with httpx.AsyncClient(
        headers={"User-Agent": "Mozilla/5.0 (compatible; LeadScraper/6.0)"},
        verify=False,
        timeout=httpx.Timeout(15.0),
    ) as http_client:

        async with async_playwright() as pw:
            browser, page = await make_browser(pw, headless=HEADLESS)

            # ══════════════════════════════════════════════════════════════════
            #  PHASE 1 — SCREEN: build & score a candidate pool
            # ══════════════════════════════════════════════════════════════════
            print("=" * 60)
            print("PHASE 1 — screening candidates ...")
            print("=" * 60)

            # Round-robin by city: city is the outer loop, categories inner.
            # Each round visits every category once in the same city, inspecting
            # at most MAX_PER_SEARCH listings per slot (counting rejects so no
            # single category can dominate the candidate pool).
            categories = random.sample(category_terms, len(category_terms))
            shuffled_areas = random.sample(areas, len(areas))

            for area in shuffled_areas:
                if len(candidates) >= screen_target:
                    break

                for search_term in categories:
                    if len(candidates) >= screen_target:
                        break

                    print(f"\n[screen {len(candidates)}/{screen_target}] '{search_term}' in {area}")

                    try:
                        place_urls = await collect_place_urls(page, search_term, area)
                    except Exception as e:
                        print(f"  collect error: {e}")
                        try:
                            await browser.close()
                        except Exception:
                            pass
                        browser, page = await make_browser(pw, headless=HEADLESS)
                        await delay(3, 5)
                        continue

                    print(f"  {len(place_urls)} listings found")

                    inspected = 0
                    for i, url in enumerate(place_urls):
                        if inspected >= MAX_PER_SEARCH or len(candidates) >= screen_target:
                            break
                        inspected += 1  # count every listing, pass or fail

                        try:
                            lead = await extract_lead(page, url, area, http_client)
                            if not lead:
                                continue

                            key = lead_slug(lead.business_name, lead.address)
                            if key in seen_keys:
                                print(f"      dup -- {lead.business_name}")
                                continue
                            seen_keys.add(key)
                            lead.slug = key

                            # Cheap signals only — no downloads, no deep search.
                            # Pass any social URL Maps already gave us (its
                            # "website" link) so find_social_media keeps it and
                            # only searches for the missing platform.
                            lead.facebook_url, lead.instagram_url = \
                                await find_social_media(
                                    page, lead.business_name, area, http_client,
                                    known_facebook=lead.facebook_url,
                                    known_instagram=lead.instagram_url,
                                )
                            # If a social URL was found it already passed the name
                            # check inside find_social_media, so its logo is safe.
                            lead.logo_verified = bool(lead.facebook_url or lead.instagram_url)
                            await enrich_from_social(lead, http_client)

                            lead.score = score_lead(lead)
                            candidates.append(lead)

                            tag = "NO SITE" if "No website" in lead.lead_reason else "OUTDATED"
                            print(f"      + [{lead.score:>3}] [{tag}] {lead.business_name}")

                        except Exception as e:
                            err = str(e)
                            if any(s in err for s in ("TargetClosedError", "Target closed", "Browser closed")):
                                print(f"  [{i+1}] browser crashed -- restarting")
                                try:
                                    await browser.close()
                                except Exception:
                                    pass
                                browser, page = await make_browser(pw, headless=HEADLESS)
                            else:
                                print(f"  [{i+1}] error: {e}")

                        await delay(2, 4)

                    await delay(3, 5)

            # ══════════════════════════════════════════════════════════════════
            #  RANK
            # ══════════════════════════════════════════════════════════════════
            candidates.sort(key=lambda l: l.score, reverse=True)
            keepers = candidates[:target_leads]

            print(f"\n{'='*60}")
            print(f"RANKED {len(candidates)} candidates -> enriching top {len(keepers)}")
            print("=" * 60)

            # ══════════════════════════════════════════════════════════════════
            #  PHASE 2 — ENRICH keepers (photos, reviews, email)
            # ══════════════════════════════════════════════════════════════════
            all_reviews: list[Review] = []
            for n, lead in enumerate(keepers, 1):
                lead.business_id = f"BIZ_{n:03d}"   # number only keepers — no gaps
                print(f"\n[{n}/{len(keepers)}] {lead.business_id} [{lead.score}] {lead.business_name}")

                try:
                    await download_photos(page, lead, http_client, photos_root)

                    revs = await scrape_reviews(page, lead)
                    all_reviews.extend(revs)

                    lead.email = await find_email(
                        page, lead.business_name, lead.area,
                        lead.website_url, lead.facebook_url, http_client,
                    )

                    # Final score now that email + photos are known.
                    lead.score = score_lead(lead)

                    print(
                        f"      [+] [{lead.score}] {lead.email or 'no email'} | "
                        f"{lead.photo_count} photos | {len(revs)} reviews"
                    )

                except Exception as e:
                    err = str(e)
                    if any(s in err for s in ("TargetClosedError", "Target closed", "Browser closed")):
                        print(f"      browser crashed -- restarting")
                        try:
                            await browser.close()
                        except Exception:
                            pass
                        browser, page = await make_browser(pw, headless=HEADLESS)
                    else:
                        print(f"      enrich error: {e}")

                await delay(2, 4)

            try:
                await browser.close()
            except Exception:
                pass

    if not keepers:
        print("\nNo leads found. Set HEADLESS=False in config.py to debug.")
        return

    # ══════════════════════════════════════════════════════════════════════════
    #  SAVE — raw snapshot (overwritten) + persistent CRM (merged)
    # ══════════════════════════════════════════════════════════════════════════
    print(f"\n{'='*60}")
    print(f"Saving {len(keepers)} leads + {len(all_reviews)} reviews ...")
    save_excel(keepers, all_reviews, OUTPUT_XLSX)
    save_csv(keepers, all_reviews, OUTPUT_CSV, OUTPUT_REVIEWS_CSV)
    save_crm(keepers)

    no_site  = sum(1 for l in keepers if "No website" in l.lead_reason)
    outdated = len(keepers) - no_site
    print("\nSummary:")
    print(f"  Screened      : {len(candidates)}")
    print(f"  Kept (top-N)  : {len(keepers)}")
    print(f"  No website    : {no_site}")
    print(f"  Outdated site : {outdated}")
    print(f"  With email    : {sum(1 for l in keepers if l.email)}")
    print(f"  With photos   : {sum(1 for l in keepers if l.photo_count)}")
    print(f"  Reviews       : {len(all_reviews)}")
    if keepers:
        print(f"  Score range   : {keepers[-1].score}–{keepers[0].score}")
