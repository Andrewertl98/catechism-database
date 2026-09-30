// Removes questions whose prompt or explanation references "next level" --
// these ask the user to know what content a future level covers, which is
// not learnable/answerable from anything actually taught. Andrew's report,
// Sep 30 2026: "I got a question where it asked true or false what the next
// level is, I have no idea." Confirmed as a systemic template (332 across
// all 16 topics), not a one-off. Removing these; per-level pools have 10
// questions each, so this leaves at least 7 per affected level -- comfortably
// above the 5-question draw.
//
// Run from the catechism-database directory: node scripts/remove_next_level_questions.js
const fs = require('fs');
const path = require('path');
const dir = 'topics';
const files = fs.readdirSync(dir).filter(f => f.endsWith('.json'));

let totalRemoved = 0;
const removedIds = [];

for (const file of files) {
  const filePath = path.join(dir, file);
  const raw = fs.readFileSync(filePath, 'utf8');
  const data = JSON.parse(raw);
  if (!Array.isArray(data.questions)) {
    console.log('SKIP (unexpected shape):', file);
    continue;
  }
  const before = data.questions.length;
  const kept = [];
  for (const q of data.questions) {
    const promptHasNext = (q.prompt || '').toLowerCase().includes('next level');
    const explHasNext = (q.explanation || '').toLowerCase().includes('next level');
    if (promptHasNext || explHasNext) {
      removedIds.push(q.id);
      totalRemoved++;
    } else {
      kept.push(q);
    }
  }
  data.questions = kept;
  const after = kept.length;
  if (before !== after) {
    fs.writeFileSync(filePath, JSON.stringify(data, null, 2) + '\n', 'utf8');
    console.log(`${file}: ${before} -> ${after} (removed ${before - after})`);
  }
}

console.log('\nTotal removed:', totalRemoved);
fs.writeFileSync('removed_question_ids.txt', removedIds.join('\n') + '\n', 'utf8');
console.log('IDs written to removed_question_ids.txt -- review, then delete that file before committing.');
