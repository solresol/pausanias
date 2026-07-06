# MANTO network features for place survival: idea inventory and paper notes

Date: 2026-07-06. Companion to the "MANTO Place Survival Model" section of
`TODO.md`. This is the working inventory of network-analysis feature families
for predicting whether a place Pausanias describes survives, plus the
methodological guardrails any paper claim must pass. It extends Greta's
original theory: that the connectedness of a place — a large city nearby,
stories shared with neighbours through common mythic figures, or the same
pattern of action performed by distinct city-related figures — may be
predictive of abandonment.

## Status of Greta's core hypotheses

Already implemented in `manto_place_connectedness_features.py` (v1):

- Large city nearby: `has_large_place_neighbor`, `large_place_neighbor_count`,
  `large_place_max_degree`, `large_place_max_pagerank`.
- Shared stories through common figures: `shared_mythic_figure_*` counts.
- Same action pattern by distinct figures: `shared_action_*` counts, using the
  canonical action vocabulary (foundation, cult site, burial, games, ...).

Generic graph position is in `manto_place_network_features.py`: degree,
PageRank, betweenness, clustering, component/community size, high-centrality
neighbours.

Prior model runs (logistic regression, single train/test split) peaked at
0.922 balanced accuracy with connectedness features on combined MANTO+LLM
labels (649 samples) and 0.731 on MANTO-only labels. Treat those numbers with
caution until the guardrails below are in place.

## Feature families

### 1. Deeper position features (place graph)

- **k-core number.** Depth of embedding rather than raw tie count; a
  degree-10 node whose neighbours are all leaves is a lonely hub, a node in
  the 5-core is woven into the fabric. Arguably the best single formalization
  of "connectedness" in Greta's sense.
- **Hop distance to the nearest large place.** The v1 feature is binary and
  adjacency-only; distance-in-hops captures the gradient between "2 hops from
  Argos" and "6 hops from anything".
- **Local reach.** Number of places reachable within 2 and 3 hops.
- **Narrative redundancy.** Approximate count of node-disjoint paths from the
  place to its nearest large place: is the place tied into Greek myth by one
  story about one hero, or by several independent stories? Low redundancy =
  fragile narrative embedding.
- **Bridge dependence.** Fraction of a place's edges that are graph bridges.
- **Harmonic/closeness centrality** (average narrative distance to the whole
  network) — deferred; expensive at full-graph scale, and local reach is a
  serviceable proxy.
- **Burt's constraint / effective size** (brokerage vs closure) — proposed,
  not yet implemented.

### 2. Bipartite structure: places × figures

The v1 features count figures; they do not weigh which figures.

- **Figure ubiquity.** For each figure, count the places attached to it. Per
  place: mean/max ubiquity of its figures, count of *exclusive* figures
  (attested at no other place), count of panhellenic figures (top-quantile
  ubiquity). Two rival hypotheses fall out: "famous patrons help" vs "a
  unique local identity helps".
- **Kin-mediated place ties.** Two places whose founders are brothers are
  story-linked even with no shared figure. Count places connected via
  figure–kin–figure chains (son_of, daughter_of, twin_of, has_children_with,
  wife_of, ...). This encodes claimed genealogical alliance between
  communities — the diplomatic mythology cities used to maintain
  relationships.
- **Figure quality via global centrality** (PageRank/HITS of the figure in
  the full graph, propagated to the place) — proposed, not yet implemented.
- **Genealogical depth of founding heroes** (generations from a major god) —
  proposed, not yet implemented.

### 3. Story-profile / role equivalence

- **Action-profile vectors.** Each place as a vector over canonical actions;
  profile **entropy** (one-note "hero's tomb town" vs diversified portfolio)
  and **cosine similarity** to neighbours and to large places. Cosine to a
  large place with *distinct* figures is the vectorized version of Greta's
  "same pattern of action by distinct city-related figures".
- **Role archetypes.** Cluster the profile vectors into nameable place-types
  ("cult centre", "burial town", "foundation-story-only") — proposed.
- **Regular equivalence / blockmodelling** (RoleSim) as the formal version of
  shared-action patterns — proposed.
- **Negative-valence motifs.** Destruction/conquest/transformation edges as
  features. Caution: aetiological myths about why a place is empty are close
  to label leakage; report separately from the "fair" model.

### 4. Meso-scale: communities and roles

- **Cartographic roles (Guimerà–Amaral).** Within-community degree z-score ×
  participation coefficient: provincial hubs vs connector places. "Connector
  places survive; provincial places don't" would be a headline finding.
- **Community-level large-city test**: same story-community as a top place,
  even if not adjacent — softer version of the neighbour test.
- **Community survival rate** must be computed out-of-fold if ever used (label
  leakage).

### 5. Geography × network hybrids

MANTO place entities carry Pleiades IDs (~1,600 of ~2,370 for the current
release), and Pleiades provides representative coordinates.

- **Geographic distance to the nearest large place**, as the physical
  counterpart of the narrative version, and as a control so network features
  do not merely proxy for "is in the Argolid rather than inland Arcadia".
- **Localism of mythology.** Fraction of a place's narrative ties that are
  geographically nearby (25/50/100 km bands). Places whose stories plug them
  into distant panhellenic networks vs purely local story-webs.
- **Gravity-model residual** (over-connected for its geography) — proposed,
  not yet implemented.

### 6. Temporal layering

`manto_edges.evidence_latest_year` supports stratifying the pre-Pausanias
graph: archaic (≤ −480), classical (−479..−323), Hellenistic (−322..−31),
early imperial (−30..170). Features: per-stratum story counts, earliest/latest
attestation, attestation span, and **myth accretion** — was the place still
acquiring new stories near Pausanias's own era, or did its mythology fossilize
with the epic corpus? Cultural liveliness may predict physical survival better
than any static centrality.

## Methodological guardrails (pre-registration notes for the paper)

1. **The fame confound.** MANTO edge counts partly measure how much ancient
   literature discusses a place, and famous places survive. Every
   degree-flavoured feature is a fame proxy. Defenses:
   - A **fame baseline model** — Pausanias mention counts plus raw
     pre-Pausanias attestation volume, no structure — that the network
     features must beat before any structural claim is made.
   - **Null-model z-scores** — degree-preserving rewiring of the
     place–figure structure, so shared-figure counts become "more sharing
     than expected given how well-attested the place and its figures are".
2. **Leakage rules.** Keep the strict `is_pre_pausanias` edge filter for all
   model-facing features. Pausanias-included runs are leakage diagnostics
   only. Destruction-type edges and anything derived from survival labels
   (community survival rates, similarity-to-survivor-centroid) are reported
   separately or computed out-of-fold.
3. **Spatial autocorrelation.** Survival is regionally clustered. Use
   cross-validation rather than a single split, and check leave-one-region-out
   behaviour before claiming generalization; otherwise the model learns
   geography and dresses it up as network structure.
4. **Label quality.** MANTO-derived status labels are heuristic (absence of a
   negative phrase ≈ survives); the manual audit item in `TODO.md` gates any
   paper-grade claim. Report MANTO-only, LLM-only, and combined label runs
   side by side.
5. **Small-n honesty.** A few hundred labelled, linked places; logistic
   regression with standardized features and cross-validated estimates;
   prefer coefficient signs and stability over point accuracy.

## First results (2026-07-06 implementation pass)

Everything above except the items marked "proposed" was implemented and run
against MANTO release 19446255 (myth graph after bookkeeping exclusion: 7,275
nodes / 63,701 pre-Pausanias edges; place graph 2,370 nodes / 5,433 edges;
1,464 MANTO places carry Pleiades coordinates).

**Evaluation regimes.** The MANTO-derived label set is 872:9 in favour of
`survives` — effectively degenerate — and the MANTO+LLM "combined" set is
639:11. The passage/sentence LLM label set is balanced (84 survives : 68
does_not_survive, n=152 linked places) and is the evaluation that means
anything. All numbers below are pooled out-of-fold balanced accuracy from
stratified 5-fold CV on that set.

| feature family | balanced accuracy |
| --- | --- |
| geography only | 0.583 |
| **fame baseline** (mentions + attestation volume) | **0.610** |
| network v3 (position) | 0.668 |
| connectedness v2 (Greta signals) | 0.702 |
| connectedness + fame | 0.715 |
| all four families | 0.728 |
| network + connectedness | **0.733** |

Headline readings:

1. **Structure beats fame.** The best structural model clears the
   attention-only baseline by ~12 points of balanced accuracy, so network
   position is not merely a proxy for how much a place gets talked about.
2. **Narrative beats geography.** Geography alone is *below* the fame
   baseline, and adding it to the structural families does not help (0.728 vs
   0.733). On current features, being narratively connected matters; being
   physically near things does not measurably add.
3. **The single-split scores were flattering.** The same
   connectedness/combined-labels configuration scores 0.975 balanced accuracy
   on a single train/test split and 0.761 under 5-fold CV — with 11 negatives
   a lucky split is easy. Prior 0.9+ results in `place_survival_model_runs`
   should be read as split luck, not model quality.
4. **Figure-ubiquity signature.** In the best model the strongest coefficient
   pair is `figure_mean_ubiquity` negative (−1.39) with `figure_max_ubiquity`
   (+1.11) and `panhellenic_figure_count` (+0.67) positive: places built
   entirely from widely-shared panhellenic figures fare badly, while places
   with one famous anchor plus otherwise local, exclusive figures fare well —
   "a big patron and your own identity".
5. **Greta's shared-figure hypothesis survives the null-model control.**
   `shared_figure_neighbor_zscore` — sharing figures with neighbours *more
   than degree-preserving chance predicts* — is positive (+0.83) in the best
   model, i.e. genuine story-sharing, not just attestation volume, associates
   with survival.
6. On the (degenerate) combined-label run, `has_large_place_neighbor` (+2.28)
   and the kin-mediated tie counts (`kin_linked_large_place_count` +1.86,
   `kin_linked_place_count` +1.35) dominate positively, and
   `early_imperial_story_count` is strongly negative (−2.14) — places known
   mainly through late mythography rather than the archaic/classical core
   look fragile. Treat these as hypotheses to re-test on better labels, not
   findings.

Caveats: n=152; coefficients on standardized but collinear features, so signs
of correlated pairs can counter-rotate; the LLM labels themselves are
unaudited (see the manual-audit item in `TODO.md`); leave-one-region-out
validation has not been run yet.

## Label supply audit (2026-07-06)

Where the n=152 training set comes from and where it leaks:

- **Passage sweep is 18% done.** 569 of 3,170 passages processed by the
  passage-level place-state sweep (gpt-5.4-mini, Batch API, 1M-token daily
  budget in cron). Actual cost is ~1,500 tokens/passage against the 3,500
  planning estimate, so the remaining ~2,600 passages cost roughly 4M tokens
  total. The sweep has already produced 371 distinct labelled places.
- **Linking is the biggest leak.** Of 371 labelled places, only 152 reach
  training. The drops are (a) Latin-vs-Greek transliteration mismatches that
  deterministic linking misses (Amyclae/Amyklai, Bassai/Bassae, Aegae/Aigai),
  (b) sub-place names that should map to a head place ("acropolis of
  Gythium", "Aegina city", "ancient Mantinea"), and (c) monuments that are
  unlinkable in principle (altars, statues, "Alcmena's bedchamber").
- **Pleiades time periods give high-precision negatives.** 1,483 MANTO places
  have Pleiades attestation periods; 227 have nothing after the Hellenistic
  period. On the overlap with unambiguous LLM labels (n=52), Pleiades
  "no post-Hellenistic attestation" agrees with the LLM's does_not_survive
  10/11 times, but Roman-era attestation does NOT imply survival (22 of 32
  LLM non-survivors are still Roman-attested — a ruin Pausanias describes is
  itself an attestation). Use asymmetrically: absence after Hellenistic as a
  does_not_survive label source; presence proves nothing.
- **MANTO Information labels stay diagnostic-only** (872:9; absence of a
  negative phrase defaults to survives).

## Linking expansion results (2026-07-06, same day, second pass)

Fixing the linking leak worked mechanically: transliteration bridging added
305 deterministic links and the LLM curation pass (gpt-5.4-mini, ~150k tokens)
added 110 more with 142 recorded no-matches, taking `manto_place_links` from
811 to 1,226 rows and the labelled training sample from n=152 to **n=356**
(the labelled-but-unlinked queue is down to 134 names, mostly monuments).

The scientific result is sobering and useful: on the bigger, harder sample
every model got *worse*, not better (5-fold CV, LLM labels, majority class
58%):

| feature family | n=152 | n=356 |
| --- | --- | --- |
| fame baseline | 0.610 | 0.568 |
| network v3 | 0.668 | 0.529 |
| connectedness v2 | 0.702 | 0.612 |
| geography | 0.583 | 0.553 |
| network + connectedness | 0.733 | 0.580 |
| connectedness + fame | 0.715 | **0.628** |
| all | 0.728 | 0.617 |

Reading: the exact-name-linkable places were the famous, well-attested ones —
exactly where network features are informative — so the n=152 numbers were an
easy-subset artifact. On the fuller sample, Greta-style connectedness still
beats fame (+0.04..0.06) but generic centrality collapses to chance. Two
follow-ups before drawing conclusions: (a) re-run stratified by link
confidence (high vs medium vs curated-llm) to separate link-noise from
easy-subset effects; (b) review the low-confidence LLM links (generic
"sanctuary of X" names) which plausibly attach wrong labels.

### Link-tier stratification (2026-07-06, third pass)

The feature builders now accept `--link-match-methods`; feature sets were
rebuilt on three link tiers and retrained (5-fold CV, LLM labels, balanced
accuracy):

| family | exact only (n=186) | +transliteration (n=292) | +LLM links (n=356) |
| --- | --- | --- | --- |
| fame baseline | 0.682 | 0.672 | 0.568 |
| connectedness | 0.623 | 0.625 | 0.612 |
| connectedness + fame | 0.689 | 0.729 | 0.628 |
| network + connectedness | 0.691 | 0.668 | 0.580 |
| all | **0.735** | **0.719** | 0.617 |

Verdict: **the degradation comes from the LLM-curated links, not from the
sample getting harder.** Adding 106 transliteration-linked places costs
almost nothing (0.735 -> 0.719; connectedness+fame improves), but adding the
110 LLM links knocks ~10 points off everything — including the fame baseline,
which should be robust to merely-obscure places. That signature points at
mislinked rows (generic "sanctuary of X" guesses, sub-places mapped to head
towns) injecting label noise, not at honest difficulty. Revised position
while the LLM links await review:

- Use the **exact+transliteration tier (n=292)** as the default modelling set
  (`--link-match-methods exact_normalized_name,transliteration`).
- Fame alone is a strong baseline (~0.67); structure alone is weaker than
  fame; but the full structural stack **adds ~5 points on top of fame**
  (0.719 vs 0.672), stable across both deterministic tiers. The defensible
  claim is incremental, not standalone: mythic-network structure carries
  survival signal beyond attention volume.
- After the 110 curated LLM links are reviewed (reviewed=TRUE / rejected),
  rebuild the full tier and re-test whether clean LLM links behave like
  transliteration links.

## Relation hygiene

MANTO bookkeeping relations (`source_attributes`, `collection`, `period`,
`unesco_status`, `mentioned_in_text`, `depictions`, `identified_in`) are
metadata, not mythology. The v1 generic network graph included them; from
feature-set v3 they are excluded by default so centralities measure the myth
network rather than the bibliography.
