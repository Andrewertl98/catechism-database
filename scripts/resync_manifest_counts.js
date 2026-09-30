// Recomputes manifest.json's per-topic-per-level questionCounts and the
// top-level totals.questions from the actual topic files -- needed after
// remove_next_level_questions.js deletes questions, since those counts were
// hand/generator-authored and don't update themselves.
//
// Run from the catechism-database directory: node scripts/resync_manifest_counts.js
const fs = require('fs');
const path = require('path');

const manifestPath = 'manifest.json';
const manifest = JSON.parse(fs.readFileSync(manifestPath, 'utf8'));

let totalQuestions = 0;
for (const topic of manifest.topics) {
  const data = JSON.parse(fs.readFileSync(topic.file, 'utf8'));
  const perLevel = {};
  for (const q of data.questions) {
    perLevel[q.level] = (perLevel[q.level] || 0) + 1;
  }
  const before = JSON.stringify(topic.questionCounts);
  const after = {};
  // Preserve level key order 1..levels rather than insertion order.
  for (let lvl = 1; lvl <= topic.levels; lvl++) {
    if (perLevel[lvl] !== undefined) after[String(lvl)] = perLevel[lvl];
  }
  topic.questionCounts = after;
  if (JSON.stringify(after) !== before) {
    console.log(`${topic.name}: recomputed (was ${before.length} chars, now ${JSON.stringify(after).length})`);
  }
  totalQuestions += data.questions.length;
}

const oldTotal = manifest.totals.questions;
manifest.totals.questions = totalQuestions;
console.log(`\ntotals.questions: ${oldTotal} -> ${totalQuestions}`);

fs.writeFileSync(manifestPath, JSON.stringify(manifest, null, 2) + '\n', 'utf8');
console.log('manifest.json updated.');
