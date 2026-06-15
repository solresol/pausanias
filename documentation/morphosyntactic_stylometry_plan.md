# Morphosyntactic Stylometry Plan

Date: 2026-06-15

This specification turns the June 2026 Greg/Greta/Ben discussion into a build plan for Pausanias stylometry. It covers the morphosyntactic lane and the traditional stylometry baselines. The main research question is not "is Book 4 weird?" in isolation, but whether the Messenian Wars section, Pausanias 4.4.1-4.27.1, is stylistically unusual after controlling for content, parser noise, book structure, and normal internal variation.

## Current repo state

- We are going to use the `gpt-5.4-mini` LLM grammar parser rather than the UDPipe models because spot-checking found the UDPipe parses were not accurate enough for evidence-bearing Ancient Greek stylometry.
- `sentence_llm_grammar.py` asks `gpt-5.4-mini` for parser-style token annotations and stores CoNLL-U-like output in `sentence_llm_grammar_analyses` plus queryable token rows in `sentence_llm_grammar_tokens`.
- The older `sentence_udpipe.py` and `sentence_trankit.py` parser lanes remain useful background and possible sanity checks, but they are not the planned primary source for morphosyntactic stylometry.
- Downstream stylometry should not hard-code any single parser table. Build a normalized token-source adapter that reads the LLM grammar tables first, with fields:
  `parser_family`, `model_name`, `prompt_version`, `passage_id`, `sentence_number`, `token_order`, `token_id`, `form`, `lemma`, `pos`, `xpos`, `feats`, `head_token_id`, `deprel`, `confidence`, `note`, `is_syntactic_token`.
- We do not hand off a plain-text corpus to Ben. Instead, we deploy detailed HTML pages to the Pausanias website with statistical outputs and interactive displays answering the questions raised in the conversation with Ben Nagy.

## What I'd Do For Pausanias

1. Keep the current content classifier as content analysis. It can support claims about mythic/historical vocabulary, but it should not be presented as stylometry.
2. Parse the Greek with the `gpt-5.4-mini` LLM grammar parser, then spot-check Book 4, Book 8, and control passages before treating any parse-derived feature as evidence.
3. Build chunk-level feature matrices, not whole-book points. Use non-overlapping chunks for statistical comparisons and rolling overlapping chunks for visualization.
4. Use Pausanias 4.4.1-4.27.1 as the precise Messenian Wars test span. Compare it with nearby Book 4, the rest of Pausanias, and Book 8 as a likely content outlier.
5. Run multiple feature families: function/high-frequency word forms, character n-grams, masked/content-controlled lexical features, LLM-derived morphosyntactic feature combinations, and syntax-word/path features.
6. Trust a finding only if it is robust across several feature families, chunk sizes, and parser/model variants. A Book 4 effect that appears only in content-heavy word features is a topic result, not a style result.
7. Use UMAP/network views as exploratory displays of local neighborhoods and connectedness. Prefer interactive D3-rendered plots with mouseover passage/chunk metadata, nearest neighbors, and feature summaries, but do not treat two-dimensional distances as direct evidence.
8. For the July paper, ship one bounded proof of concept: a parser spot-check, a chunk matrix, and a Book 4/Messenian Wars outlier table across two or three feature families.

## Source-backed method choices

### Gorman morphosyntax

Gorman's 2019 study is the closest methodological precedent for ancient Greek. It uses dependency-treebank annotation without vocabulary: dependency relation plus morphology for each token and its dependency parent. It then builds type-value features, retains frequent features, and classifies short Greek text segments with logistic regression and support vector classification. Reported accuracy remains high even for 50-token inputs, but the point for Pausanias is not to copy the accuracy claim; it is to copy the content-independent feature design.

Implementation implications:

- Treat token form and lemma as available metadata but not part of the morphosyntactic feature family.
- For each syntactic token, create base target features:
  `t.pos`, `t.xpos`, `t.deprel`, and each `t.feats.<key>`.
- If the token has a syntactic parent in the same sentence, add parent features:
  `p.pos`, `p.xpos`, `p.deprel`, and each `p.feats.<key>`.
- Generate type-value pairs from combinations of these categories:
  - simplex: one category, e.g. `t.Case=Acc`
  - binary: two categories, e.g. `t.pos+t.Case=NOUN/Acc`
  - ternary: three categories, e.g. `t.deprel+p.pos+p.Mood=nsubj/VERB/Ind`
- Default to max arity 3. Gorman 2019 explored up to five categories on hand treebank data; Gorman 2022 used machine-generated UD data and capped combinations at three because of combinatorial explosion and sparsity.
- Select features in two modes:
  - exploratory mode: build the frequent feature vocabulary from all Pausanias chunks;
  - target-test mode: build the vocabulary from control chunks that exclude the Messenian Wars target span, then apply it to all chunks.
- Keep frequency thresholds configurable. Start with:
  - include all simplex features except categories with extremely sparse values;
  - for binary/ternary features, keep type-value pairs appearing in at least 5 percent of syntactic tokens in the selection corpus, matching Gorman 2022's machine-annotation threshold;
  - also support top-N fallback values such as 250, 500, 1000, and 2500 features when the percentage threshold over- or under-selects.
- Aggregate token features to chunk relative frequencies. Store both counts and relative frequencies.
- Use L2-regularized logistic regression for labeled tests because it handles many collinear variables and preserves interpretability better than L1 selection.

### Syntax words / dependency paths

Gorman and Gorman 2016 use "syntax words" (`sWords`) built from the dependency path from the sentence root to each target token, initially as dependency-relation sequences and then expanded with part-of-speech tags. They build relative-frequency tables over the most common sWords, standardize by z-score, and use hierarchical clustering and manual inspection of divergent z-scores.

Implementation implications:

- Add an optional `sword` feature extractor:
  - follow each token's `head_token_id` chain to the root;
  - produce a path from root to target;
  - represent each step as `deprel-pos` or, for AGDT output, `relation-xpos/pos`;
  - cap malformed paths and cycles defensively.
- Use the most frequent sWords as a matrix family. Start with:
  - corpus mean relative frequency >= 0.0025, matching the 2016 study's selection rule;
  - plus top-N modes at 500, 1000, and 2500.
- Report per-chunk z-scores and the largest target-vs-control differences. This makes the output philologically inspectable, e.g. "adverbial participial structures attached to a main verb" rather than only "feature_382".
- For nested/agglutinative sWords, also compute conditional ratios where useful, e.g. a child path divided by the frequency of its parent/root path, following the Polybius example in Gorman and Gorman 2016.

### Traditional baselines

The traditional baselines are not inferior controls; they answer a different question. They test whether a target section is unusual under common stylometric feature spaces. Koentges' Ancient Greek Menexenus study is the best model for these baselines: it uses most frequent word forms and most frequent character 4-grams, evaluates several feature counts, and compares multiple distance measures because the best measure may be language-dependent.

Build these feature families:

- `word_mfw`: word-form most frequent words at feature counts 100, 200, 300, 500, 1000, 3000.
- `function_word`: curated particles, conjunctions, articles, prepositions, pronouns, and high-frequency grammatical adverbs. This should be a named subset of `word_mfw`, not a replacement.
- `particle`: Greek particles and discourse markers, including common forms visible in the UD Perseus particle inventory and Pausanias' own high-frequency list.
- `char_ngrams`: character 3-, 4-, and 5-grams. Use 4-grams as the primary Koentges baseline. Include whitespace boundary markers in one mode and exclude punctuation in a sensitivity mode.
- `masked_word`: replace content-bearing forms before counting:
  - proper/person/place names -> `<NAME>` or `<PLACE>` where known;
  - nouns/verbs/adjectives/adverbs -> POS/morph masks in one mode;
  - keep particles, articles, conjunctions, adpositions, auxiliaries, and other grammatical items as surface forms.

Normalization rules:

- Normalize Unicode to NFC.
- Use Greek-aware casefolding for word baselines.
- Preserve diacritics in the primary run. Add accent-stripped sensitivity only as a robustness check, because diacritics may reflect editorial practice rather than Pausanias.
- Strip passage identifiers, generated labels, and English translations from all baseline inputs.
- Store tokenizer and normalization settings in every run record.

Distance/classification methods:

- Standardize features by z-score before Euclidean or Delta-style distances.
- Implement at least: Euclidean, cosine distance, Burrows's Delta, and Eder's Simple/Eder's Delta if practical.
- Add nearest-neighbor lists and k-nearest-neighbor graph edges for interpretability.
- Add bootstrap consensus or repeated parameter sweeps over feature counts, following stylo's practice of checking stability across frequency bands.
- Use t-SNE/UMAP only for exploratory plots. Prefer PCA for first-pass transparent visualization and UMAP/HDBSCAN only as a local-neighborhood aid.

## Chunking and units

Create two chunk sets:

- `pausanias_5000_nonoverlap_v1`: consecutive non-overlapping chunks of about 5000 Greek word tokens. Use these for statistical tables because chunks are approximately independent.
- `pausanias_5000_roll500_v1`: rolling windows of 5000 tokens with 500-token step / 4500-token overlap. This mirrors the rolling stylometry example of 5000-word windows and 4500-word overlap, and is for visualizing local stylistic shifts.

Chunk metadata:

- `chunk_id`, `chunk_set`, `chunk_index`, `passage_start`, `passage_end`, `book_start`, `book_end`, `token_count`, `sentence_count`.
- Boolean flags:
  - `is_messenian_wars` for overlap with Pausanias 4.4.1-4.27.1;
  - `is_book4`;
  - `is_book8`;
  - `is_control`;
  - `is_boundary_chunk` when a chunk crosses major section/test boundaries.
- For overlapping windows, store `overlap_fraction_messenian_wars` rather than only a boolean.

For target tests, avoid treating overlapping rolling windows as independent observations. Use non-overlapping chunks or aggregate rolling scores descriptively.

## Data model to build

Prefer database-backed run records plus CSV/Parquet outputs under `output/stylometry/`.

Suggested tables:

- `stylometry_runs`
  - `run_id`, `created_at`, `status`, `chunk_set`, `parser_family`, `parser_model`, `parser_prompt_version`, `feature_family`, `normalization`, `parameters`, `notes`.
- `stylometry_chunks`
  - metadata listed above; one row per chunk per chunk set.
- `stylometry_chunk_sentences`
  - `chunk_id`, `passage_id`, `sentence_number`, `token_start`, `token_end`, `included_token_count`.
- `stylometry_feature_vocab`
  - `run_id`, `feature_id`, `feature_type`, `feature_value`, `arity`, `source_category`, `selection_count`, `selection_frequency`.
- `stylometry_chunk_features`
  - `run_id`, `chunk_id`, `feature_id`, `count`, `relative_frequency`, `zscore`.
- `stylometry_pairwise_distances`
  - `run_id`, `chunk_id_a`, `chunk_id_b`, `metric`, `distance`.
- `stylometry_outlier_scores`
  - `run_id`, `chunk_id`, `target_label`, `score_type`, `score`, `rank`, `nearest_control_chunks`, `notes`.

CSV outputs should mirror each table so the work is reviewable without database access.

## Analysis reports

Produce at least these outputs:

- `output/stylometry/parser_spotcheck_sample.csv`
  - selected sentences with parser outputs and hand-review columns.
- `output/stylometry/chunks_<chunk_set>.csv`
  - chunk inventory and target/control flags.
- `output/stylometry/features_<run_id>.csv`
  - feature vocabulary with readable names.
- `output/stylometry/matrix_<run_id>.csv`
  - chunk by feature relative-frequency matrix.
- `output/stylometry/distances_<run_id>.csv`
  - pairwise distances and nearest neighbors.
- `output/stylometry/book4_messenian_outliers.csv`
  - target chunks, rank among all chunks, nearest neighbors, metric summaries, and robustness flags.
- `pausanias_site/analysis/stylometry.html`
  - one quiet report page with method note, parser warning, chunk map, tables, and PCA/UMAP/network visualizations.
- `pausanias_site/analysis/stylometry-umap.html`
  - interactive D3-rendered UMAP or network display with mouseover chunk IDs, passage ranges, Book 4/Messenian flags, nearest neighbors, and strongest feature differences.
- `pausanias_site/analysis/stylometry-statistics.html`
  - statistical output page with target-vs-control distance ranks, permutation tests, robustness grids, and feature contribution tables.

The report should always separate:

- content-vocabulary results;
- traditional stylometry baselines;
- parser-derived morphosyntax;
- exploratory visualizations.

## Parser validation

Before a full stylometry claim:

1. Sample at least 60 sentences:
   - 20 from Pausanias 4.4.1-4.27.1;
   - 10 from surrounding Book 4;
   - 10 from Book 8;
   - 20 from control books.
2. For the `gpt-5.4-mini` grammar parser and prompt version, review:
   - tokenization of enclitics, elision, punctuation, numerals;
   - UPOS/XPOS;
   - high-value morphology: Case, Number, Gender, Tense, Mood, Voice, VerbForm, Person;
   - dependency head and relation for participles, genitives, clauses, discourse particles, and appositions.
3. Score each sentence coarsely: `usable`, `usable_with_noise`, `bad_parse`.
4. Record token-level `confidence` and `note` fields from `sentence_llm_grammar_tokens`; surface low-confidence or noted rows in the website report.
5. Keep UDPipe/Trankit comparisons optional and diagnostic only. They should not drive the primary analysis unless the LLM grammar lane fails.

Rationale: the UDPipe/UD parser lanes were not accurate enough in spot checks for this project. The LLM parser is still a parser-like source rather than ground truth, so the plan keeps explicit spot-checking and uncertainty display before making claims from aggregate morphosyntax.

## Statistical protocol

For each feature family:

1. Build non-overlapping chunk matrix.
2. Select feature vocabulary in both exploratory and target-excluded modes.
3. Standardize features on the control set where appropriate.
4. Compute distances from each target chunk to:
   - all non-target chunks;
   - Book 4 non-target chunks;
   - same-book/same-neighborhood controls;
   - Book 8 chunks.
5. Report:
   - nearest neighbors for each target chunk;
   - target chunk rank by mean distance to controls;
   - permutation test comparing target-vs-control distances to random contiguous spans of similar length;
   - sensitivity across chunk size, feature count, parser, and metric.
6. Treat overlapping rolling-window outputs as visualization and local diagnosis, not as independent p-value inputs.

Recommended robustness grid:

- chunk sizes: 2000, 5000, 8000 tokens;
- feature counts: 100, 300, 500, 1000, 2500/3000 where applicable;
- char n: 3, 4, 5;
- metrics: cosine, Euclidean, Burrows Delta, Eder Simple/Delta;
- parser families: primary `llm-grammar/gpt-5.4-mini`; optional UDPipe/UD or Trankit/AGDT diagnostic comparison only;
- parser prompt versions: at least the production prompt plus any revised prompt used after spot-checking;
- normalization: polytonic-preserved primary, accent-stripped sensitivity.

## Implementation sequence

Phase 1: corpus and chunk builder

- Add `stylometry_chunks.py`.
- Read Greek sentences in passage order.
- Tokenize with the same Greek token regex used by parser scripts, but keep a `tokenizer_version`.
- Emit non-overlapping and rolling chunk inventories.
- Add tests for passage-boundary flags, Messenian Wars overlap, and token counts.

Phase 2: normalized parser token view

- Add `stylometry_tokens.py`.
- Provide a primary adapter for `sentence_llm_grammar_tokens`, including `model`, `prompt_version`, `confidence`, and `note`.
- Keep optional adapters for `sentence_udpipe_tokens` and `sentence_trankit_tokens` only for legacy comparison.
- Resolve token parent rows within sentence.
- Exclude punctuation/multiword/empty nodes from syntactic-token counts.
- Add tests with miniature CoNLL-U examples.

Phase 3: traditional baseline features

- Add `stylometry_baselines.py`.
- Implement word MFW, function/particle subsets, char n-grams, and masked word features.
- Add matrix writer and feature vocabulary writer.
- Add tests for Unicode normalization, boundary-marked char n-grams, and masking.

Phase 4: morphosyntactic features

- Add `stylometry_morphosyntax.py`.
- Implement target/parent feature combinations, frequent feature selection, count aggregation, relative frequencies, and z-scores.
- Implement optional sWord path features.
- Add tests for parent lookup, arity generation, threshold selection, and sWord generation.

Phase 5: distances and outlier reports

- Add `stylometry_analysis.py`.
- Implement distance metrics, nearest-neighbor summaries, permutation tests over contiguous spans, and robustness aggregation.
- Emit CSVs and a compact HTML report.

Phase 6: website deployment

- Add website generators for detailed stylometry pages under `pausanias_site/analysis/`.
- Deploy static tables plus interactive UMAP/network displays, preferably D3-rendered so points can be moused over.
- The pages should answer the Ben-call questions directly:
  - Is Pausanias 4.4.1-4.27.1 morphosyntactically unusual?
  - Is Book 8 a content outlier only, or also a style outlier?
  - Do syntax/morphology results support Hutton's broad consistency claim?
  - Which features drive any apparent Messenian Wars difference?
- Keep CSV/JSON assets beside the HTML so the visualizations are reproducible and inspectable.

## Acceptance criteria

- `uv run pytest tests/test_stylometry_*.py` passes.
- A `--stop-after` or `--sample-size` mode exists for every expensive script.
- Every output run records parser family/model/prompt version, feature family, chunk set, normalization, random seed, and feature-selection mode.
- The Book 4/Messenian result page says explicitly whether each observed effect is content-heavy, traditional-stylometric, or morphosyntactic.
- The report includes at least one table of interpretable morphosyntactic features contributing to any Book 4 outlier score.
- The website includes interactive UMAP/network displays with mouseover chunk metadata and links back to passage-level evidence.
- No claim treats UMAP/t-SNE plot distances as statistical evidence.

## Sources used

- Robert Gorman, "Author Identification of Short Texts Using Dependency Treebanks without Vocabulary" (Digital Scholarship in the Humanities, 2019/2020): https://academic.oup.com/dsh/article/35/4/812/5606771
- Robert Gorman, "Universal Dependencies and Author Attribution of Short Texts with Syntax Alone" (Digital Humanities Quarterly, 2022): https://dhq-static.digitalhumanities.org/pdf/000606.pdf
- Vanessa B. Gorman and Robert J. Gorman, "Approaching Questions of Text Reuse in Ancient Greek Using Computational Syntactic Stylometry" (Open Linguistics, 2016): https://digitalcommons.unl.edu/historyfacpub/207/
- Thomas Koentges, "The Un-Platonic Menexenus" (Greek, Roman, and Byzantine Studies, 2020): https://grbs.library.duke.edu/index.php/grbs/article/view/16197
- Mike Kestemont, "Function Words in Authorship Attribution: From Black Magic to Theory?" (CLfL/EACL, 2014): https://aclanthology.org/W14-0908/
- Maciej Eder, Jan Rybicki, and Mike Kestemont, "Stylometry with R: A Package for Computational Text Analysis" (R Journal, 2016): https://journal.r-project.org/articles/RJ-2016-007/
- Computational Stylistics Group, "Rolling Stylometry": https://computationalstylistics.github.io/projects/rolling-stylometry/
- UMAP FAQ: https://umap-learn.readthedocs.io/en/latest/faq.html
- Universal Dependencies Ancient Greek Perseus treebank page: https://universaldependencies.org/treebanks/grc_perseus/index.html
- UFAL UDPipe 2 models page: https://ufal.mff.cuni.cz/udpipe/2/models
