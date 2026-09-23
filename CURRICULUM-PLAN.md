# Curriculum plan: turning the question bank into a learning journey

Drafted Sep 22, 2026, after Andrew's direction: every topic should read as a
path that snowballs — from the easiest possible starting point, each level
building on the one before, up to the highest. Not a difficulty-sorted pile of
independent questions.

This file is the design artifact. It is meant to be reviewed *before* the
authoring happens, because reviewing 15 syllabi is a couple of hours and
reviewing 1,880 questions is not.

---

## What the analysis found (why this is a reorg, not an append)

Three separate problems, all confirmed against the live bank:

**1. There is almost no easy content.** Only 104 of 1,469 questions (7%) sit at
or below 1250 Elo. A new user starts rated 1000 and meets level-1 content
averaging 1193 — an expected score of 29%. Per topic that runs from 62%
(church-history) down to 8% (church-fathers). Wrong answers cost hearts, so
most topics lock a new user out on day one.

**2. The levels are not one ramp — they are two courses stitched together.**
Levels 1–5 climb from ~1200 to ~2670; level 6 then *drops* ~800 points to
~1780 and climbs again. In thirteen of fifteen topics, **level 5 is harder
than level 10.**

The cause is precise, not mysterious. Fitting every question back through
`EloEngine.seedDifficulty`, levels 1–5 imply a topic of ~4 levels while levels
6+ imply exactly the topic's current count. Levels 1–5 were authored when
topics had four or five levels total, spanning the whole 850→2500 range in
five steps, and were never recomputed when topics grew to 8–10. Levels 6–10
were authored correctly against the new count.

**3. The sequence has real content holes.** Church History spends levels 1–5 on
a survey (apostles → Nicaea → Trent → Vatican II) and levels 6–10 on a second,
deeper pass at the modern period. Read as a journey, the middle falls out:

| Subject | Questions in the bank |
|---|---|
| The Crusades | **0** |
| Charlemagne / the medieval empire | **0** |
| East–West Schism (1054) | 1 |
| Avignon / Great Western Schism | 2 |

Roughly a thousand years is almost absent. A difficulty-ordered bank never had
to notice; a journey does.

---

## Target structure

Per topic, where N is the current level count:

```
  3 new levels below the existing first level
+ N existing levels, re-sequenced into one chronological//conceptual path
+ N-1 new half-levels, one bridging each existing pair
+ 1 new capstone level above the current top
= 2N + 3 levels
```

| Current N | Topics | New levels each | After |
|---|---|---|---|
| 8 | councils, heresies | 11 | 19 |
| 9 | church-fathers, metaphysics, virtues-and-vices | 12 | 21 |
| 10 | the other ten topics | 13 | 23 |

**188 new levels. At 10 questions each, ~1,880 new questions.** Final bank
~3,349 questions, up from 1,469.

---

## Order of work

**Phase 1 — syllabi (design).** For each topic, an ordered list of every level:
its title, what it teaches, what it assumes from the level before, and which
existing questions map onto it. Cheap to review, and it is what makes the
questions a journey instead of 1,880 more isolated facts. A worked example for
Church History is below.

**Phase 2 — review.** Andrew signs off on the syllabi. Fixing a sequence here
costs minutes; fixing it after authoring costs weeks.

**Phase 3 — authoring.** Fill every level to 10 questions against the syllabus,
in `drafts/`, nothing live. Every batch passes `onramp_tool.py check`
(citation provenance, quote fidelity against reviewed text, schema, difficulty
against the seed formula). Four topics' on-ramps are already done this way.

**Phase 4 — cutover.** One deliberate migration, covered below.

---

## Blockers that must be cleared at cutover

- **`schema.json`'s question-id pattern only permits levels 1–10**
  (`^...-l(10|[1-9])-[0-9]{3}$`). Topics will reach 19–23 levels. The regex has
  to be widened before any of this can validate.
- **`HARD_GATE_APPLIES_FROM_LEVEL = 6`** in `validate.py` (and
  `ContentDatabase.hardGateAppliesFromLevel` in the app) is an absolute level
  number. Under the new numbering the same real content sits far higher; the
  constant has to move with it or gated material becomes visible.
- **Every question's `difficultyElo` must be recomputed** against its new level
  and its topic's new total. This is mechanical — the seed formula already
  spreads 850→2500 across any level count — and it is what finally removes the
  "level 5 harder than level 10" artifact.
- **Question ids must stay opaque and never be renumbered.** `MissedQuestion`
  review-queue records and `manifest.json`'s `auditedQuestionIDs` both
  reference them. An id reading `-l1-` for what is now level 4 is the correct
  outcome, not a bug.
- **Real users' saved progress needs migrating.** `TopicProgressRecord` stores
  completion by level number. Without a migration, everyone's history silently
  points at the wrong levels.
- **Android carries its own copy** of the seeding logic and the gate
  (`shared/.../elo/EloEngine.kt`). The content files are shared; the constants
  are not.

---

## Worked example — Church History, 23 levels

`[NEW]` = needs authoring. `[L#]` = existing level that maps here. The existing
ten levels keep their internal order but interleave chronologically, which is
what turns two parallel courses into one path.

| # | Level | Builds on |
|---|---|---|
| 1 | The Church begins — Jesus, Pentecost, the first community `[NEW]` | nothing assumed |
| 2 | The apostles and where they went `[NEW]` | 1 |
| 3 | Handing the faith on — the first bishops `[NEW]` | 2 |
| 4 | Peter and the apostolic Church `[L1]` | 3 |
| 5 | Life under Rome before Constantine `[NEW]` | 4 |
| 6 | Persecution, the martyrs, the first apologists `[L2]` | 5 |
| 7 | From persecution to legality — Constantine `[NEW]` | 6 |
| 8 | Nicaea and the age of the councils `[L3]` | 7 |
| 9 | Fathers, monks, and the Christian West `[NEW]` | 8 |
| 10 | Charlemagne and the medieval Church `[NEW — no coverage today]` | 9 |
| 11 | East and West divide — 1054 `[NEW — 1 question today]` | 10 |
| 12 | Crusades, universities, the friars `[NEW — no coverage today]` | 11 |
| 13 | Scholasticism and Aquinas `[L4 partial]` | 12 |
| 14 | Avignon, conciliarism, the eve of reform `[NEW — 2 questions today]` | 13 |
| 15 | The Reformation and the Council of Trent `[L4]` | 14 |
| 16 | Missions abroad — Ricci and the Chinese Rites `[L6 partial]` | 15 |
| 17 | Jansenism and the 17th–18th century disputes `[L6]` | 16 |
| 18 | Revolution, restoration, the modern state `[NEW]` | 17 |
| 19 | Pius IX, the Syllabus, the First Vatican Council `[L7 + L5 partial]` | 18 |
| 20 | Leo XIII, Americanism, the social question `[L7]` | 19 |
| 21 | The Church and the totalitarian century `[L8]` | 20 |
| 22 | The Second Vatican Council `[L5]` | 21 |
| 23 | Reading the council; the contemporary Church `[L9 + L10]` | 22 |

Note what the sequence exposes: **five of the thirteen new levels are subjects
the bank barely covers at all** (10, 11, 12, 14, and most of 18). Those are not
padding to hit a level count — they are the missing middle of Church history.

---

## Open questions for Andrew

1. **Topics without a natural chronology** — Prayer, Virtues and Vices,
   Metaphysics — need a *conceptual* spine instead (e.g. Prayer: what prayer is
   → its forms → the Our Father → difficulties → contemplative prayer). Worth
   confirming that reads right to you before all fifteen are drafted.
2. **Is 10 questions per level still the target** at 331 levels? That is what
   produces the ~1,880 figure. Eight per level would cut roughly 375 questions
   from the job.
3. **The two-course structure is currently deliberate** (survey, then advanced
   pass). Collapsing it into one chronological path is the right call for a
   journey, but it does mean a returning user's level 6 is not the level 6 they
   left.

---

## Decisions from Andrew, Sep 22, 2026

**Church History follows a timeline.** Confirmed — the 23-level syllabus above
is already built chronologically, and interleaving the current two courses is
what makes that possible.

**New topic: the Old Testament.** Checked against what exists before scoping
it, and it is a real gap rather than a split:

- `sacred-scripture` is meta-level — canon, inspiration, the senses of
  Scripture, Dei Verbum, textual criticism. It teaches how to read the Bible,
  not what is in it.
- Across the entire bank, **56 of 1,469 questions (4%)** even mention an Old
  Testament subject. Abraham, the Exodus, David, the prophets and the Psalms
  are effectively absent as content.

So this is additive. As a brand-new topic it has no existing levels to
re-sequence, which makes it the cleanest possible test of the journey format:
built as a timeline from the start, and a natural prequel to Church History.

Proposed spine (23 levels, to be filled out in the same format as Church
History above): creation and the first parents -> Noah and the covenant ->
Abraham -> Isaac, Jacob, and Joseph -> slavery in Egypt -> Moses and the
Exodus -> Sinai and the Law -> desert wandering -> Joshua and the conquest ->
the Judges -> Samuel and the first kings -> David -> Solomon and the Temple ->
the kingdom divides -> the northern prophets -> Assyria and the fall of Israel
-> Isaiah and Judah -> Jeremiah and the fall of Jerusalem -> the Exile ->
Ezekiel and Daniel -> return and rebuilding -> wisdom and the Psalms ->
waiting for the Messiah.

Adding a sixteenth topic is not content-only. It also needs:
- `schema.json`'s `topicSlug` enum extended
- a `manifest.json` entry
- `TopicCatalog.swift` -- palette, level names, mastery titles
- the Android equivalent in `shared/.../content/`
- both apps' topic counts, which appear in store listings and in-app copy

## Working order

One topic at a time, start to finish, and each completed topic becomes the
reference for the next -- its level titles, the shape of its bridging levels,
how tightly each level leans on the one before. Church History goes first
because it is the clearest timeline; the Old Testament follows as the first
topic built this way from nothing.

**Done, Sep 23, 2026: Church History (23 levels) and the Old Testament (23
levels).** Both drafted, verified, committed. Neither is live -- both await
reviewer sign-off before cutover, same as everything else in this file.

---

## Open question for Andrew: does a "journey" mean the same thing for every
remaining topic?

Church History and the Old Testament both had an obvious organizing axis --
real, external chronology. Most of the 13 topics still ahead don't:

| Topic | Natural axis? |
|---|---|
| Saints | Chronological is *possible* (early martyrs -> medieval founders -> mystics -> modern) but the live bank is currently organized by **theme**, not time -- L1 doctrine, L2 martyrs, L6 canonization process, L7 apologetics, L9-10 cross-topic synthesis. A timeline reorg would dissolve those thematic groupings. |
| Dogmas-and-doctrine, Metaphysics, Liturgy-and-mass, Sacred-scripture, Prayer, Virtues-and-vices, Church-latin | No real chronology at all -- these are conceptual. A "journey" here has to mean *conceptual* dependency (term before it's used, simple doctrine before the nuance built on it), which is a real design choice per topic, not a template that transfers from Church History. |
| Councils, Heresies | Are chronological in the current bank already (councils in session order, heresies roughly by era) -- likely the smoothest remaining reorgs. |
| Apologetics, Answering-objections | Scenario-based by design (a named objection per level); "journey" probably means objection-difficulty progression, not time or concept order. |
| Our-lady | Could go chronological through her own life (Annunciation -> Visitation -> ... -> Assumption -> modern apparitions/devotion) similar to a mini Church History. |

Church History and the Old Testament's syllabi were reviewed by Andrew before
authoring began (per this file's own stated process, "reviewing 15 syllabi is
a couple of hours and reviewing 1,880 questions is not"). Continuing on to
Saints (or any of the next 13) means picking a real organizing principle for
a topic that, in several cases, has no obvious one -- exactly the kind of call
this file exists to get reviewed *before* authoring, not after.

**Proposed for Saints specifically**, as the most natural next topic (least
conceptual, most reusable from Church History's own template): reorganize
chronologically -- early martyrs (Agnes, Lawrence, Perpetua & Felicity) ->
Church Fathers-era saints -> medieval founders (Benedict, Francis, Dominic)
-> mystics and Doctors (Teresa of Ávila, John of the Cross, Catherine of
Siena, Thérèse) -> modern saints (Kolbe, Teresa of Calcutta, Faustina,
Bakhita) -> a closing block folding in the current bank's canonization-process
and apologetics content (L6-L7 today) as the final third of the arc rather
than a separate thematic detour. This would take the existing 10 levels'
*content* and re-sequence it by era, the same move Church History's L1-L10
went through, rather than inventing new saints to research.

**Decided by Andrew, Sep 23, 2026:** chronological where a topic actually has
one; where it doesn't (prayer named explicitly as the clear case), fall back
to the *other* organizing principle this whole project has been about from
the start -- a real pedagogical progression, school-age understanding at
level 1 building step by step to genuinely complex material at the top, never
a plateau or a jump. "Building on a strong foundation is critical" -- his own
words, and the standard every remaining topic's syllabus gets held to,
chronological or not.

Per-topic axis, decided under that standard:
- **Chronological**: saints (by era, as proposed above), councils (already
  session-ordered), heresies (already roughly era-ordered), our-lady (through
  her own life, then apparitions/devotion history).
- **Conceptual/pedagogical** (school-age -> complex, term-before-use,
  simple-doctrine-before-its-nuance): dogmas-and-doctrine, metaphysics,
  liturgy-and-mass, sacred-scripture, prayer, virtues-and-vices, church-latin.
- **Scenario-difficulty** (already the right shape, just needs re-seeding and
  possibly reordering scenarios easiest-to-hardest): apologetics,
  answering-objections.

Authoring proceeds topic by topic under this standard. Saints goes next.

**Done, Sep 23, 2026: Saints (23 levels), following Church History and the
Old Testament.** Drafted, verified, committed. Chronological through level
19 (apostles to contemporary canonizations), then process/apologetics/
synthesis/capstone (20-23), mirroring Church History's own two-part shape.

---

## Worked example -- Councils, 19 levels (N=8 -> 2*8+3=19)

Councils is already close to chronological in the live bank -- levels 1-5
already move roughly forward in time, level 8 is a Trent deep-dive
duplicating level 4's own era, and levels 6-7 are meta (terminology,
apologetics). The reorg interleaves the Trent duplication into two full
levels and moves the meta content to the end, same shape as Saints.

| # | Level | Builds on |
|---|---|---|
| 1 | What makes a council ecumenical? `[L1 partial]` | nothing assumed |
| 2 | Nicaea I (325) -- the first council `[L1 partial]` | 1 |
| 3 | Constantinople I and Ephesus (381, 431) `[L1 partial]` | 2 |
| 4 | Chalcedon (451) -- completing the first four `[L1 partial]` | 3 |
| 5 | Constantinople II and III (553, 680-681) `[L2]` | 4 |
| 6 | Nicaea II (787) -- the icon controversy resolved `[L3 partial]` | 5 |
| 7 | Lyon II and Florence -- failed reunion attempts `[L3 partial]` | 6 |
| 8 | Lateran IV (1215) and the medieval councils `[NEW -- 1 line today]` | 7 |
| 9 | Trent begins -- Scripture, Tradition, justification `[L4 + L8 partial]` | 8 |
| 10 | Trent continues -- sacraments, the Mass, images `[L4 + L8 partial]` | 9 |
| 11 | Trent's long institutional legacy `[NEW]` | 10 |
| 12 | The long gap -- no council for three centuries `[NEW]` | 11 |
| 13 | Vatican I (1869-1870) `[L5 partial]` | 12 |
| 14 | The gap after Vatican I, and John XXIII's call `[NEW]` | 13 |
| 15 | Vatican II opens `[L5 partial]` | 14 |
| 16 | Vatican II's documents in depth `[NEW]` | 15 |
| 17 | Conciliar terminology -- canons, decrees, anathema sit `[L6]` | 16 |
| 18 | Answering objections about the councils `[L7]` | 17 |
| 19 | Capstone: all twenty-one councils as one continuous story | 18 |

Councils goes next after Saints, since it needs the least new research of
any remaining topic -- almost every level maps to existing, already-reviewed
content, with new levels filling two real, narrow gaps (Lateran IV, and the
long 1870-1962 silence between Vatican I and II).

**Done, Sep 23, 2026: Councils (19 levels), following Church History, the
Old Testament, and Saints.** Drafted, verified, committed. Chronological
through level 16 (Nicaea to Vatican II), then terminology/apologetics/
capstone (17-19), closing with the same "hermeneutic of reform" theme
Church History's and Saints' own capstones already established.

---

## Worked example -- Heresies, 19 levels (N=8 -> 2*8+3=19)

Heresies is the natural next topic -- structurally almost identical to
Councils (same 10-level live shape, same rough chronological spine in
levels 1-5, same meta levels 6-7 for precise terminology and live
apologetics scenarios), and it tells the *same* history from the opposite
side: not the council's answer, but the error's own logic and appeal.
Deliberately kept distinct from Councils rather than redundant with it.

| # | Level | Builds on |
|---|---|---|
| 1 | What is heresy? Distinguishing it from apostasy and schism `[L5 partial]` | nothing assumed |
| 2 | The earliest errors -- Simon Magus, Gnosticism, Docetism `[L1 partial]` | 1 |
| 3 | Marcion, Montanism, and early Trinitarian error (Modalism) `[L1 partial]` | 2 |
| 4 | Arianism and Nicaea's answer `[L1 + L2 partial]` | 3 |
| 5 | The Christological heresies -- Apollinarianism, Nestorianism, Eutyches, Monothelitism `[L2]` | 4 |
| 6 | Donatism -- does a minister's sin invalidate a sacrament? `[NEW, reusing L6 citations]` | 5 |
| 7 | Pelagianism and semi-Pelagianism `[NEW, reusing L6 citations]` | 6 |
| 8 | Iconoclasm and the Cathars `[L3 partial]` | 7 |
| 9 | The Waldensians, Wycliffe, and Hus `[L3 partial]` | 8 |
| 10 | The Reformation's core claims -- sola fide, sola scriptura `[L4 partial]` | 9 |
| 11 | The Reformation's other movements -- Anabaptists, Anglicanism, Zwingli `[L4 partial]` | 10 |
| 12 | Jansenism `[NEW, reusing L4/L6 citations]` | 11 |
| 13 | Modernism and Americanism `[L5 partial]` | 12 |
| 14 | Feeneyism and liberation theology's real excesses `[L5 partial]` | 13 |
| 15 | Modern relativism and Dominus Iesus `[L5 + L8 partial]` | 14 |
| 16 | Contemporary errors -- prosperity gospel, syncretism, presumption `[L8 partial]` | 15 |
| 17 | Precise conciliar-text terminology for these errors `[L6]` | 16 |
| 18 | Live apologetics -- recognizing these errors today `[L7]` | 17 |
| 19 | Capstone: heresy as the inverted mirror of orthodoxy | 18 |

**Done, Sep 23, 2026: Heresies (19 levels), following Church History, the
Old Testament, Saints, and Councils.** Drafted, verified, committed.
Chronological through level 16 (Simon Magus to today's live prosperity-
gospel and syncretism variants), then terminology/apologetics/capstone
(17-19) fully reusing the old live bank's levels 6-7, closing with heresy
named directly as the inverted mirror of orthodoxy -- the same history
Councils tells from the opposite side.

---

## Worked example -- Dogmas-and-doctrine, 23 levels (N=10 -> 2*10+3=23)

Dogmas-and-doctrine is a genuinely conceptual topic -- no real chronology,
per the standard Andrew confirmed Sep 23. The live bank's 10 levels already
have a real thematic order (Creed basics -> creation -> Christ -> grace and
sacraments -> last things -> Church -> Mary -> grace/merit precision ->
moral theology -> a Trinity/divinization capstone), but live level 1 opens
with fairly technical vocabulary (consubstantial, hypostatic union,
filioque) with no on-ramp beneath it, and there is no real level on Original
Sin at all -- a genuine gap, since grace and redemption only make full sense
once the need for them is established. The journey below fixes both: three
new foundational levels below the old bank's easiest content, the old bank's
10 levels resequenced by real conceptual difficulty rather than left in
their current order, a new bridging level after each one deepening or
motivating what comes next, and a new capstone naming dogma itself as a
gift rather than a cage.

| # | Level | Builds on |
|---|---|---|
| 1 | What is a dogma? Dogma, doctrine, and theological opinion; Scripture and Tradition as the sources of revelation, guarded by the Magisterium `[NEW]` | nothing assumed |
| 2 | God is one, and can be known by reason as well as by revelation -- the classic divine attributes `[NEW]` | 1 |
| 3 | The Fall and Original Sin -- why humanity needs a Redeemer `[NEW]` | 2 |
| 4 | Creation -- ex nihilo, providence, angels, and the human person as a unity of body and soul `[L2]` | 3 |
| 5 | Made in God's image: human dignity and the soul's own real capacity for God `[NEW bridging]` | 4 |
| 6 | The Incarnation and the Paschal Mystery -- God becomes man to save `[L3]` | 5 |
| 7 | Why the God-man? The real fittingness of the Incarnation for our redemption `[NEW bridging]` | 6 |
| 8 | Grace and the Sacraments -- how Christ's saving work reaches us today `[L4]` | 7 |
| 9 | The Church's sacramental economy: ex opere operato, and why that precision actually matters `[NEW bridging]` | 8 |
| 10 | The Trinity in precise terms -- Nicaea, Chalcedon, and the Church's technical vocabulary `[L1]` | 9 |
| 11 | Why the Church needed precise Trinitarian and Christological language at all `[NEW bridging]` | 10 |
| 12 | The Last Things -- death, particular judgment, purgatory, heaven, and hell `[L5]` | 11 |
| 13 | Hope and the Last Things: how real eschatology actually shapes how a Catholic lives `[NEW bridging]` | 12 |
| 14 | The Church -- her nature, marks, and real authority `[L6]` | 13 |
| 15 | The real limits and true meaning of papal infallibility `[NEW bridging]` | 14 |
| 16 | Mary -- the Marian dogmas and their real apologetic defense `[L7]` | 15 |
| 17 | Answering common real objections to Marian doctrine in actual conversation `[NEW bridging]` | 16 |
| 18 | Grace and merit in precise terms -- congruism, Bañezianism, and real theological debate within orthodoxy `[L8]` | 17 |
| 19 | What separates a real theological debate from a real heresy? `[NEW bridging, ties back to Heresies]` | 18 |
| 20 | Catholic moral theology -- conscience, the natural law, and Veritatis Splendor `[L9]` | 19 |
| 21 | Applying real moral theology to a genuinely hard real-life case `[NEW bridging]` | 20 |
| 22 | The Trinity, divinization, and why the whole of doctrine coheres as one real story `[L10]` | 21 |
| 23 | Capstone: dogma as a real gift, not a cage -- how doctrine protects the truths that make faith, hope, and love possible `[NEW]` | 22 |

**Done, Sep 23, 2026: Dogmas-and-doctrine (23 levels), following Church
History, the Old Testament, Saints, Councils, and Heresies.** Drafted,
verified, committed. Opens with three new foundational levels (what a
dogma is, God's oneness, the Fall) below the old bank's easiest content,
resequences the old bank's 10 levels by real conceptual difficulty with
a new bridging level after each one, and closes with a new capstone
naming dogma as a gift rather than a cage.

---

## Worked example -- Metaphysics, 21 levels (N=9 -> 2*9+3=21)

Metaphysics is another genuinely conceptual topic, no real chronology.
Its live bank is already unusually well-ordered thematically (being and
reason -> act/potency -> causality -> transcendentals -> natural
theology -> hylomorphism/divine simplicity -> the soul -> angels ->
philosophical schools), but live level 1 opens by blending genuinely
easy content (the basic principle of non-contradiction) with genuinely
advanced content (analogical predication, "Being itself") in the same
level -- exactly the plateau/jump Andrew's standard rules out. The
journey below fixes this with three new, genuinely easy foundational
levels below the current bank's floor, resequences the 9 old levels by
real conceptual difficulty, adds one new bridging level after most of
them (8 total, since 9 old levels have 8 real gaps between them), and
closes with a new capstone.

| # | Level | Builds on |
|---|---|---|
| 1 | What is metaphysics? Asking what is real, not just how it behaves `[NEW]` | nothing assumed |
| 2 | The principle of non-contradiction -- reasoning's own most basic law `[NEW, easier version of L1 partial]` | 1 |
| 3 | Cause and effect: why nothing real happens without a real cause `[NEW]` | 2 |
| 4 | The four causes, and Aquinas's argument from motion (the First Way) `[L3]` | 3 |
| 5 | From "it moves" to "it's caused": deepening the argument from motion `[NEW bridging]` | 4 |
| 6 | Act and potency -- what real change actually is `[L2]` | 5 |
| 7 | Why act and potency actually matter, beyond motion alone `[NEW bridging]` | 6 |
| 8 | The transcendentals -- Being, Unity, Truth, and Goodness `[L4]` | 7 |
| 9 | Evil as a real privation, not a real thing in its own right `[NEW bridging]` | 8 |
| 10 | Natural theology -- the Five Ways in full `[L5]` | 9 |
| 11 | What philosophy's own real proofs can and cannot reach, versus what revelation adds `[NEW bridging]` | 10 |
| 12 | Being and reason -- essence/existence, analogical language, Being itself `[L1]` | 11 |
| 13 | Why God is not "a being" but Being itself, more deeply considered `[NEW bridging]` | 12 |
| 14 | Hylomorphism and divine simplicity `[L6]` | 13 |
| 15 | Why prime matter can never really exist on its own `[NEW bridging]` | 14 |
| 16 | The soul as the substantial form of the body `[L7]` | 15 |
| 17 | Answering "isn't the soul just brain states?" in real conversation `[NEW bridging]` | 16 |
| 18 | Angels -- purely spiritual creatures `[L8]` | 17 |
| 19 | Why angels matter for understanding human nature by real contrast `[NEW bridging]` | 18 |
| 20 | Philosophical schools within Catholic orthodoxy -- Thomism, Scotism, and more `[L9]` | 19 |
| 21 | Capstone: metaphysics as the real study of what's actually real beneath appearances `[NEW]` | 20 |

**Done, Sep 23, 2026: Metaphysics (21 levels), following Church History,
the Old Testament, Saints, Councils, Heresies, and Dogmas-and-doctrine.**
Drafted, verified, committed. Opens with three new foundational levels
(what metaphysics asks, non-contradiction, causality) below the old
bank's easiest content, resequences the old bank's 9 levels by real
conceptual difficulty with a new bridging level after most of them, and
closes with a new capstone naming metaphysics as the real study of what
is actually real beneath appearances.

---

## Worked example -- Apologetics, 23 levels (N=10 -> 2*10+3=23)

Apologetics is scenario-based by design (per Andrew's own confirmed
standard), and its live bank is already unusually mature and well
sequenced -- basic definitions, Creed objections, sola scriptura,
historical/scientific objections, ecumenism, motives of credibility
with real multi-turn dialogue mechanics, more advanced dialogues,
classical-versus-cumulative-case method (already cross-linking to
Metaphysics), Newman's illative sense (already cross-linking to Church
History, Saints, and Metaphysics), and a real capstone tying the whole
topic together around 1 Peter 3:15. The journey below keeps that real
order intact, adding three new gentler foundational levels below the
current floor and a new bridging level after each old level, deepening
or extending its real content rather than repeating it.

| # | Level | Builds on |
|---|---|---|
| 1 | What is a real objection, and how should a Catholic actually respond to one? `[NEW]` | nothing assumed |
| 2 | The three real stages of apologetics -- listening, understanding, answering `[NEW]` | 1 |
| 3 | Why apologetics matters even for non-scholars -- an ordinary Catholic's own real calling `[NEW]` | 2 |
| 4 | Faith and reason as real partners; apologetics' own real definition and proper goal `[L1]` | 3 |
| 5 | Real objections to the Creed's most basic claims, before the fuller defense ahead `[NEW bridging]` | 4 |
| 6 | Defending the Creed -- the Trinity, the Resurrection, the virgin birth `[L2]` | 5 |
| 7 | What makes a real objection actually land, versus answering a mere caricature `[NEW bridging]` | 6 |
| 8 | Sola scriptura, and Scripture and Tradition together `[L3]` | 7 |
| 9 | Applying Scripture and Tradition to a genuinely new real moral question `[NEW bridging]` | 8 |
| 10 | Historical and scientific objections -- the canon, Constantine, evolution, evil `[L4]` | 9 |
| 11 | The real difference between "science can't settle this" and "this is therefore false" `[NEW bridging]` | 10 |
| 12 | Ecumenism and interreligious dialogue `[L5]` | 11 |
| 13 | Real dialogue held together with real truth, never collapsing into relativism `[NEW bridging]` | 12 |
| 14 | Motives of credibility, the bibliographical test, and real dialogue with Islam `[L6]` | 13 |
| 15 | Applying the bibliographical test to a fresh, real historical case `[NEW bridging]` | 14 |
| 16 | Advanced real dialogue -- Protestant objections, the canon, persuasion's real stages `[L7]` | 15 |
| 17 | Recognizing when a real conversation has actually reached its real limit `[NEW bridging]` | 16 |
| 18 | Classical versus cumulative-case apologetics, connecting to Metaphysics `[L8]` | 17 |
| 19 | Why the Church permits both real approaches without any real contradiction `[NEW bridging]` | 18 |
| 20 | Newman's illative sense and the full cumulative case, drawing on Church History, Saints, and Metaphysics `[L9]` | 19 |
| 21 | Building a real cumulative case of your own, step by step `[NEW bridging]` | 20 |
| 22 | Capstone: 1 Peter 3:15, gentleness and respect, tying this whole topic together `[L10]` | 21 |
| 23 | Capstone: apologetics as a real act of love, not conquest `[NEW]` | 22 |

**Done, Sep 23, 2026: Apologetics (23 levels), following Church History,
the Old Testament, Saints, Councils, Heresies, Dogmas-and-doctrine, and
Metaphysics.** Drafted, verified, committed. Kept the already-mature
live bank's own real order intact, adding three new gentler
foundational levels and a new bridging level after each old level that
deepens or extends its content, closing with a new capstone naming
apologetics as a real act of love, not conquest.

---

## Worked example -- Liturgy-and-mass, 23 levels (N=10 -> 2*10+3=23)

Liturgy-and-mass has a real, natural order already -- the Mass's own
actual sequence (basic structure -> Liturgy of the Word -> Liturgy of
the Eucharist), followed by the liturgical year, the sacraments,
precise Eucharistic-Prayer and canonical vocabulary, real objections,
and a comparative Eastern/Western depth arc closing in ressourcement
and a real capstone. This live bank is already unusually well
sequenced; the journey below keeps that real order fully intact, adding
three new gentler foundational levels (what liturgy even is, the Mass
as "source and summit" in simple first terms, a newcomer's own real
walk-through) below the current floor, and a new bridging level after
each old level, deepening its content rather than repeating it.

| # | Level | Builds on |
|---|---|---|
| 1 | What is liturgy? Why the Church worships through set, communal ritual `[NEW]` | nothing assumed |
| 2 | The Mass as "source and summit" -- a simple first look `[NEW]` | 1 |
| 3 | Walking into Mass for the first time -- what a newcomer actually sees `[NEW]` | 2 |
| 4 | Basic vocabulary and structure of the Mass `[L1]` | 3 |
| 5 | Why the Mass has two main parts, more deeply considered `[NEW bridging]` | 4 |
| 6 | The Liturgy of the Word `[L2]` | 5 |
| 7 | Why Scripture is proclaimed, not merely read privately, at Mass `[NEW bridging]` | 6 |
| 8 | The Liturgy of the Eucharist `[L3]` | 7 |
| 9 | Transubstantiation, more deeply considered -- what changes and what does not `[NEW bridging]` | 8 |
| 10 | The liturgical year `[L4]` | 9 |
| 11 | Why the Church needs a whole year, not only a weekly Mass, to tell the story `[NEW bridging]` | 10 |
| 12 | The seven sacraments, grouped and explained `[L5]` | 11 |
| 13 | How the other six sacraments actually relate back to the Mass itself `[NEW bridging]` | 12 |
| 14 | Precise Eucharistic Prayer and canonical vocabulary `[L6]` | 13 |
| 15 | Why this precision actually matters pastorally, not just academically `[NEW bridging]` | 14 |
| 16 | Real objections to the Mass, answered `[L7]` | 15 |
| 17 | A further real objection to the Mass, answered `[NEW bridging]` | 16 |
| 18 | Comparative depth -- the Roman Rite and the Byzantine Divine Liturgy `[L8]` | 17 |
| 19 | What this comparison teaches about liturgy's own real unity in diversity `[NEW bridging]` | 18 |
| 20 | Eastern Catholic Churches and the ressourcement principle `[L9]` | 19 |
| 21 | Applying ressourcement to one's own real understanding of the Mass `[NEW bridging]` | 20 |
| 22 | Capstone: everything this topic has built, resolved `[L10]` | 21 |
| 23 | Capstone: the Mass as heaven touching earth `[NEW]` | 22 |

**Done, Sep 23, 2026: Liturgy-and-mass (23 levels), following Church
History, the Old Testament, Saints, Councils, Heresies, Dogmas-and-
doctrine, Metaphysics, and Apologetics.** Drafted, verified, committed.
Kept the live bank's own already-natural order fully intact, adding
three new gentler foundational levels and a new bridging level after
each old level, closing with a new capstone naming the Mass as heaven
touching earth.

---

## Worked example -- Sacred-scripture, 23 levels (N=10 -> 2*10+3=23)

Sacred-scripture already has a real, natural order -- basic vocabulary
(canon, inspiration, inerrancy) -> Old Testament genres -> the Gospels
-> New Testament letters -> the senses of Scripture and interpretation
-> precise canon-history and textual-criticism vocabulary -> real
objections -> historical-critical method and interpretive schools ->
typology and cross-topic connections -> a textual-criticism capstone.
This live bank is already unusually mature; the journey below keeps
that real order fully intact, adding three new gentler foundational
levels (what the Bible actually is, why this app covers it, a real,
practical first guide to actually reading it) below the current floor,
and a new bridging level after each old level.

| # | Level | Builds on |
|---|---|---|
| 1 | What is the Bible, really? Basic real facts before technical vocabulary `[NEW]` | nothing assumed |
| 2 | Why this app covers Sacred Scripture as its own real topic `[NEW]` | 1 |
| 3 | A real, practical first guide to actually reading the Bible `[NEW]` | 2 |
| 4 | Canon, inspiration, and inerrancy `[L1]` | 3 |
| 5 | What inerrancy actually does and does not claim, more deeply considered `[NEW bridging]` | 4 |
| 6 | The Old Testament's own real genres -- Torah, prophets, wisdom `[L2]` | 5 |
| 7 | Why the Old Testament's own real genres actually matter for reading it well `[NEW bridging]` | 6 |
| 8 | The Gospels `[L3]` | 7 |
| 9 | Why four Gospels, not one -- what each real, distinct portrait actually adds `[NEW bridging]` | 8 |
| 10 | The New Testament letters `[L4]` | 9 |
| 11 | Reading a real New Testament letter as a real letter, not a list of proof-texts `[NEW bridging]` | 10 |
| 12 | The senses of Scripture and real interpretation `[L5]` | 11 |
| 13 | Applying the senses of Scripture to a real, familiar passage `[NEW bridging]` | 12 |
| 14 | Precise canon-history and textual-criticism vocabulary `[L6]` | 13 |
| 15 | Why this precision matters for an ordinary reader, not just scholars `[NEW bridging]` | 14 |
| 16 | Real objections to Scripture, answered `[L7]` | 15 |
| 17 | A further real objection to Scripture, answered `[NEW bridging]` | 16 |
| 18 | Historical-critical method and real interpretive schools `[L8]` | 17 |
| 19 | Why the Church permits more than one real interpretive school `[NEW bridging]` | 18 |
| 20 | Typology and this app's own real cross-topic connections `[L9]` | 19 |
| 21 | Finding a further real typological connection of one's own `[NEW bridging]` | 20 |
| 22 | Capstone: real textual-critical questions, honestly resolved `[L10]` | 21 |
| 23 | Capstone: Scripture as a real letter from God, addressed to the reader personally `[NEW]` | 22 |

Sacred-scripture goes next, since its live bank is already close to a
real, natural order and needs the least invention of any remaining
topic.

---

## Worked example -- Saints, 23 levels

`[NEW]` = needs authoring. `[L#]` = existing level that maps here (fully or
partially; where a level's own content spans centuries, e.g. old L3's mix of
Benedict/Francis/Dominic/Ignatius across a 900-year range, it splits across
two new levels by era, same as Church History's old L4/L5/L6/L7 did).

| # | Level | Builds on |
|---|---|---|
| 1 | What is a saint? Mary and John the Baptist `[L1 partial]` | nothing assumed |
| 2 | The apostles as the first witnesses `[NEW]` | 1 |
| 3 | Stephen and the earliest martyrs `[L2 partial]` | 2 |
| 4 | The age of the Roman martyrs -- Agnes, Lawrence, Sebastian, Perpetua & Felicity `[L2]` | 3 |
| 5 | The Desert Fathers and the birth of monasticism `[NEW]` | 4 |
| 6 | Doctors of the early Church as saints -- Augustine, Jerome, Ambrose `[NEW, reusing church-fathers citations]` | 5 |
| 7 | Benedict and Western monastic sainthood `[L3 partial]` | 6 |
| 8 | Francis, Clare, and Dominic -- the mendicant saints `[L3 partial]` | 7 |
| 9 | Catherine of Siena and the Avignon crisis `[L4 partial]` | 8 |
| 10 | Saints on the eve of the Reformation -- Joan of Arc `[NEW]` | 9 |
| 11 | The Counter-Reformation saints -- Ignatius, Teresa of Ávila, John of the Cross `[L3 + L4 partial]` | 10 |
| 12 | Thomas More, martyr of the English Reformation `[L8 partial]` | 11 |
| 13 | Missionary saints of the age of exploration -- Francis Xavier `[NEW, reusing church-history citation]` | 12 |
| 14 | Saints of charity in the age of reason -- Vincent de Paul, John Vianney `[NEW]` | 13 |
| 15 | Thérèse of Lisieux and the Little Way `[L4 partial]` | 14 |
| 16 | Missionary and founder saints of the 19th century `[NEW]` | 15 |
| 17 | Saints of the world wars -- Kolbe, Faustina `[L5 partial]` | 16 |
| 18 | Teresa of Calcutta and Josephine Bakhita `[L5 partial]` | 17 |
| 19 | Contemporary canonizations `[NEW]` | 18 |
| 20 | How the Church recognizes a saint -- the canonization process `[L6]` | 19 |
| 21 | Answering objections about the saints `[L7]` | 20 |
| 22 | The saints across history -- cross-topic synthesis `[L9]` | 21 |
| 23 | Capstone: hard and ambiguous cases `[L10]` | 22 |

The last four levels are deliberately meta rather than chronological, per
Andrew's standard above: once a learner has actually met saints across two
thousand years (levels 1-19), the topic shifts to *how the Church discerns
sainthood at all* (20), *defends the practice* (21), *synthesizes across the
whole timeline* (22), and *tests judgment on genuinely hard cases* (23) --
school-age concrete examples first, the abstract and contested questions only
once that foundation is real.
