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
- [ ] Keep the slow legacy sentence-tagging lane running only as a background
      comparison path.
- [ ] Monitor daily batch fetch/submission so submitted discourse and people
      runs do not sit un-ingested.

## Optional Exploratory Threads

- [ ] Compare the predictors of mythic and historical vocabulary against Mobbs'
      2020 Atlas of dominance vs affiliance.
- [ ] Keep the graphic-history / graphic-book angle exploratory rather than a
      blocker for the July paper.
- [ ] Keep the Herodian/interactive Greek-game-gadget idea separate from the
      Pausanias paper backlog unless it becomes an explicit teaching or outreach
      deliverable.
