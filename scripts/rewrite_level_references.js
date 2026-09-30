// De-contextualizes the dominant "this level's own X" / "the previous
// level's own X" possessive framing in hint/explanation/prompt/left/right/
// correctAnswer fields, across every topic file. Andrew's report, Sep 30
// 2026: these read fine live in a graded level, but the SAME question drawn
// into Daily Mix (or a friend duel round) has no "this level" for the user
// to recall, so the hint/explanation becomes meaningless.
//
// Run this AFTER remove_next_level_questions.js (that script deletes the
// separate, genuinely-unanswerable "what does the next level cover"
// questions -- a different problem from this one).
//
// SAFE, MECHANICAL PART: "this level's own X" / "the previous level's own X"
// (and the same without "own") is a possessive qualifier before a real noun
// phrase -- replacing it with "the X" reads grammatically correctly in every
// sample checked ("Recall this level's own real, simplest definition of a
// virtue." -> "Recall the real, simplest definition of a virtue.") and loses
// no actual content, since the substantive fact/definition/citation stays.
//
// NOT SAFE, NOT TOUCHED: sentences where "this level"/"the previous level"/
// "next level" is the grammatical SUBJECT of a verb ("Consider what this
// level actually did with...") or where a question's entire content is
// built around curriculum structure itself (e.g. "What habit has this level
// established for this whole topic?", or "This app's own Apologetics topic
// already introduced..."). These need real authoring judgment -- rewording
// them mechanically risks either broken grammar or silently changing what's
// being asked. This script reports every remaining instance after the safe
// pass runs, file by file with the full field text, instead of guessing.
//
// Run from the catechism-database directory: node scripts/rewrite_level_references.js
const fs = require('fs');
const path = require('path');
const dir = 'topics';
const files = fs.readdirSync(dir).filter(f => f.endsWith('.json'));
const FIELDS = ['prompt', 'explanation', 'hint', 'correctAnswer'];

function applySafeRewrite(text) {
  if (!text) return text;
  // Longest/most-specific patterns first. Capitalization of the match is
  // preserved on the replacement ("This level's own" -> "The", "this
  // level's own" -> "the").
  const rules = [
    /\bthis level's own\b/gi,
    /\bthe previous level's own\b/gi,
    /\bprevious level's own\b/gi,
    /\bthis level's\b/gi,
    /\bthe previous level's\b/gi,
    /\bprevious level's\b/gi,
  ];
  let out = text;
  for (const re of rules) {
    out = out.replace(re, (match) => (match[0] === match[0].toUpperCase() ? 'The' : 'the'));
  }
  return out;
}

function fixPairs(pairs) {
  if (!Array.isArray(pairs)) return pairs;
  return pairs.map((p) => ({
    ...p,
    left: applySafeRewrite(p.left),
    right: applySafeRewrite(p.right),
  }));
}

function fixChoices(choices) {
  if (!Array.isArray(choices)) return choices;
  return choices.map((c) => applySafeRewrite(c));
}

let totalFieldsRewritten = 0;
const residual = []; // { file, id, field, text }

for (const file of files) {
  const filePath = path.join(dir, file);
  const data = JSON.parse(fs.readFileSync(filePath, 'utf8'));
  if (!Array.isArray(data.questions)) continue;

  let fileChanged = false;
  for (const q of data.questions) {
    for (const field of FIELDS) {
      if (typeof q[field] !== 'string') continue;
      const before = q[field];
      const after = applySafeRewrite(before);
      if (after !== before) {
        q[field] = after;
        fileChanged = true;
        totalFieldsRewritten++;
      }
    }
    if (Array.isArray(q.choices)) {
      const before = JSON.stringify(q.choices);
      q.choices = fixChoices(q.choices);
      if (JSON.stringify(q.choices) !== before) {
        fileChanged = true;
        totalFieldsRewritten++;
      }
    }
    if (Array.isArray(q.pairs)) {
      const before = JSON.stringify(q.pairs);
      q.pairs = fixPairs(q.pairs);
      if (JSON.stringify(q.pairs) !== before) {
        fileChanged = true;
        totalFieldsRewritten++;
      }
    }

    // Scan what's left, after the safe pass, for reporting only.
    const scanFields = { ...q };
    for (const field of FIELDS) {
      const val = scanFields[field];
      if (typeof val === 'string' && /this level|previous level|next level/i.test(val)) {
        residual.push({ file, id: q.id, field, text: val });
      }
    }
    if (Array.isArray(q.choices)) {
      q.choices.forEach((c, i) => {
        if (/this level|previous level|next level/i.test(c)) {
          residual.push({ file, id: q.id, field: `choices[${i}]`, text: c });
        }
      });
    }
    if (Array.isArray(q.pairs)) {
      q.pairs.forEach((p, i) => {
        if (/this level|previous level|next level/i.test(p.left)) {
          residual.push({ file, id: q.id, field: `pairs[${i}].left`, text: p.left });
        }
        if (/this level|previous level|next level/i.test(p.right)) {
          residual.push({ file, id: q.id, field: `pairs[${i}].right`, text: p.right });
        }
      });
    }
  }

  if (fileChanged) {
    fs.writeFileSync(filePath, JSON.stringify(data, null, 2) + '\n', 'utf8');
  }
}

console.log('Fields rewritten (safe possessive pass):', totalFieldsRewritten);
console.log('Residual instances needing manual review:', residual.length);
fs.writeFileSync(
  'residual_level_references.txt',
  residual.map((r) => `${r.file}  ${r.id}  [${r.field}]\n  ${r.text}\n`).join('\n'),
  'utf8',
);
console.log('Full list written to residual_level_references.txt -- review, then delete before committing.');
