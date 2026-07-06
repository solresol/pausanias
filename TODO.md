# Pausanias To-Do List

This is the canonical project to-do list. It consolidates the older split notes.

Source anchors are in the private ignored transcript notes, especially:

- `transcripts/2026-05-08-greg-and-greta-pausanias-excerpts.md`
- `transcripts/2026-06-12-greg-greta-ben-pausanias-stylometry.md`

## Current Paper-Facing Status

- [x] Reframe the core tagging from binary mythical/non-mythical into
      mythic, historical, and other/geographical/descriptive buckets.
- [x] Complete the active three-bucket sentence tag coverage across the corpus.
- [x] Keep Books 4 and 8 available as robustness checks, while using
      Books-4-and-8-excluded runs for the first paper pass.
- [x] Run surface-form and lemma-level mythic-vs-historical models.
- [x] Run model variants with and without rhetorical/reporting markers.
- [x] Exclude proper nouns from the main predictive analysis.
- [x] Publish Book 3 Greta/Rosie manual-label sensitivity outputs.
- [x] Publish the translation-length residual analysis.
- [x] Publish first-pass morphosyntactic stylometry pages.
- [x] Publish a first rhetoric/source-marker report for Greta.
- [ ] Write the paper-facing interpretation as a compact argument:
      content/rhetorical classification now; stylometry as next-stage evidence.
- [ ] Spot-check the source-marker examples before treating the epichoric/source
      counts as paper evidence.
- [ ] Turn the current live outputs into a short Greta discussion handout or
      slide sequence.

## July Paper / Greta Conversation

- [ ] Present the current content classifier as a preliminary result with clear
      limitations, then frame syntactic/stylometric work as the next step rather
      than trying to finish the whole method before the talk.
- [ ] Review how well the current classifier is working and record the finding
      before choosing the next analysis.
- [ ] Decide which additional Pausanias analysis, if any, belongs in the July
      paper rather than a later paper.
- [ ] Decide whether the MANTO place-survival network features belong in the
      July paper or a separate follow-on paper; see
      `documentation/manto_network_feature_ideas.md` for the feature inventory
      and the fame-baseline/leakage guardrails any claim must pass.
- [ ] Use the manual Book 3 disagreement rate as uncertainty/error bars for
      claims such as "daughter is strongly mythic" rather than treating AI labels
      as ground truth.
- [ ] Reconcile the production checkout on `raksasa` with GitHub/local `main`
      before relying on the newest non-analysis commits.

## Classifier Ontology and Validation

- [ ] Refine the annotation ontology before leaning harder on the classifier:
      decide whether implicit references count, and focus on substantial
      narrative material rather than tiny inferential cues.
- [ ] Add the framework dimension Greta proposed:
      chronological framework plus post-500 BC historical narrative;
      chronological framework plus mythical narrative; spatial framework plus
      post-500 BC historical narrative; spatial framework plus mythical
      narrative; other/unhighlighted.
- [ ] Measure inter-annotator agreement between two expert annotators using the
      revised ontology. Use a limited passage sample if the whole corpus is too
      much, and try to involve Rosie before she leaves.
- [ ] Compare expert labels against AI labels after the revised ontology is
      available.
- [ ] Revisit the scepticism definition, since the call tied the new
      mythic/historical/other definitions to the current scepticism
      interpretation.
- [ ] Preserve the simplified points/checklist output, but regenerate it after
      any new ontology, stopword, marker-removal, and lemma runs.

## Rhetoric and Source Markers

- [x] Build first-pass marker statistics for report formulae, direct epichoric
      terms, source-marked epichoric formulae, and broader local-source proxies.
- [ ] Inspect whether saying verbs have explicit subjects, such as "the
      Athenians say", or are bare narrator-distancing formulae.
- [ ] Rerun the rhetoric/source-marker comparison after discourse-mode tags are
      populated, using `sources_traditions_discussion` as a higher-recall
      control.
- [ ] Keep the direct epichoric measure separate from source-marked epichoric
      claims; direct `epichoric` vocabulary alone is semantically noisy.

## Discourse-Mode Control

- [x] Add the discourse-mode classifier code path and the website page.
- [x] Submit the first discourse-mode pilot batch.
- [ ] Fetch and ingest the submitted discourse-mode batch.
- [ ] Populate `sentence_discourse_mode_tags`.
- [ ] Rerun the aorist/discourse-mode control page once tags exist.
- [ ] Use discourse mode to test whether apparent verbal-form trends are
      stylistic or content/discourse driven.

## Morphosyntactic Stylometry

- [x] Add UDPipe and Trankit parser lanes for the whole corpus.
- [x] Add the `gpt-5.4-mini` LLM grammar parser and store queryable token rows.
- [x] Publish first morphosyntax, function-word, and character n-gram analysis
      pages.
- [ ] Continue the LLM grammar parser toward full-corpus coverage.
- [ ] Spot-check at least 60 parser outputs before making evidence-bearing
      morphosyntax claims: 20 from Pausanias 4.4.1-4.27.1, 10 from surrounding
      Book 4, 10 from Book 8, and 20 from control books.
- [ ] Read and cite the Gorman work on Universal Dependencies / syntactic
      features for ancient-language stylometry.
- [ ] Read and cite Bill Hutton as the key existing diachronic study.
- [ ] Test whether Pausanias 4.4.1-4.27.1, the Messenian Wars span, is
      stylistically unusual relative to Pausanias' internal variation.
- [ ] Treat Book 8 as a likely content outlier first; only call it a style
      outlier if the stylometry supports that.
- [ ] Add a diachronic-composition framing section before the stylometric tests:
      Book 1 probably comes first and may be around 160 CE; Book 5 gives a
      173 CE anchor from the Roman refoundation of Corinth; a similar rate for
      Books 6-10 implies a total composition period of roughly 20-25 years.
- [ ] Add the cross-reference evidence to the diachronic framing: 155
      cross-references across the whole work, about one-third forward-looking,
      plus few repeated information blocks.
- [ ] Use chunking for internal variation and outlier tests; avoid treating
      whole books or overlapping UMAP windows as independent statistical units.
- [ ] Build the planned robustness grid over chunk sizes, feature counts, char
      n-grams, and distance metrics.
- [ ] Use UMAP/network views only as exploratory displays of local neighborhoods
      and connectedness, not as direct distance evidence.

## People, Genealogy, and Gender

- [x] Add a pilot section-level people/gender extraction and website page.
- [ ] Expand section-people extraction beyond the current pilot coverage.
- [ ] Count female versus male names across the mythic/historical/framework
      classes.
- [ ] Measure named versus unnamed persons, including anonymous "daughter of X"
      patterns.
- [ ] Include non-linear kinship terms such as aunt, uncle, and cousin.
- [ ] Use Manto for mythical figures where possible and add a path for
      historical figures.
- [ ] Check Hellenistic dynastic material after Alexander as a likely historical
      confounder for kinship vocabulary.

## MANTO Place Survival Model

- [x] Add a reproducible MANTO release checker and importer for the public
      Zenodo CSV/JSON release.
- [x] Store strict pre-Pausanias filtering on MANTO edges so Pausanias-derived,
      later, and unknown-date source evidence cannot leak into the main model.
- [x] Import MANTO-derived place-survival labels from entity `Information`
      fields and Pausanias tie records.
- [x] Restore archived sentence-level `place-state` outputs for evidence and
      candidate generation.
- [x] Re-enable active LLM place-state extraction as a passage-level Batch API
      sweep rather than a sentence-level sweep.
- [x] Let the explainable place-survival classifier train from MANTO-only,
      sentence-LLM-only, passage-LLM-only, all-LLM, or combined target labels.
- [x] Add deterministic Pausanias-place-to-MANTO linking to the documented
      MANTO import sequence.
- [x] Add first-pass MANTO place linking, strict graph-feature extraction, and
      an explainable logistic-regression classifier scaffold.
- [ ] Run the full MANTO import after downloading the current release into the
      ignored local cache.
- [ ] Review MANTO source-date coverage and add manual source-date overrides for
      high-value ancient sources that the generic importer cannot date.
- [ ] Manually audit a sample of MANTO-derived place-survival labels before
      treating absence of a negative status phrase as a stable positive label.
- [ ] Manually review ambiguous Pausanias-to-MANTO place links, especially exact
      name matches without Pleiades IDs.
- [ ] Expand Pausanias-to-MANTO place linking beyond exact names: MANTO
      alternate labels, local epithets, monument/site names attached to a head
      place, and Pleiades/Wikidata mismatches.
- [ ] Compare the strict pre-Pausanias model against a Pausanias-included upper
      bound only as a leakage diagnostic, not as evidence.
- [ ] Compare MANTO labels, archived sentence-level LLM claims, and new
      passage-level LLM claims before treating the combined labels as paper
      evidence.

### Network-feature brainstorm (2026-07-06)

Full write-up with paper-facing methodology notes:
`documentation/manto_network_feature_ideas.md`.

- [x] Add deeper position features to the place graph: k-core number, hop
      distance to the nearest large place, 2/3-hop local reach, approximate
      node-disjoint paths to the nearest large place (narrative redundancy),
      and bridge-edge fraction.
- [x] Exclude MANTO bookkeeping relations (source_attributes, collection,
      period, unesco_status, mentioned_in_text, depictions, identified_in)
      from the generic network-feature graph.
- [x] Add figure-ubiquity features: exclusive-figure count, panhellenic-figure
      count, mean/max figure ubiquity per place.
- [x] Add kin-mediated place ties: places linked via figure-kinship-figure
      chains (founders who are siblings, parent/child, spouses).
- [x] Add action-profile features: per-place action vectors, profile entropy,
      cosine similarity with neighbours and with large places.
- [x] Add Guimerà-Amaral cartographic roles: within-community degree z-score
      and participation coefficient over Louvain communities.
- [x] Add temporal-layering features from evidence_latest_year: per-stratum
      story counts (archaic/classical/Hellenistic/early imperial), attestation
      span, and myth-accretion signals.
- [x] Import Pleiades coordinates for MANTO places and add geography-network
      hybrid features: geographic distance to the nearest large place,
      neighbour-distance statistics, and localism of mythology (fraction of
      narrative ties within 25/50/100 km).
- [x] Add a fame-baseline feature family (Pausanias mention counts plus raw
      pre-Pausanias attestation volume) that structural features must beat.
- [x] Add stratified cross-validation to the place-survival classifier instead
      of relying on a single train/test split.
- [x] Add null-model z-scores for shared-figure features via degree-preserving
      rewiring of the place-figure structure.
- [ ] Treat the passage/sentence LLM label set (84:68, n=152) as the primary
      evaluation; the MANTO label set is 872:9 and the MANTO+LLM combined set
      639:11, both nearly degenerate. First-pass CV results are in
      `documentation/manto_network_feature_ideas.md`: structure 0.733 vs fame
      baseline 0.610 vs geography 0.583 balanced accuracy.
- [ ] Stop citing the earlier 0.9+ balanced accuracies: the same
      connectedness/combined-labels configuration scores 0.975 on a single
      split but 0.761 under 5-fold CV, so those were split luck on 11
      negatives.
- [ ] Follow up the figure-ubiquity signature (mean ubiquity negative, max
      ubiquity/panhellenic count positive: "a big patron plus your own local
      identity") and the positive shared-figure null-model z-score before
      presenting either to Greta as a finding.
- [ ] Grow the balanced labelled sample: the passage-level place-state sweep
      currently yields 152 linked, labelled places; more passage batches and
      better Pausanias-to-MANTO linking both raise n. Label supply audit is in
      `documentation/manto_network_feature_ideas.md`.
- [ ] Fix the labelled-place linking leak first (free, biggest lever): 371
      LLM-labelled places but only 152 link. Add Latin/Greek transliteration
      variants (Amyclae/Amyklai, -ae/-ai, c/k) and head-place mapping
      ("acropolis of Gythium" -> Gythium, "ancient Mantinea" -> Mantinea) to
      the linking/attach name variants.
- [ ] Finish the passage place-state sweep: 569/3,170 passages done; remaining
      ~2,600 passages cost roughly 4M batch tokens (~1,500 actual
      tokens/passage vs the 3,500 planning estimate). Either raise the one-off
      token budget or let the daily cron run ~9 more days.
- [ ] Add Pleiades time-period labels as a third, asymmetric label source:
      "no attestation after Hellenistic" (227 MANTO places) is a
      high-precision does_not_survive signal (10/11 agreement with LLM labels
      on the overlap); Roman-era attestation must NOT be used as a survives
      signal, since Pausanias-described ruins are themselves Roman-attested.
- [ ] Build a small manual gold set (~50 stratified place-state labels) with
      Greg/Greta and use the disagreement rate as the error bar on LLM labels,
      mirroring the Book 3 manual-tag sensitivity approach.
- [ ] Later: figure quality via global centrality propagation, genealogical
      depth of founding heroes, role-archetype clustering of action profiles,
      regular-equivalence blockmodelling, Burt's constraint, gravity-model
      residuals, and leave-one-region-out validation.
- [ ] Keep negative-valence motifs (destruction/conquest edges) out of the
      fair model; report them separately as a leakage-adjacent diagnostic.

## Translation-Length Residuals and Wordiness

- [x] Make visible which Greek words are associated with longer- or
      shorter-than-expected English translations.
- [x] Add the dual view of English words found in longer- or shorter-than-
      expected passages.
- [x] Publish `pausanias_site/translation_length/index.html` and the
      mythic/historical diagnostic page.
- [ ] Extend the residual model beyond word counts if useful: syllables, letter
      length, phoneme length, word rarity, or Scrabble-like complexity.
- [ ] Use repeated AI translations, where practical, to reduce the objection
      that a residual is just one translator's style.
- [ ] Keep the geography/landscape hypothesis explicit: the likely signal is
      about how ancient and modern language handle landscape, springs, cities,
      built features, and experiential geography.
- [ ] Compare against Strabo or Herodotus once the Pausanias pipeline produces
      stable residual outputs.

## Ben Handoff

- [ ] Confirm whether Ben still wants a Unicode Greek plain-text corpus dump.
      The current implementation path favors detailed HTML outputs over a raw
      corpus handoff, but the older call notes requested passage/chunk
      identifiers and useful labels.
- [ ] Keep Ben apprised once there is concrete output to inspect. His useful
      availability sounded more like August than June/July, so do not block the
      conference paper on his toolkit.

## Operations and Throughput

- [x] Move sentence-level Greta tagging to the OpenAI Batch API.
- [x] Add persistent run metadata: model, prompt version, token usage,
      timestamp, API mode, batch IDs, and failure status.
- [x] Add token-budgeted daily batch submission rather than relying only on a
      tiny fixed row count.
- [x] Add the passage-level place-state sweep to the daily cron pipeline with a
      one-million-token planning budget.
- [ ] Keep the slow legacy sentence-tagging lane running only as a background
      comparison path.
- [ ] Monitor daily batch fetch/submission so submitted discourse, people, and
      passage place-state runs do not sit un-ingested.

## Optional Exploratory Threads

- [ ] Compare the predictors of mythic and historical vocabulary against Mobbs'
      2020 Atlas of dominance vs affiliance.
- [ ] Keep the graphic-history / graphic-book angle exploratory rather than a
      blocker for the July paper.
- [ ] Keep the Herodian/interactive Greek-game-gadget idea separate from the
      Pausanias paper backlog unless it becomes an explicit teaching or outreach
      deliverable.
