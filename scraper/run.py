"""
Entry point. Run with:
    python run.py                                   # full crawl (config defaults)
    python run.py --state nj                        # whole state
    python run.py --state nj --cities "Newark,Edison" \
                  --categories "hair salon,barbershop" \
                  --screen-target 20 --target-leads 5

With no args it crawls every states/*.csv city and every CATEGORY_SEARCHES term
(today's behavior). The flags let the CRM Scrape tab run a filtered subset.
"""
import argparse
import asyncio
import csv
from pathlib import Path

from pipeline.config import STATES_DIR
from pipeline.runner import run


def _split(csv_str):
    """'a, b , c' -> ['a', 'b', 'c'] (drops blanks)."""
    if not csv_str:
        return None
    return [part.strip() for part in csv_str.split(",") if part.strip()] or None


def _state_cities(code: str):
    """All cities in states/<code>.csv (same `city` column parse as runner)."""
    path = Path(STATES_DIR) / f"{code.lower()}.csv"
    if not path.exists():
        raise SystemExit(f"No city file for state '{code}' (expected {path}).")
    cities = []
    with open(path, newline="", encoding="utf-8") as f:
        for row in csv.DictReader(f):
            city = (row.get("city") or row.get("City") or "").strip()
            if city:
                cities.append(city)
    return cities


def main() -> None:
    ap = argparse.ArgumentParser(description="Crawl + rank + enrich leads into the CRM.")
    ap.add_argument("--state", help="state code, e.g. nj (whole state unless --cities given)")
    ap.add_argument("--cities", help="comma-separated city names within --state")
    ap.add_argument("--categories", help="comma-separated business types")
    ap.add_argument("--screen-target", type=int, help="candidates to screen before ranking")
    ap.add_argument("--target-leads", type=int, help="keepers to fully enrich")
    args = ap.parse_args()

    if args.cities and not args.state:
        ap.error("--cities requires --state")

    # Build "City, ST" area strings (mirrors runner._load_areas formatting).
    # --state alone = every city in that state; --cities narrows it.
    areas = None
    if args.state:
        code = args.state.strip().upper()
        cities = _split(args.cities) or _state_cities(code)
        areas = [f"{city}, {code}" for city in cities]

    asyncio.run(run(
        areas=areas,
        categories=_split(args.categories),
        screen_target=args.screen_target,
        target_leads=args.target_leads,
    ))


if __name__ == "__main__":
    main()
