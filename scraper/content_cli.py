"""
Thin JSON CLI around the editable site content (Supabase
`cold_pitch.business_content`) — the row each public site renders.

This is how the site builder writes good content WITHOUT hand-written SQL. When
you build a business's design you also author its real content (menu, about,
hours you've confirmed, reviews) as `businesses/<slug>/content.json`, then push
it here. It upserts through pipeline/db.upsert_content, so it never clobbers an
owner's edits on a live ('active') row and never touches owner_email/site_status.

All data logic lives in pipeline/db.py; this is just transport. Requires
SUPABASE_URL + SUPABASE_SERVICE_ROLE_KEY in the environment (or a project-root
.env). Service-role, local/server only.

Usage
-----
  python content_cli.py get  <slug>                 # current row as JSON
  python content_cli.py set  <slug> --file <path>   # upsert from a JSON file
  python content_cli.py set  <slug> '<json>'        # upsert from inline JSON
  python content_cli.py set  <slug>                 # upsert from JSON on stdin

The JSON is an object of business_content columns (snake_case): business_name,
about, phone, email, address, hours (obj of mon..sun), holidays_note,
services ([{name,description,price}]), reviews ([{text,name,stars,date}]),
photo_hero_url, photo_gallery_urls ([...]), facebook_url, instagram_url, rating,
review_count. `slug` is taken from the argument; any slug in the JSON is ignored.
Only the keys you include are written — omit a field to leave it unchanged.
Everything prints JSON; errors go to stderr with a non-zero exit code.
"""
import json
import sys
from pathlib import Path

_SCRAPER_DIR = Path(__file__).resolve().parent
sys.path.insert(0, str(_SCRAPER_DIR))

from pipeline.db import get_content, upsert_content  # noqa: E402


def cmd_get(args: list) -> None:
    if not args:
        sys.exit("get: usage: get <slug>")
    rec = get_content(args[0])
    if rec is None:
        sys.exit(f"get: slug not found: {args[0]}")
    print(json.dumps(rec, default=str))


def cmd_set(args: list) -> None:
    if not args:
        sys.exit("set: usage: set <slug> [--file <path> | '<json>' | (stdin)]")
    slug = args[0]
    rest = args[1:]

    if "--file" in rest:
        i = rest.index("--file")
        try:
            raw = Path(rest[i + 1]).read_text(encoding="utf-8")
        except IndexError:
            sys.exit("set: --file needs a path")
        except OSError as e:
            sys.exit(f"set: cannot read file: {e}")
    elif rest:
        raw = rest[0]
    else:
        raw = sys.stdin.read()

    try:
        record = json.loads(raw)
    except json.JSONDecodeError as e:
        sys.exit(f"set: invalid JSON: {e}")
    if not isinstance(record, dict):
        sys.exit("set: JSON must be an object of columns")

    record["slug"] = slug          # the argument is authoritative
    upsert_content(record)
    print(json.dumps({"ok": True, "slug": slug}))


COMMANDS = {"get": cmd_get, "set": cmd_set}


def main() -> None:
    if len(sys.argv) < 2 or sys.argv[1] not in COMMANDS:
        sys.exit(f"usage: content_cli.py {{{'|'.join(COMMANDS)}}} ...")
    COMMANDS[sys.argv[1]](sys.argv[2:])


if __name__ == "__main__":
    main()
