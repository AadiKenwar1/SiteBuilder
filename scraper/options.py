"""
Dump the Scrape tab's dropdown options as JSON:

    { "states": [ { "code": "nj", "cities": ["Newark", ...] }, ... ],
      "categories": ["hair salon", "barbershop", ...] }

States + cities come from states/*.csv (same `city` column parse as
runner._load_areas); categories from config.CATEGORY_SEARCHES — so Python stays
the single source of truth. Used by the Next.js /api/scrape/options route.

    python options.py
"""
import csv
import json
import sys
from pathlib import Path

_SCRAPER_DIR = Path(__file__).resolve().parent
sys.path.insert(0, str(_SCRAPER_DIR))

from pipeline.config import STATES_DIR, CATEGORY_SEARCHES  # noqa: E402


def _states():
    states = []
    for state_file in sorted(Path(STATES_DIR).glob("*.csv")):
        cities = []
        with open(state_file, newline="", encoding="utf-8") as f:
            for row in csv.DictReader(f):
                city = (row.get("city") or row.get("City") or "").strip()
                if city:
                    cities.append(city)
        if cities:
            states.append({"code": state_file.stem.lower(), "cities": cities})
    return states


def main() -> None:
    print(json.dumps({"states": _states(), "categories": list(CATEGORY_SEARCHES)}))


if __name__ == "__main__":
    main()
