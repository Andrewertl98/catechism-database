#!/usr/bin/env python3
"""Export a human-readable review packet for the theological reviewer.

The audit pipeline (sign_audit_manifest.swift -> manifest.json ->
AuditManifestVerifier in the app) already exists and is what actually gates
content in the app. What was missing was the front of that pipeline: a way to
hand a reviewer something they can actually read and mark up, rather than raw
JSON.

Usage
  python3 export_review_packet.py                     # every topic, all levels
  python3 export_review_packet.py --min-level 8       # only levels 8+
  python3 export_review_packet.py --topic heresies    # one topic
  python3 export_review_packet.py --gated-only        # only the six hard-gated topics
  python3 export_review_packet.py --unaudited-only    # skip anything already signed off

Writes one Markdown file per topic into review-packets/. Markdown so it opens
in anything, prints cleanly, and can be pasted into email or a doc without
losing structure.
"""

import argparse, json, glob, os, sys

# Mirrors Topic.hardGatedTopics in Saintly/Models/TopicCatalog.swift. Levels 6+
# in these topics are not served by the app until they are signed off, so they
# are the ones a reviewer's time should go to first.
HARD_GATED = {
    "dogmas-and-doctrine", "councils", "heresies",
    "apologetics", "answering-objections", "metaphysics",
}

TYPE_LABEL = {
    "multiple_choice": "Multiple choice",
    "true_false": "True / false",
    "matching_pairs": "Matching pairs",
    "fill_blank": "Fill in the blank",
}


def audited_ids():
    try:
        with open("manifest.json") as f:
            return set(json.load(f).get("auditedQuestionIDs") or [])
    except (OSError, ValueError):
        return set()


def render_citation(c):
    bits = [f"**{c.get('type','?')}** — {c.get('reference','(no reference)')}"]
    if c.get("quote"):
        bits.append(f"  > {c['quote']}")
    return "\n".join(bits)


def render_question(q, n):
    out = [f"### {n}. `{q['id']}`  ·  Level {q.get('level','?')}  ·  {TYPE_LABEL.get(q.get('type'), q.get('type','?'))}", ""]
    out.append(f"**Question.** {q.get('prompt','(no prompt)')}")
    out.append("")

    if q.get("choices"):
        out.append("**Answer options.**")
        for ch in q["choices"]:
            mark = "✓" if ch == q.get("correctAnswer") else " "
            out.append(f"- [{mark}] {ch}")
        out.append("")
    elif q.get("correctAnswer") is not None:
        out.append(f"**Correct answer.** {q['correctAnswer']}")
        out.append("")

    if q.get("pairs"):
        out.append("**Pairs.**")
        for p in q["pairs"]:
            out.append(f"- {p.get('left','?')} → {p.get('right','?')}")
        out.append("")

    if q.get("explanation"):
        out.append(f"**Explanation shown to the user.** {q['explanation']}")
        out.append("")
    if q.get("hint"):
        out.append(f"**Hint.** {q['hint']}")
        out.append("")

    cites = q.get("citations") or []
    out.append("**Citations.**" if cites else "**Citations.** _(none — this is a validation error)_")
    for c in cites:
        out.append(render_citation(c))
    out.append("")
    out.append("**Reviewer verdict:**  ☐ Approved   ☐ Approved with change (note below)   ☐ Rejected")
    out.append("")
    out.append("> _Notes:_")
    out.append("")
    out.append("---")
    out.append("")
    return "\n".join(out)


HEADER = """# Review packet — {title}

**Questions in this packet:** {count} (levels {levels})

## What we are asking

Please check each question below for **doctrinal accuracy** and for whether the
**citation actually supports** what the question and explanation claim. A question
can be factually true and still be wrong for our purposes if the citation does not
carry the claim.

For each question, tick one of the three verdicts and add a note where useful.
Anything you mark Rejected or Approved-with-change will be revised and sent back
to you — nothing goes into the app on a maybe.

## What happens to your answers

Only questions you approve get marked audited and served in the app. The six
doctrinally load-bearing topics are hard-gated in code: their harder levels are
literally not shown to any user until your sign-off is recorded. That gate is
enforced by a signature check in the app, not by a flag in a file, so it cannot be
set by accident.

Please reply to the email this came attached to with your verdicts — a written
reply from you is the record of the review, and it gets archived alongside the
content. The technical signature only proves the repository owner marked something
audited; your email is what proves a theologian actually read it.

---

"""


def main():
    ap = argparse.ArgumentParser()
    ap.add_argument("--topic", help="single topic slug, e.g. heresies")
    ap.add_argument("--min-level", type=int, default=1)
    ap.add_argument("--gated-only", action="store_true",
                    help="only the six topics hard-gated in the app")
    ap.add_argument("--unaudited-only", action="store_true",
                    help="skip questions already signed off in manifest.json")
    ap.add_argument("--out", default="review-packets")
    args = ap.parse_args()

    already = audited_ids() if args.unaudited_only else set()
    os.makedirs(args.out, exist_ok=True)

    files = sorted(glob.glob("topics/*.json"))
    if not files:
        sys.exit("No topics/*.json found — run this from the catechism-database directory.")

    written = 0
    for path in files:
        with open(path) as f:
            data = json.load(f)
        slug = data.get("topic") or os.path.basename(path).replace(".json", "")
        if args.topic and slug != args.topic:
            continue
        if args.gated_only and slug not in HARD_GATED:
            continue

        qs = [q for q in data.get("questions", [])
              if q.get("level", 0) >= args.min_level and q.get("id") not in already]
        if not qs:
            continue
        qs.sort(key=lambda q: (q.get("level", 0), q.get("id", "")))

        levels = sorted({q.get("level", 0) for q in qs})
        title = slug.replace("-", " ").title()
        body = HEADER.format(
            title=title, count=len(qs),
            levels=f"{levels[0]}–{levels[-1]}" if len(levels) > 1 else str(levels[0]),
        )
        body += "".join(render_question(q, i) for i, q in enumerate(qs, 1))

        dest = os.path.join(args.out, f"{slug}.md")
        with open(dest, "w") as f:
            f.write(body)
        print(f"  {dest}  ({len(qs)} questions, levels {levels[0]}-{levels[-1]})")
        written += 1

    if not written:
        print("Nothing to export with those filters.")
    else:
        print(f"\n{written} packet(s) written to {args.out}/")


if __name__ == "__main__":
    main()
