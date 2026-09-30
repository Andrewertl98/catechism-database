// Applies hand-authored rewrites from fixes.json to the topic files. Part 2
// of the Sep 30 2026 content-reference cleanup -- unlike Part 1's mechanical
// possessive-drop pass, every entry in fixes.json is a real editorial
// rewrite (a human/Claude judgment call per instance), keyed by
// {topicFile: {questionId: {fieldPath: newText}}}.
//
// fieldPath is one of: prompt, explanation, hint, correctAnswer,
// "choices[N]", "pairs[N].left", "pairs[N].right" -- matching exactly how
// residual_level_references.txt names fields.
//
// Run from the catechism-database directory: node scripts/apply_fixes.js
const fs = require('fs');
const path = require('path');

const fixes = JSON.parse(fs.readFileSync('scripts/fixes.json', 'utf8'));

function setField(q, fieldPath, value) {
  const arrMatch = fieldPath.match(/^(choices|pairs)\[(\d+)\](?:\.(left|right))?$/);
  if (arrMatch) {
    const [, arrName, idxStr, side] = arrMatch;
    const idx = Number(idxStr);
    if (!Array.isArray(q[arrName]) || idx >= q[arrName].length) {
      throw new Error(`Bad array field ${fieldPath} on ${q.id}`);
    }
    if (side) {
      q[arrName][idx][side] = value;
    } else {
      q[arrName][idx] = value;
    }
    return;
  }
  if (!(fieldPath in q)) {
    throw new Error(`Field ${fieldPath} does not exist on ${q.id}`);
  }
  q[fieldPath] = value;
}

let totalFieldsApplied = 0;
let totalQuestionsTouched = 0;

for (const [file, questions] of Object.entries(fixes)) {
  const filePath = path.join('topics', file);
  const data = JSON.parse(fs.readFileSync(filePath, 'utf8'));
  const byId = new Map(data.questions.map((q) => [q.id, q]));

  for (const [qid, fields] of Object.entries(questions)) {
    const q = byId.get(qid);
    if (!q) {
      throw new Error(`Question ${qid} not found in ${file}`);
    }
    for (const [fieldPath, value] of Object.entries(fields)) {
      setField(q, fieldPath, value);
      totalFieldsApplied++;
    }
    totalQuestionsTouched++;
  }

  fs.writeFileSync(filePath, JSON.stringify(data, null, 2) + '\n', 'utf8');
  console.log(`${file}: ${Object.keys(questions).length} questions updated`);
}

console.log(`\nTotal: ${totalQuestionsTouched} questions, ${totalFieldsApplied} fields rewritten.`);
