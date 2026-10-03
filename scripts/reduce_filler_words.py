#!/usr/bin/env python3
"""
Reduces the "real"/"actually"/"genuine" filler density across the question
bank, without eliminating it -- Andrew's explicit call: some uses are real
theological vocabulary (Real Presence, real distinction between essence and
existence, really distinct Persons), and some "actually" uses carry genuine
logical contrast. Deleting every occurrence would be wrong, not just risky.

SCOPE: only touches fields where real+actually+genuine combined appear 2 or
more times -- 1,845 of the bank's 10,457 text fields. The other 7,739 fields
(a single, natural-reading occurrence) are left completely alone. This
mirrors the actual problem: isolated uses mostly read fine; it's the
stacking ("real, careful, honest", "actually... real... actually") in the
same sentence that reads badly.

PROTECTED PHRASES, never touched regardless of field density (verified by
reading every real occurrence in the bank first -- see Claude's own
analysis, not guessed):
  - "Real Presence" / "real presence" / "really present"   (the Eucharist)
  - "really distinct"                                       (Trinity Persons,
                                                               essence/existence)
  - "real distinction between essence and existence"        (Metaphysics)
  - "real distinction of Persons"                            (Trinity)

Everything else matching these phrases is ordinary English, not technical
vocabulary -- including "real relationship" (just generic filler here, not
the Trinitarian "real relations" term, which doesn't actually appear in
this bank) and "real distinction" on its own (used generically throughout
Answering Objections/Apologetics for "a real, non-strawman distinction",
not the metaphysical term).

Run from the catechism-database directory: python3 scripts/reduce_filler_words.py
"""
import json
import os
import re

PROTECTED_PATTERNS = [
    re.compile(r'\breal presence\b', re.I),
    re.compile(r'\breally present\b', re.I),
    re.compile(r'\breally distinct\b', re.I),
    re.compile(r'\breal distinction between essence and existence\b', re.I),
    re.compile(r'\breal distinction of persons\b', re.I),
]

DENSITY_RE = re.compile(r'\b(real|actually|genuine)\b', re.I)


def protected_spans(text):
    spans = []
    for pat in PROTECTED_PATTERNS:
        for m in pat.finditer(text):
            spans.append((m.start(), m.end()))
    spans.sort()
    return spans


def apply_outside_protected(text, func):
    """Runs func(text) but re-stitches any protected span back verbatim,
    in case func's regexes would otherwise have touched it. We do this by
    running func on the whole string, then diffing character-for-character
    against the original within protected ranges and restoring them."""
    spans = protected_spans(text)
    if not spans:
        return func(text)
    # Mask protected spans with placeholder tokens that contain no
    # trigger words, run the real rules, then restore.
    placeholders = {}
    masked = text
    offset = 0
    pieces = []
    last = 0
    for i, (s, e) in enumerate(spans):
        pieces.append(text[last:s])
        token = f'\x00PROTECTED{i}\x00'
        placeholders[token] = text[s:e]
        pieces.append(token)
        last = e
    pieces.append(text[last:])
    masked = ''.join(pieces)
    result = func(masked)
    for token, original in placeholders.items():
        result = result.replace(token, original)
    return result


def field_density(text):
    return len(DENSITY_RE.findall(text))


def clean_text(text):
    t = text

    # Dedupe stacked intensifiers first (order matters -- most specific first)
    t = re.sub(r'\bgenuine,\s*real\b', 'genuine', t, flags=re.I)
    t = re.sub(r'\breal,\s*genuine\b', 'genuine', t, flags=re.I)
    t = re.sub(r'\breal and genuine\b', 'genuine', t, flags=re.I)
    t = re.sub(r'\bgenuine and real\b', 'genuine', t, flags=re.I)

    # "a real, <vowel-sound word>" -> "an <word>" -- the comma-stacked form
    # of the article fix (e.g. "a real, important point" -> "an important
    # point"), must run before the generic "real,\s*" strip below, which
    # would otherwise leave the wrong article ("a important").
    t = re.sub(r'\b([Aa]) real,\s*(?=[aeiouAEIOU])', lambda m: 'An ' if m.group(1) == 'A' else 'an ', t)

    # "a real <vowel-sound word>" -> "an <word>" (no comma -- "real" directly
    # modifies the next word). Must also run before the generic strip below.
    t = re.sub(r'\b([Aa]) real (?=[aeiouAEIOU])', lambda m: 'An ' if m.group(1) == 'A' else 'an ', t)

    # "a real <word>" -> "a <word>" (consonant case, article already correct)
    # -- same comma guard as above.
    t = re.sub(r'\b([Aa]) real\b(?!,)', lambda m: m.group(1), t)

    # "this real, X" -> "this X"  (e.g. "and this real, careful point matters")
    t = re.sub(r'\bthis real,\s*', 'this ', t, flags=re.I)
    t = re.sub(r'\bthe real,\s*', 'the ', t, flags=re.I)

    # ", real <word>" -> " <word>" -- the comma-BEFORE case (e.g. "a fixed,
    # real time" -> "a fixed time", "entire, real life" -> "entire life").
    # Without this, stripping bare "real " alone would leave the preceding
    # comma orphaned ("a fixed, time"). Must run before the generic bare
    # "real " strip below, which would otherwise hit this case first and
    # leave the comma behind.
    t = re.sub(r',\s*real\b\s*', ' ', t, flags=re.I)

    # Stacked "real, <adj>[, <adj>]" as a leading intensifier in a list ->
    # drop "real," and let the remaining adjectives stand
    t = re.sub(r'\breal,\s*', '', t, flags=re.I)

    # Remaining bare "real " directly modifying a noun with no comma (e.g.
    # "real certainty", "real objections", "a real part") -> drop it
    t = re.sub(r'\breal\s+', '', t, flags=re.I)

    # "actually" as a bare filler adverb immediately before a verb -- only
    # inside fields we've already decided are dense enough to touch. Keep
    # negated-contrast uses ("doesn't actually", "isn't actually", "wasn't
    # actually") since those are more often doing real logical work.
    t = re.sub(r'(?<!n\'t )(?<!not )\bactually\s+', '', t, flags=re.I)

    # Punctuation cleanup from the removals above: double commas, "a ,",
    # dangling ", ," sequences, double spaces, space-before-comma.
    t = re.sub(r',\s*,', ',', t)
    t = re.sub(r'\s+,', ',', t)
    t = re.sub(r',\s*--', ' --', t)
    t = re.sub(r'\s{2,}', ' ', t)
    t = re.sub(r'^,\s*', '', t)
    t = t.strip()

    return t


def clean_field(text):
    if field_density(text) < 2:
        return text, False
    new = apply_outside_protected(text, clean_text)
    # If the sentence-initial word itself was stripped (e.g. "Real, careful
    # listening..." -> "careful listening..."), the new first letter needs
    # re-capitalizing -- found by testing against 187 real fields where this
    # happened, not a hypothetical edge case.
    if new and text and text[0].isupper() and new[0].islower():
        new = new[0].upper() + new[1:]
    return new, (new != text)


def clean_pairs(pairs):
    changed = False
    for p in pairs:
        for side in ('left', 'right'):
            v = p.get(side)
            if isinstance(v, str):
                new, did = clean_field(v)
                if did:
                    p[side] = new
                    changed = True
    return changed


def clean_choices(choices):
    changed = False
    for i, c in enumerate(choices):
        if isinstance(c, str):
            new, did = clean_field(c)
            if did:
                choices[i] = new
                changed = True
    return changed


def main():
    total_fields_changed = 0
    total_questions_touched = 0
    for fname in sorted(os.listdir('topics')):
        if not fname.endswith('.json'):
            continue
        path = f'topics/{fname}'
        data = json.load(open(path, encoding='utf-8'))
        file_changed = False
        for q in data['questions']:
            q_changed = False
            for field in ('prompt', 'explanation', 'hint', 'correctAnswer'):
                v = q.get(field)
                if isinstance(v, str):
                    new, did = clean_field(v)
                    if did:
                        q[field] = new
                        q_changed = True
                        total_fields_changed += 1
            if isinstance(q.get('choices'), list):
                if clean_choices(q['choices']):
                    q_changed = True
            if isinstance(q.get('pairs'), list):
                if clean_pairs(q['pairs']):
                    q_changed = True
            if q_changed:
                total_questions_touched += 1
                file_changed = True
        if file_changed:
            with open(path, 'w', encoding='utf-8') as f:
                f.write(json.dumps(data, indent=2, ensure_ascii=False) + '\n')
            print(f'{fname}: updated')

    print(f'\nTotal questions touched: {total_questions_touched}')
    print(f'Total fields/choices/pairs changed: {total_fields_changed}')


if __name__ == '__main__':
    main()
