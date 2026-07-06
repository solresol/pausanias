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

## Relation hygiene

MANTO bookkeeping relations (`source_attributes`, `collection`, `period`,
`unesco_status`, `mentioned_in_text`, `depictions`, `identified_in`) are
metadata, not mythology. The v1 generic network graph included them; from
feature-set v3 they are excluded by default so centralities measure the myth
network rather than the bibliography.
