#!/usr/bin/env python3
"""Mark reviewed content as audit_status: "audited" in bulk.

This is step 1 of the sign-off workflow described in sign_audit_manifest.swift's
header: that script reads each question's own `audit_status` field to decide
what goes into manifest.json's signed `auditedQuestionIDs` list. Hand-editing
JSON for dozens of questions per topic is exactly the kind of tedious, error-
prone step that gets skipped or fumbled under time pressure, so this script
does it in bulk instead.

Typical use, once the reviewer has actually approved a topic (or a specific
level range within it):

    python3 mark_audited.py --topic councils
    python3 mark_audited.py --topic dogmas-and-doctrine --min-level 8 --max-level 10
    python3 mark_audited.py --topic heresies --ids heresies-l8-003 heresies-l8-007

Then run sign_audit_manifest.swift (see its own header for the signing key
step) to actually sign manifest.json -- this script only sets the per-question
field; it does NOT touch manifest.json or the cryptographic signature at all,
on purpose, so marking content here can never by itself unlock anything in the
app. That separation is the whole point of the two-step design.

--dry-run prints what WOULD change without writing anything, for checking the
scope of a batch before committing to it.
"""
from __future__ import annotations

import argparse
import json
import sys
from pathlib import Path

REPO_ROOT = Path(__file__).resolve().parent


def load_manifest() -> dict:
    return json.loads((REPO_ROOT / "manifest.json").read_text(encoding="utf-8"))


def main() -> None:
    ap = argparse.ArgumentParser(description=__doc__, formatter_class=argparse.RawDescriptionHelpFormatter)
    ap.add_argument("--topic", required=True, help="Topic slug, e.g. councils")
    ap.add_argument("--min-level", type=int, default=1)
    ap.add_argument("--max-level", type=int, default=10)
    ap.add_argument("--ids", nargs="*", default=None,
                     help="Only mark these specific question IDs (overrides --min-level/--max-level)")
    ap.add_argument("--dry-run", action="store_true", help="Show what would change, write nothing")
    args = ap.parse_args()

    manifest = load_manifest()
    entry = next((t for t in manifest["topics"] if t["slug"] == args.topic), None)
    if entry is None:
        valid = ", ".join(sorted(t["slug"] for t in manifest["topics"]))
        print(f"Unknown topic slug '{args.topic}'. Valid slugs: {valid}", file=sys.stderr)
        sys.exit(1)

    path = REPO_ROOT / entry["file"]
    data = json.loads(path.read_text(encoding="utf-8"))

    id_filter = set(args.ids) if args.ids else None
    changed = []
    already = []
    for q in data["questions"]:
        if id_filter is not None:
            if q["id"] not in id_filter:
                continue
        elif not (args.min_level <= q["level"] <= args.max_level):
            continue

        if q.get("audit_status") == "audited":
            already.append(q["id"])
            continue
        changed.append(q["id"])
        if not args.dry_run:
            q["audit_status"] = "audited"

    if id_filter is not None:
        missing = id_filter - {q["id"] for q in data["questions"]}
        if missing:
            print(f"Warning: these IDs were not found in {entry['file']}: {sorted(missing)}", file=sys.stderr)

    label = "Would mark" if args.dry_run else "Marked"
    print(f"{label} {len(changed)} question(s) as audited in {args.topic}.")
    if already:
        print(f"({len(already)} already were audited, left unchanged.)")
    if changed:
        for qid in changed:
            print(f"  {qid}")

    if args.dry_run or not changed:
        return

    with open(path, "w", encoding="utf-8") as f:
        json.dump(data, f, indent=2, ensure_ascii=False)
        f.write("\n")

    print(f"\nWrote {path}.")
    print("Next: run sign_audit_manifest.swift to sign manifest.json for real -- see that")
    print("script's own header for the AUDIT_SIGNING_KEY step. This script alone changes")
    print("nothing about what the app actually unlocks.")


if __name__ == "__main__":
    main()
