#!/usr/bin/env python3
"""
validate.py -- Schema and content validator for the FIDES catechism-database.

Checks, for every file in topics/*.json (and, with the same citation rule,
seasonal/*.json against seasonal-schema.json -- see validate_seasonal):
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
SEASONAL_DIR = REPO_ROOT / "seasonal"
SEASONAL_SCHEMA_PATH = REPO_ROOT / "seasonal-schema.json"

# Citation types considered authoritative / Magisterial-level on their own.
# "church_father" is intentionally excluded: Church Fathers may supplement
# a question's citations but can never be the sole source, per product policy.
# "catechism" covers an approved catechism other than the CCC itself (the
# Baltimore Catechism, e.g.) -- an officially commissioned, hierarchically
# approved document, not one theologian's private writing, so it counts.
AUTHORITATIVE_CITATION_TYPES = {"ccc", "scripture", "council", "magisterial_document", "catechism"}

LEVELS = ["1", "2", "3", "4", "5"]

# The six doctrinally load-bearing topics hard-gated behind theological
# reviewer sign-off -- mirrors export_review_packet.py's HARD_GATED set. The
# gate itself is level-based, not whole-topic (see ContentDatabase.swift's
# hardGateAppliesFromLevel = 6): levels 1-5 of these topics shipped at
# launch and are already fully live, unreviewed L6+ is what's actually held
# back. miniGameEligible follows the same boundary -- L1-5 content from
# these topics is fine to tag (MINI-GAMES-SPEC.md explicitly names Heresies
# L1-5's Arianism/Docetism/iconoclasm as source material); L6+ is not,
# since a timed/binary format shouldn't surface content the app itself
# hasn't cleared for users yet.
HARD_GATED_TOPICS = {
    "dogmas-and-doctrine", "councils", "heresies",
    "apologetics", "answering-objections", "metaphysics",
}
HARD_GATE_APPLIES_FROM_LEVEL = 6

# multiple_choice/true_false feed the timed "Heresy or Orthodox" sort;
# matching_pairs feeds the untimed "Saint / Feast-Day," "Church Latin
# Match," and "Prayer Match" games. fill_blank feeds the untimed "Prayer
# Fill-In" game, added Sep 1, 2026 -- reciting a known prayer's missing
# word is real recall, not a reflex test, same "never timed" reasoning
# matching_pairs already established. The taxonomy's "timed/binary formats
# only for unambiguous propositions" restriction in MINI-GAMES-SPEC.md
# specifically targets the timed games (Heresy or Orthodox, Virtue or
# Vice) -- untimed factual pairing/recall doesn't carry the same "trains
# fast pattern-matching over real understanding" risk.
MINI_GAME_ELIGIBLE_TYPES = {"multiple_choice", "true_false", "matching_pairs", "fill_blank"}


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
    and the app services)."""
    citations = question.get("citations", [])
    if not any(c.get("type") in AUTHORITATIVE_CITATION_TYPES for c in citations):
        errors.append(
            f"{location}: question '{question.get('id', '?')}' has no authoritative "
            f"Magisterial citation (ccc / scripture / council / magisterial_document / catechism). "
            f"Church Fathers alone are not sufficient."
        )


def check_mini_game_eligibility(question: dict, file_slug: str, location: str, errors: list[str]) -> None:
    """miniGameEligible: true is only legal on multiple_choice/true_false
    questions outside the six hard-gated topics -- see MINI-GAMES-SPEC.md's
    content-type taxonomy and schema.json's field description."""
    if not question.get("miniGameEligible"):
        return
    if file_slug in HARD_GATED_TOPICS and question.get("level", 0) >= HARD_GATE_APPLIES_FROM_LEVEL:
        errors.append(
            f"{location}: question '{question.get('id', '?')}' has miniGameEligible: true "
            f"but is level {question.get('level')} of hard-gated topic '{file_slug}' -- "
            f"mini-game content can't come from a level still awaiting theological "
            f"reviewer sign-off (levels below {HARD_GATE_APPLIES_FROM_LEVEL} are fine)."
        )
    if question.get("type") not in MINI_GAME_ELIGIBLE_TYPES:
        errors.append(
            f"{location}: question '{question.get('id', '?')}' has miniGameEligible: true "
            f"but type '{question.get('type')}' -- only multiple_choice, true_false, "
            f"matching_pairs, and fill_blank are eligible for a mini-game."
        )


def check_accepted_answers(question: dict, location: str, errors: list[str]) -> None:
    """'acceptedAnswers' is a fill_blank-only convenience -- extra exact
    answers graded correct alongside 'correctAnswer'. It's meaningless on any
    other type, and an empty list is just noise."""
    if "acceptedAnswers" not in question:
        return
    qid = question.get("id", "?")
    if question.get("type") != "fill_blank":
        errors.append(
            f"{location}: question '{qid}' has 'acceptedAnswers' but type "
            f"'{question.get('type')}' -- the field only applies to fill_blank."
        )
    values = question.get("acceptedAnswers")
    if not isinstance(values, list) or not values or any(not str(v).strip() for v in values):
        errors.append(
            f"{location}: question '{qid}' has an empty or blank entry in "
            f"'acceptedAnswers' -- omit the field entirely if there are no alternates."
        )
    elif str(question.get("correctAnswer", "")).strip().lower() in {str(v).strip().lower() for v in values}:
        errors.append(
            f"{location}: question '{qid}' repeats its own correctAnswer in "
            f"'acceptedAnswers' -- correctAnswer is always accepted already."
        )


AUX_GAME_FILES = ("who-am-i.json", "guess-the-book.json", "jeopardy.json")


def _has_authoritative_citation(citations: list) -> bool:
    return any(c.get("type") in AUTHORITATIVE_CITATION_TYPES for c in (citations or []))


# The longest each season can run, in days -- a season's challenge needs at
# least this many levels to cover every year (Advent runs 22-28 days).
SEASON_MAX_DAYS = {"advent": 28, "christmas": 19, "lent": 46, "easter": 49}


def validate_seasonal(manifest: dict, seen_ids: dict[str, str], errors: list[str], warnings: list[str]) -> None:
    """seasonal/<season>.json: one season's general topic and daily challenge.

    Gated in the apps by manifest.json's seasonalVersion / seasonalFiles, so
    the two must agree with what is on disk. Same citation rule as topics/.
    """
    declared = list(manifest.get("seasonalFiles", []))
    on_disk = sorted(p.relative_to(REPO_ROOT).as_posix() for p in SEASONAL_DIR.glob("*.json")) if SEASONAL_DIR.is_dir() else []
    if declared and not manifest.get("seasonalVersion"):
        errors.append("manifest.json: seasonalFiles is set but seasonalVersion is missing")
    for name in sorted(set(declared) - set(on_disk)):
        errors.append(f"manifest.json: seasonalFiles lists '{name}', which does not exist")
    for name in sorted(set(on_disk) - set(declared)):
        warnings.append(f"{name}: not listed in manifest.json's seasonalFiles, so the apps will not load it")
    if not on_disk:
        return

    try:
        schema = load_json(SEASONAL_SCHEMA_PATH)
    except LoadError as e:
        errors.append(str(e))
        return

    for rel in on_disk:
        path = REPO_ROOT / rel
        try:
            data = load_json(path)
        except LoadError as e:
            errors.append(str(e))
            continue
        try:
            jsonschema.validate(instance=data, schema=schema)
        except jsonschema.exceptions.ValidationError as e:
            where = "/".join(str(p) for p in e.path) or "(root)"
            errors.append(f"{rel}: schema validation failed at {where} -- {e.message}")
            continue

        season = data["season"]
        if path.name != f"{season}.json":
            errors.append(f"{rel}: filename does not match its season '{season}'")

        topics = {t["slug"]: t for t in data["topics"]}
        kinds = sorted(t["kind"] for t in data["topics"])
        if kinds != ["challenge", "general"]:
            errors.append(f"{rel}: needs exactly one 'general' and one 'challenge' topic (found {kinds})")
        for slug, topic in topics.items():
            expected = season if topic["kind"] == "general" else f"{season}-challenge"
            if slug != expected:
                errors.append(f"{rel}: the {topic['kind']} topic must be '{expected}', not '{slug}'")
            numbers = [lv["level"] for lv in topic["levels"]]
            if numbers != list(range(1, len(numbers) + 1)):
                errors.append(f"{rel}: {slug} levels must be numbered 1..{len(numbers)} in order")
            if topic["kind"] == "challenge":
                if len(numbers) < SEASON_MAX_DAYS[season]:
                    warnings.append(
                        f"{rel}: {slug} has {len(numbers)} level(s); the longest {season} runs "
                        f"{SEASON_MAX_DAYS[season]} days, so some days would have no level"
                    )
                if data["anchoredTailLevels"] > len(numbers):
                    errors.append(f"{rel}: anchoredTailLevels exceeds the challenge's level count")
                for lv in topic["levels"]:
                    for field in ("reflection", "scripture", "saint"):
                        if field not in lv:
                            warnings.append(f"{rel}: {slug} level {lv['level']} has no '{field}' for its opening card")

        per_level: dict[tuple[str, int], int] = {}
        for q in data["questions"]:
            qid = q["id"]
            if qid in seen_ids:
                errors.append(f"{rel}: duplicate question id '{qid}' (already used in {seen_ids[qid]})")
            else:
                seen_ids[qid] = rel
            slug = q["topic"]
            if slug not in topics:
                errors.append(f"{rel}: question '{qid}' has topic '{slug}', which is not one of this file's topics")
                continue
            if not qid.startswith(f"{slug}-l{q['level']}-"):
                errors.append(f"{rel}: question id '{qid}' does not match its topic and level")
            if q["level"] > len(topics[slug]["levels"]):
                errors.append(f"{rel}: question '{qid}' is on level {q['level']}, which {slug} does not declare")
            check_citation_policy(q, rel, errors)
            check_accepted_answers(q, rel, errors)
            per_level[(slug, q["level"])] = per_level.get((slug, q["level"]), 0) + 1

        for slug, topic in topics.items():
            for lv in topic["levels"]:
                if per_level.get((slug, lv["level"]), 0) == 0:
                    errors.append(f"{rel}: {slug} level {lv['level']} has no questions")

def validate_fishing_verses(errors: list[str], warnings: list[str]) -> None:
    """fishing-verses.json, dove-verses.json, moses-verses.json and rosary-verses.json: the verses the arcade games reveal.

    Each entry is a Scripture text with its reference and a one-line note for the recap. The text must be an
    exact copy of the Douay-Rheims (see content-workflow tooling, which copies it by script); this check only
    guards the structure and obvious copy damage. Absent file is fine (the game then hides itself).
    """
    for name in ("fishing-verses.json", "dove-verses.json", "moses-verses.json", "rosary-verses.json"):
        _validate_verse_file(REPO_ROOT / name, name, errors)


def _validate_verse_file(path, name: str, errors: list[str]) -> None:
    if not path.exists():
        return
    try:
        data = load_json(path)
    except LoadError as e:
        errors.append(str(e))
        return
    seen: set[str] = set()
    verses = data.get("verses") if isinstance(data, dict) else None
    if not isinstance(verses, list) or not verses:
        errors.append(f"{name}: needs a non-empty 'verses' list")
        return
    for v in verses:
        vid = str(v.get("id", "")).strip()
        where = f"{name}:{vid or '?'}"
        if not vid:
            errors.append(f"{where}: verse is missing an 'id'")
        elif vid in seen:
            errors.append(f"{where}: duplicate id")
        seen.add(vid)
        for field in ("reference", "text", "note"):
            if not str(v.get(field, "")).strip():
                errors.append(f"{where}: missing '{field}'")
        text = str(v.get("text", ""))
        if "[" in text or "]" in text or "  " in text or text != text.strip():
            errors.append(f"{where}: text has copy damage (bracket, double space or stray whitespace)")

def validate_holyland(errors: list[str], warnings: list[str]) -> None:
    for name in ("holyland.json", "earlychurch.json"):
        validate_map_file(errors, warnings, name)


def validate_map_file(errors: list[str], warnings: list[str], name: str) -> None:
    """holyland.json / earlychurch.json: the pin-drop game's maps (Natural Earth, simplified) and their places.

    Each place needs an id, name, prompt, reference, text, note and coordinates inside the map box. The verse text is an exact
    Douay-Rheims copy made by the content tooling; this check only guards structure and obvious copy damage.
    Absent file is fine (the game then hides itself).
    """
    path = REPO_ROOT / name
    if not path.exists():
        return
    try:
        data = load_json(path)
    except LoadError as e:
        errors.append(str(e))
        return
    box = (data.get("map") or {}).get("bbox")
    if not (isinstance(box, list) and len(box) == 4 and box[0] < box[2] and box[1] < box[3]):
        errors.append(f"{name}: map.bbox needs west, south, east, north")
        return
    for key in ("land", "lakes", "rivers"):
        if not (data["map"].get(key)):
            errors.append(f"{name}: map.{key} is empty")
    if data.get("title") is not None and not str(data["title"]).strip():
        errors.append(f"{name}: title is blank")
    sc = data.get("scoring")
    if sc is not None:
        keys = ("spotOnKm", "veryCloseKm", "closeKm", "zeroKm")
        if not all(isinstance(sc.get(k), (int, float)) for k in keys) or not (0 < sc["spotOnKm"] <= sc["veryCloseKm"] <= sc["closeKm"] < sc["zeroKm"]):
            errors.append(f"{name}: scoring distances must grow: spotOnKm <= veryCloseKm <= closeKm < zeroKm")
    for lab in data["map"].get("labels") or []:
        if not str(lab.get("name", "")).strip() or not (box[0] <= lab.get("lon", 1e9) <= box[2] and box[1] <= lab.get("lat", 1e9) <= box[3]):
            errors.append(f"{name}: a map label is blank or outside the box")
    places = data.get("places")
    if not isinstance(places, list) or not places:
        errors.append(f"{name}: needs a non-empty 'places' list")
        return
    seen: set[str] = set()
    for p in places:
        pid = str(p.get("id", "")).strip()
        where = f"{name}:{pid or '?'}"
        if not pid:
            errors.append(f"{where}: place is missing an 'id'")
        elif pid in seen:
            errors.append(f"{where}: duplicate id")
        seen.add(pid)
        for field in ("name", "prompt", "reference", "text", "note"):
            if not str(p.get(field, "")).strip():
                errors.append(f"{where}: missing '{field}'")
        lat, lon = p.get("lat"), p.get("lon")
        if not (isinstance(lat, (int, float)) and isinstance(lon, (int, float))):
            errors.append(f"{where}: needs numeric lat and lon")
        elif not (box[0] <= lon <= box[2] and box[1] <= lat <= box[3]):
            errors.append(f"{where}: lies outside the map box")
        text = str(p.get("text", ""))
        if "[" in text or "]" in text or "  " in text or text != text.strip():
            errors.append(f"{where}: text has copy damage (bracket, double space or stray whitespace)")

def validate_aux_games(errors: list[str], warnings: list[str]) -> None:
    """Structural + citation checks for the standalone mini-game content
    files (Who Am I?, Guess the Book, Jeopardy). These live at the repo root,
    not in topics/, and are not questions -- but the same 'every item carries
    an authoritative Magisterial citation' rule applies. Absent files are
    fine (a build without that game just shows nothing)."""
    seen: dict[str, str] = {}

    def check_id(item_id: str, where: str) -> None:
        if not item_id:
            errors.append(f"{where}: item is missing an 'id'")
        elif item_id in seen:
            errors.append(f"{where}: duplicate id '{item_id}' (also in {seen[item_id]})")
        else:
            seen[item_id] = where

    # ── who-am-i.json ─────────────────────────────────────────────────────
    path = REPO_ROOT / "who-am-i.json"
    if path.exists():
        try:
            data = load_json(path)
        except LoadError as e:
            errors.append(str(e))
            data = None
        for item in (data or {}).get("items", []):
            qid = item.get("id", "")
            check_id(qid, f"who-am-i.json:{qid or '?'}")
            if item.get("answerKind") not in ("person", "thing"):
                errors.append(f"who-am-i.json:{qid}: answerKind must be 'person' or 'thing'")
            if not str(item.get("answer", "")).strip():
                errors.append(f"who-am-i.json:{qid}: missing 'answer'")
            clues = item.get("clues") or []
            if not (2 <= len(clues) <= 6) or any(not str(c).strip() for c in clues):
                errors.append(f"who-am-i.json:{qid}: 'clues' must be 2-6 non-empty strings (got {len(clues)})")
            if not _has_authoritative_citation(item.get("citations")):
                errors.append(f"who-am-i.json:{qid}: no authoritative Magisterial citation")

    # ── guess-the-book.json ──────────────────────────────────────────────
    path = REPO_ROOT / "guess-the-book.json"
    if path.exists():
        try:
            data = load_json(path)
        except LoadError as e:
            errors.append(str(e))
            data = None
        for item in (data or {}).get("items", []):
            qid = item.get("id", "")
            check_id(qid, f"guess-the-book.json:{qid or '?'}")
            if item.get("testament") not in ("OT", "NT"):
                errors.append(f"guess-the-book.json:{qid}: testament must be 'OT' or 'NT'")
            if not str(item.get("book", "")).strip():
                errors.append(f"guess-the-book.json:{qid}: missing 'book'")
            if not str(item.get("passage", "")).strip():
                errors.append(f"guess-the-book.json:{qid}: missing 'passage'")
            if not _has_authoritative_citation(item.get("citations")):
                errors.append(f"guess-the-book.json:{qid}: no authoritative Magisterial citation")

    # ── jeopardy.json ────────────────────────────────────────────────────
    path = REPO_ROOT / "jeopardy.json"
    if path.exists():
        try:
            data = load_json(path)
        except LoadError as e:
            errors.append(str(e))
            data = None
        for board in (data or {}).get("boards", []):
            bid = board.get("id", "?")
            check_id(bid, f"jeopardy.json:{bid}")
            cats = board.get("categories") or []
            if not cats:
                errors.append(f"jeopardy.json:{bid}: board has no categories")
            for cat in cats:
                ctitle = cat.get("title", "?")
                clues = cat.get("clues") or []
                if not clues:
                    errors.append(f"jeopardy.json:{bid}/{ctitle}: category has no clues")
                for clue in clues:
                    label = f"jeopardy.json:{bid}/{ctitle}/{clue.get('value', '?')}"
                    if not isinstance(clue.get("value"), int):
                        errors.append(f"{label}: 'value' must be an integer")
                    if not str(clue.get("clue", "")).strip():
                        errors.append(f"{label}: missing 'clue' text")
                    if not str(clue.get("answer", "")).strip():
                        errors.append(f"{label}: missing 'answer'")
                    if not _has_authoritative_citation(clue.get("citations")):
                        errors.append(f"{label}: no authoritative Magisterial citation")


def answer_length_tell(question: dict) -> tuple[str, int] | None:
    """Returns (question id, char gap) when a multiple_choice question's
    correct answer is both the single longest choice AND >=30% longer than
    the next-longest -- i.e. "pick the longest option" is a reliable shortcut
    past the theology. Returns None otherwise. Aggregated by the caller into
    one summary line rather than a warning per question: this is a systemic
    authoring pattern (see the app's known-bugs 1.8), not a set of outliers."""
    if question.get("type") != "multiple_choice":
        return None
    choices = question.get("choices") or []
    correct = question.get("correctAnswer")
    if len(choices) < 2 or correct not in choices:
        return None
    lengths = sorted((len(c) for c in choices), reverse=True)
    correct_len = len(correct)
    if correct_len < lengths[0] or lengths[0] == lengths[1] or lengths[1] == 0:
        return None
    if (correct_len - lengths[1]) / correct_len >= 0.30:
        return (question.get("id", "?"), correct_len - lengths[1])
    return None


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
    length_tells: list[tuple[str, int]] = []
    mc_total = 0

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
            check_mini_game_eligibility(q, file_slug, path.name, errors)
            check_accepted_answers(q, path.name, errors)

            mc_total += 1 if q.get("type") == "multiple_choice" else 0
            tell = answer_length_tell(q)
            if tell:
                length_tells.append(tell)

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

    validate_aux_games(errors, warnings)
    validate_seasonal(manifest, seen_ids, errors, warnings)
    validate_fishing_verses(errors, warnings)
    validate_holyland(errors, warnings)

    if length_tells and mc_total:
        worst = sorted(length_tells, key=lambda t: t[1], reverse=True)[:5]
        worst_str = ", ".join(f"{qid} (+{gap})" for qid, gap in worst)
        warnings.append(
            f"answer-length tell: {len(length_tells)} of {mc_total} multiple_choice questions "
            f"have the correct answer as the longest choice by 30%+ over the next-longest -- "
            f'"pick the longest" partly works. Systemic, not per-question; a distractor-padding '
            f"pass is tracked in the app's known-bugs 1.8. Worst offenders: {worst_str}."
        )

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
