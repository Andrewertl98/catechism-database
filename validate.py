#!/usr/bin/env python3
"""
validate.py -- Schema and content validator for the FIDES catechism-database.

Checks, for every file in topics/*.json:
  1. The file conforms to schema.json (structure, types, per-question-type
     shape, and the "at least one authoritative citation" rule).
  2. Every question's inline "topic" field matches the file's top-level
     "topic" field (defense in depth beyond what the schema alone enforces).
  3. Every question id is globally unique across the whole database.
  4. manifest.json's declared topics and question counts match reality
     (mismatches are warnings, not hard failures, so manifest.json can be
     regenerated rather than hand-edited without breaking CI).

Run locally:
    pip install jsonschema
    python validate.py

Run in CI:
    python validate.py --ci

Exits 0 on success, 1 on any validation failure.
"""

from __future__ import annotations

import argparse
import json
import sys
from pathlib import Path

try:
    import jsonschema
except ImportError:
    print("Missing dependency: pip install jsonschema", file=sys.stderr)
    sys.exit(1)

REPO_ROOT = Path(__file__).resolve().parent
SCHEMA_PATH = REPO_ROOT / "schema.json"
MANIFEST_PATH = REPO_ROOT / "manifest.json"
TOPICS_DIR = REPO_ROOT / "topics"

# Citation types considered authoritative / Magisterial-level on their own.
# "church_father" is intentionally excluded: Church Fathers may supplement
# a question's citations but can never be the sole source, per product policy.
AUTHORITATIVE_CITATION_TYPES = {"ccc", "scripture", "council", "magisterial_document"}

LEVELS = ["1", "2", "3", "4", "5"]


class LoadError(Exception):
    pass


def load_json(path: Path):
    try:
        with path.open("r", encoding="utf-8") as f:
            return json.load(f)
    except FileNotFoundError:
        raise LoadError(f"{path}: file not found")
    except json.JSONDecodeError as e:
        raise LoadError(f"{path}: invalid JSON -- {e}")


def check_citation_policy(question: dict, location: str, errors: list[str]) -> None:
    """Belt-and-suspenders check: schema.json's 'contains' clause already
    enforces this, but we re-check here with a friendlier error message,
    mirroring the project's defense-in-depth pattern used elsewhere
    (e.g. the orthodoxy anchor duplicated in both the Cloudflare Worker
    and ClaudeService)."""
    citations = question.get("citations", [])
    if not any(c.get("type") in AUTHORITATIVE_CITATION_TYPES for c in citations):
        errors.append(
            f"{location}: question '{question.get('id', '?')}' has no authoritative "
            f"Magisterial citation (ccc / scripture / council / magisterial_document). "
            f"Church Fathers alone are not sufficient."
        )


def main() -> None:
    parser = argparse.ArgumentParser(description="Validate the FIDES catechism-database.")
    parser.add_argument("--ci", action="store_true", help="CI-friendly output; same checks, exits non-zero on failure.")
    args = parser.parse_args()

    errors: list[str] = []
    warnings: list[str] = []

    try:
        schema = load_json(SCHEMA_PATH)
        manifest = load_json(MANIFEST_PATH)
    except LoadError as e:
        print(f"FATAL: {e}", file=sys.stderr)
        sys.exit(1)

    if not TOPICS_DIR.is_dir():
        print(f"FATAL: {TOPICS_DIR} does not exist", file=sys.stderr)
        sys.exit(1)

    manifest_slugs = {t["slug"] for t in manifest.get("topics", [])}
    seen_ids: dict[str, str] = {}
    actual_counts: dict[str, dict[str, int]] = {}

    topic_files = sorted(TOPICS_DIR.glob("*.json"))
    if not topic_files:
        errors.append(f"No topic files found in {TOPICS_DIR}")

    for path in topic_files:
        try:
            data = load_json(path)
        except LoadError as e:
            errors.append(str(e))
            continue

        try:
            jsonschema.validate(instance=data, schema=schema)
        except jsonschema.exceptions.ValidationError as e:
            where = "/".join(str(p) for p in e.path) or "(root)"
            errors.append(f"{path.name}: schema validation failed at {where} -- {e.message}")
            continue

        file_slug = data["topic"]
        if file_slug not in manifest_slugs:
            errors.append(f"{path.name}: topic '{file_slug}' is not listed in manifest.json")

        expected_filename = f"{file_slug}.json"
        if path.name != expected_filename:
            errors.append(f"{path.name}: filename does not match its topic '{file_slug}' (expected {expected_filename})")

        counts = actual_counts.setdefault(file_slug, {})
        for q in data["questions"]:
            qid = q["id"]

            if qid in seen_ids:
                errors.append(f"{path.name}: duplicate question id '{qid}' (already used in {seen_ids[qid]})")
            else:
                seen_ids[qid] = path.name

            if q.get("topic") != file_slug:
                errors.append(
                    f"{path.name}: question '{qid}' has topic '{q.get('topic')}', "
                    f"which does not match the file's topic '{file_slug}'"
                )

            check_citation_policy(q, path.name, errors)

            if not q.get("hint"):
                warnings.append(
                    f"{path.name}: question '{qid}' has no 'hint' field — the "
                    f"guide mascot will fall back to a generic hint for it."
                )

            level_key = str(q["level"])
            counts[level_key] = counts.get(level_key, 0) + 1

    # Cross-check manifest.json's declared counts against what's on disk.
    for topic in manifest.get("topics", []):
        slug = topic["slug"]
        declared = topic.get("questionCounts", {})
        actual = actual_counts.get(slug, {})
        for level in LEVELS:
            d = int(declared.get(level, 0))
            a = actual.get(level, 0)
            if d != a:
                warnings.append(
                    f"manifest.json: {slug} level {level} declares {d} question(s), "
                    f"but {a} were found in topics/{slug}.json"
                )

    for slug in sorted(manifest_slugs - set(actual_counts.keys())):
        warnings.append(f"manifest.json lists topic '{slug}' but topics/{slug}.json has no valid questions")

    if warnings:
        print("Warnings:")
        for w in warnings:
            print(f"  \u26a0 {w}")

    if errors:
        print("\nErrors:")
        for e in errors:
            print(f"  \u2717 {e}")
        print(f"\n{len(errors)} error(s), {len(warnings)} warning(s). Validation FAILED.")
        sys.exit(1)

    total = sum(sum(c.values()) for c in actual_counts.values())
    print(
        f"\n\u2713 All topic files valid. {total} question(s) across "
        f"{len(actual_counts)} topic file(s). {len(warnings)} warning(s)."
    )
    sys.exit(0)


if __name__ == "__main__":
    main()
