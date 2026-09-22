#!/usr/bin/env python3
"""
Tooling for the on-ramp expansion (see 'andrew to do/waiting on you.txt').

Two jobs:

  pool <topic-slug>     Dump the citations already shipped AND reviewed in the
                        live bank for that topic, so new questions are written
                        against real references instead of from memory.

  check <draft-file>    Verify a draft on-ramp file. Checks, in order:
                          1. provenance  -- every (type, reference) already
                             exists somewhere in the live bank
                          2. quote fidelity -- every supplied quote is
                             byte-identical to wording already reviewed
                          3. schema     -- required fields, id pattern,
                             per-type shape, elo range, authoritative citation
                          4. difficulty -- difficultyElo matches EloEngine's
                             own seed formula for the post-cutover level count
                          5. impact     -- expected score for a new user

Provenance and quote fidelity are the important ones: they are what caught a
reference written from recall (CCC 2796) and three drifted quotes in the
church-fathers prototype. Run `check` on every batch before it ships.
"""
import json, re, sys, os

HERE = os.path.dirname(os.path.abspath(__file__))
MANIFEST = os.path.join(HERE, 'manifest.json')

# EloEngine.swift -- keep in sync if those constants ever change.
DIFFICULTY_FLOOR, DIFFICULTY_CEILING = 850, 2500
FORMAT_MODIFIER = {'true_false': -50, 'multiple_choice': 0,
                   'matching_pairs': 40, 'fill_blank': 60}
STARTING_RATING = 1000
NEW_LEVELS = 3           # on-ramp levels added below each topic's current L1
# Full target shape per CURRICULUM-PLAN.md: 3 below + N existing + (N-1) bridging + 1 capstone.
def target_total(live_levels):
    return 2 * live_levels + 3
AUTHORITATIVE = {'ccc', 'scripture', 'council', 'magisterial_document', 'catechism'}
ID_RE = re.compile(r'^[a-z0-9]+(-[a-z0-9]+)*-l([1-9]|[12][0-9])-[0-9]{3}$')
# Topics that do not exist in the live bank yet, with their target level count.
NEW_TOPIC_LEVELS = {'old-testament': 23}
REQUIRED = ['id', 'topic', 'level', 'type', 'difficultyElo', 'prompt',
            'explanation', 'citations']


def load_manifest():
    with open(MANIFEST) as f:
        return json.load(f)


def live_bank():
    """(refs, quotes, levels_by_slug) from the shipped content."""
    m = load_manifest()
    refs, quotes = set(), {}
    levels = {t['slug']: t['levels'] for t in m['topics']}
    for t in m['topics']:
        with open(os.path.join(HERE, t['file'])) as f:
            for q in json.load(f)['questions']:
                for c in q.get('citations', []):
                    key = (c['type'], c['reference'])
                    refs.add(key)
                    if c.get('quote'):
                        quotes.setdefault(key, set()).add(c['quote'])
    return refs, quotes, levels


def seed(level, total_levels, kind):
    progress = (level - 1) / (total_levels - 1) if total_levels > 1 else 1.0
    base = DIFFICULTY_FLOOR + progress * (DIFFICULTY_CEILING - DIFFICULTY_FLOOR)
    return round(base + FORMAT_MODIFIER[kind])


def expected(rating, difficulty):
    return 1 / (1 + 10 ** ((difficulty - rating) / 400))


def cmd_pool(slug):
    m = load_manifest()
    entry = next((t for t in m['topics'] if t['slug'] == slug), None)
    if not entry:
        sys.exit(f'unknown topic: {slug}')
    total = target_total(entry['levels'])
    print(f'# {slug}: {entry["levels"]} live levels -> {total} after a '
          f'{NEW_LEVELS}-level on-ramp')
    print('# difficultyElo to use for the new levels:')
    for lvl in range(1, NEW_LEVELS + 1):
        vals = ', '.join(f'{k} {seed(lvl, total, k)}' for k in
                         ('multiple_choice', 'true_false', 'matching_pairs', 'fill_blank'))
        print(f'#   level {lvl}: {vals}')
    print()
    with open(os.path.join(HERE, entry['file'])) as f:
        qs = json.load(f)['questions']
    seen = {}
    for q in qs:
        for c in q.get('citations', []):
            seen.setdefault((c['type'], c['reference']), c.get('quote', ''))
    print(f'# {len(seen)} reviewed citations available in this topic:')
    for (t, r), quote in sorted(seen.items()):
        print(f'{t}|{r}|{quote}')


def cmd_check(path):
    with open(path) as f:
        draft = json.load(f)
    qs = draft['questions']
    slug = draft['topic']
    refs, quotes, levels = live_bank()
    total = (NEW_TOPIC_LEVELS[slug] if slug in NEW_TOPIC_LEVELS
             else target_total(levels[slug]))

    problems = []

    # 1. provenance. A CCC paragraph, council or magisterial document written from
    # memory is the dangerous case -- a wrong paragraph number is unverifiable by a
    # reader and corrodes the app's core promise. A new Scripture reference is a
    # normal part of building a new topic (chapter and verse are checkable against
    # any Bible), so it is surfaced for review rather than blocked.
    new_scripture = []
    for q in qs:
        for c in q['citations']:
            if (c['type'], c['reference']) not in refs:
                if c['type'] == 'scripture':
                    new_scripture.append(f"{q['id']}: {c['reference']}")
                else:
                    problems.append(f"PROVENANCE {q['id']}: '{c['reference']}' ({c['type']}) "
                                    f"is not cited anywhere in the live bank -- "
                                    f"written from memory?")

    # 2. quote fidelity
    for q in qs:
        for c in q['citations']:
            key = (c['type'], c['reference'])
            if c.get('quote') and key in quotes and c['quote'] not in quotes[key]:
                problems.append(f"QUOTE DRIFT {q['id']}: wording for "
                                f"'{c['reference']}' differs from reviewed text")

    # 3. schema
    ids = set()
    for q in qs:
        for field in REQUIRED:
            if field not in q:
                problems.append(f"SCHEMA {q.get('id','?')}: missing '{field}'")
        if not ID_RE.match(q.get('id', '')):
            problems.append(f"SCHEMA {q.get('id','?')}: id fails schema pattern")
        if q['id'] in ids:
            problems.append(f"SCHEMA {q['id']}: duplicate id")
        ids.add(q['id'])
        if q.get('topic') != slug:
            problems.append(f"SCHEMA {q['id']}: topic field != file topic")
        if not 800 <= q.get('difficultyElo', 0) <= 2800:
            problems.append(f"SCHEMA {q['id']}: difficultyElo out of range")
        kind = q.get('type')
        if kind == 'multiple_choice':
            if 'choices' not in q or 'correctAnswer' not in q:
                problems.append(f"SCHEMA {q['id']}: multiple_choice needs choices + correctAnswer")
            else:
                if not 2 <= len(q['choices']) <= 6:
                    problems.append(f"SCHEMA {q['id']}: choice count out of range")
                if q['correctAnswer'] not in q['choices']:
                    problems.append(f"SCHEMA {q['id']}: correctAnswer is not one of the choices")
                if len(set(q['choices'])) != len(q['choices']):
                    problems.append(f"SCHEMA {q['id']}: duplicate choices")
        elif kind == 'true_false':
            if not isinstance(q.get('correctAnswer'), bool):
                problems.append(f"SCHEMA {q['id']}: true_false needs a boolean correctAnswer")
        elif kind == 'matching_pairs':
            if len(q.get('pairs', [])) < 2:
                problems.append(f"SCHEMA {q['id']}: matching_pairs needs at least 2 pairs")
            if 'correctAnswer' in q:
                problems.append(f"SCHEMA {q['id']}: matching_pairs must omit correctAnswer")
        elif kind == 'fill_blank':
            if not isinstance(q.get('correctAnswer'), str):
                problems.append(f"SCHEMA {q['id']}: fill_blank needs a string correctAnswer")
        else:
            problems.append(f"SCHEMA {q['id']}: unknown type '{kind}'")
        if 'hint' in q and len(q['hint']) < 10:
            problems.append(f"SCHEMA {q['id']}: hint shorter than schema minimum")
        if not any(c['type'] in AUTHORITATIVE for c in q['citations']):
            problems.append(f"CITATION {q['id']}: no authoritative citation "
                            f"(a Church Father alone is never sufficient)")

    # 4. difficulty
    for q in qs:
        if q.get('type') in FORMAT_MODIFIER:
            want = seed(q['level'], total, q['type'])
            if q.get('difficultyElo') != want:
                problems.append(f"DIFFICULTY {q['id']}: elo {q.get('difficultyElo')} "
                                f"but the seed formula says {want} (level {q['level']} of {total})")

    # answer-length tell -- the live bank already carries this warning, don't add to it
    tells = 0
    for q in qs:
        if q.get('type') == 'multiple_choice' and 'choices' in q:
            others = [c for c in q['choices'] if c != q.get('correctAnswer')]
            if others and len(q['correctAnswer']) > 1.3 * max(len(c) for c in others):
                tells += 1

    print(f'{os.path.basename(path)}: {len(qs)} questions, topic {slug} '
          f'({levels.get(slug, 0)} live levels -> {total})'
          + (' [NEW TOPIC]' if slug in NEW_TOPIC_LEVELS else ''))
    print()
    if problems:
        print(f'FAILED -- {len(problems)} problem(s):')
        for p in problems:
            print('  -', p)
    else:
        print('PASSED -- provenance, quote fidelity, schema, and difficulty all clean.')
    print()
    for lvl in sorted({q['level'] for q in qs}):
        sub = [q for q in qs if q['level'] == lvl]
        avg = sum(q['difficultyElo'] for q in sub) / len(sub)
        exp = sum(expected(STARTING_RATING, q['difficultyElo']) for q in sub) / len(sub)
        print(f'  level {lvl}: {len(sub):>2} questions | avg elo {avg:>6.0f} | '
              f'new-user expected score {exp*100:>3.0f}%')
    if new_scripture:
        print(f'\n  {len(new_scripture)} new Scripture reference(s) introduced -- '
              f'legitimate for a new topic, but each quote must be checked against a '
              f'real translation before this ships:')
        for s in new_scripture:
            print(f'    {s}')
    if tells:
        print(f'\n  note: {tells} multiple_choice question(s) have the correct answer '
              f'as much the longest choice -- same tell the live bank is already '
              f'flagged for; worth padding distractors.')
    return 1 if problems else 0


if __name__ == '__main__':
    if len(sys.argv) < 3:
        sys.exit(__doc__)
    cmd, arg = sys.argv[1], sys.argv[2]
    if cmd == 'pool':
        cmd_pool(arg)
    elif cmd == 'check':
        sys.exit(cmd_check(arg))
    else:
        sys.exit(__doc__)
