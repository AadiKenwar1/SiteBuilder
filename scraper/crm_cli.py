"""
Thin JSON CLI around the CRM (Supabase `cold_pitch.leads`) so non-Python callers
— the Node intake server in ../intake — can read and write the single source of
truth without re-implementing the data logic.

All data logic lives in pipeline/db.py; this is just a transport layer. Requires
SUPABASE_URL + SUPABASE_SERVICE_ROLE_KEY in the environment (or a project-root
.env).

Usage
-----
  python crm_cli.py add  '<json>'                 # upsert one business
  python crm_cli.py list                          # curated rows as JSON
  python crm_cli.py get  <slug>                    # one full row as JSON
  python crm_cli.py set  <slug> <field> <value>   # set one column on one row
  python crm_cli.py delete <slug> [--keep-folder]  # remove row (+ its folder)

`add` accepts a JSON object on argv or on stdin. Keys are CRM column headers
(e.g. "Business Name", "Phone", "Site Slug"). It prints {"slug": "..."} so the
caller can record the merge key. Everything prints JSON; errors go to stderr
with a non-zero exit code.
"""
import json
import shutil
import sys
from pathlib import Path

_SCRAPER_DIR = Path(__file__).resolve().parent
sys.path.insert(0, str(_SCRAPER_DIR))

from pipeline.db import load_rows, get, upsert, set_field, delete  # noqa: E402
from pipeline.config import _PROJECT_ROOT                          # noqa: E402

# Columns surfaced to the intake table — the full CRM is ~20 wide; this keeps
# the manual-entry UI readable. "Slug" stays in so the UI can target PATCHes.
LIST_COLS = [
    "Status", "Score", "Business Name", "Business Type", "Area",
    "Phone", "Email", "Lead Reason", "Site Slug", "Preview URL", "Slug",
]


def _to_score(rec: dict) -> float:
    try:
        return float(rec.get("Score") or 0)
    except (TypeError, ValueError):
        return 0.0


def cmd_add(args: list) -> None:
    raw = args[0] if args else sys.stdin.read()
    record = json.loads(raw)
    if not record.get("Business Name"):
        sys.exit("add: 'Business Name' is required")
    print(json.dumps({"slug": upsert(record)}))


def cmd_list(_args: list) -> None:
    rows = sorted(load_rows().values(), key=_to_score, reverse=True)
    out = [{c: str(r.get(c, "") or "") for c in LIST_COLS} for r in rows]
    print(json.dumps(out))


def cmd_get(args: list) -> None:
    if not args:
        sys.exit("get: usage: get <slug>")
    rec = get(args[0])
    if rec is None:
        sys.exit(f"get: slug not found: {args[0]}")
    print(json.dumps(rec))


def cmd_set(args: list) -> None:
    if len(args) < 2:
        sys.exit("set: usage: set <slug> <field> <value>")
    slug, field = args[0], args[1]
    value = args[2] if len(args) > 2 else ""
    if not set_field(slug, field, value):
        sys.exit(f"set: slug not found: {slug}")
    print(json.dumps({"ok": True}))


def cmd_delete(args: list) -> None:
    if not args:
        sys.exit("delete: usage: delete <slug> [--keep-folder]")
    slug = args[0]
    keep_folder = "--keep-folder" in args[1:]

    rec = delete(slug)
    if rec is None:
        sys.exit(f"delete: slug not found: {slug}")

    removed_folder = None
    if not keep_folder:
        site = (rec.get("Site Slug") or "").strip()
        if site:
            folder = _PROJECT_ROOT / "businesses" / site
            if folder.is_dir():
                shutil.rmtree(folder, ignore_errors=True)
                removed_folder = str(folder)
    print(json.dumps({"ok": True, "removed_folder": removed_folder}))


COMMANDS = {
    "add": cmd_add, "list": cmd_list, "get": cmd_get,
    "set": cmd_set, "delete": cmd_delete,
}


def main() -> None:
    if len(sys.argv) < 2 or sys.argv[1] not in COMMANDS:
        sys.exit(f"usage: crm_cli.py {{{'|'.join(COMMANDS)}}} ...")
    COMMANDS[sys.argv[1]](sys.argv[2:])


if __name__ == "__main__":
    main()
