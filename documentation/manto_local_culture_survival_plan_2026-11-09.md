# Local mythic identity and settlement persistence to Pausanias

Research and pipeline plan, 9 November 2026

**Subsequent import update:** after the initial planning audit below, the October
release was downloaded, imported into an isolated schema and validated. The
local atlas was refreshed from it; the active public tables remain on the
earlier release. See the [v3 import and preview verification](manto_v3_staged_import_2026-11-09.md)
for actual counts, checks and remaining activation steps. The August counts and
historical model results below retain their original scope.

## Recommendation

Build on the existing Pausanias/MANTO pipeline, but do not start by adding more graph centralities. The next study should measure **documented local mythic distinctiveness relative to independently defined geographic neighbours**, distinguish that from connections to wider mythic networks, and test whether it improves prediction of settlement status in Pausanias's time.

The strongest first deliverable is an audited regional pilot with a source-backed profile for each settlement. A production synthesis pipeline follows only after entity resolution, source chronology and endpoint labels pass review. The current data support preparing this study, not claiming that distinctive cultures caused cities to survive.

Four questions should remain separate:

1. Which settlements have distinctive documented heroes and traditions, after accounting for evidence coverage?
2. Which resemble nearby settlements through the **same heroes**, and which share **story patterns involving different heroes**?
3. Are villages' narrative profiles disproportionately contained in those of nearby cities? This measures asymmetric resemblance, not demonstrated borrowing.
4. Does distinctiveness add out-of-region predictive information about later habitation, beyond baseline settlement scale, geography and attestation?

“Culture” is broader than MANTO's coverage. The measured construct is the local mythic repertoire recorded in surviving sources, not the entirety of lived local culture.

## 1. What already exists, and what is verified now

### Repository and prior research

The project matching the request is `solresol/pausanias`. This plan was prepared against remote commit `edbe865` in a separate worktree. The existing development checkout had unrelated graphic-book changes and was left intact. Relevant MANTO scripts and the July research inventory were unchanged between that checkout and the fetched remote.

Reusable components:

- `manto_release.py`, `manto_release_check.py`: immutable release discovery, archive cache and checksum checks.
- `manto_importer.py`: raw-record index, entities, ties, edges, source-date filtering and provisional status labels.
- `link_manto_places.py`, `llm_link_manto_places.py`: identifier/name/transliteration links and a curation queue.
- `manto_place_network_features.py`: network position and related features.
- `manto_place_connectedness_features.py`: shared heroes, exclusive heroes, figure ubiquity, action profiles, kin-mediated connections, temporal strata and rewiring controls.
- `import_pleiades_coordinates.py`, `manto_place_geography_features.py`: representative coordinates and 25/50/100 km locality measures.
- `predict_place_survival.py`: regularized logistic classification, alias collapse and stratified cross-validation.
- `manto_place_feature_catalog.py`: human-readable feature definitions.
- `documentation/manto_network_feature_ideas.md`: July analyses and explicit corrections.

The user's recollection of earlier work is correct. The corrected 27 July analysis is also still present in the current database: **255 unique MANTO places, 204 positive and 51 negative labels**. Connectedness achieved **0.564 balanced accuracy**, compared with **0.480** for pre-Pausanias attestation alone and **0.522** for all admissible features. These are historical stratified five-fold results, not results for the newest release and not geographical holdout results.

Earlier much higher scores were retired after removing Pausanias-derived attention predictors and collapsing aliases before assigning folds. The remaining positive exclusive-hero coefficient is a hypothesis, not an established effect. Correlated coefficients and the small negative class make individual signs particularly unstable.

### Latest public data versus installed data

Verified public release: [MANTO v3, Zenodo 23079055](https://zenodo.org/records/23079055), published **1 October 2026**. Archive: `publication-2616-20261001075526.zip`, reported size 517.6 MB, MD5 `f0cfc21122e9a700699c4a2a73533133`. The [live Nodegoat publication](https://manto.unh.edu/publication.s/2616/) also identifies itself as 01-10-2026. Record the version-specific DOI and checksum, rather than relying on a mutable “latest” URL. Recheck the exact release licence and attribution requirements before distributing data products.

Read-only inspection of the documented current PostgreSQL 18 database on 9 November found:

| Item | Observed result |
| --- | --- |
| Latest imported release | 22239985, archive dated 31 August 2026; imported 1 October |
| New public October release | Not present in `manto_releases` |
| Imported entities, all kinds, August release | 54,064 |
| Geographic entities identified by the current place prefix | 2,450, including non-settlements |
| Geographic entities with Pleiades IDs | 1,667 |
| With usable representative coordinates | 1,485, about 61% of all geographic entities |
| Current importer edges flagged pre-Pausanias | 244,290 |
| Edges excluded for unknown source date | 419,644 |
| Other excluded edges | 518,463 Pausanias; 333,778 later/non-pre-Pausanias |
| Provisional MANTO Information-field labels | 873 survives, 9 does not survive, 50 excluded |
| Place-link rows | 1,252 |
| Name/type keys mapping to more than one MANTO entity | 223 |
| Curated LLM link rows | 109, all unreviewed; 98 distinct MANTO targets |
| Connectedness features / model runs for August release | Neither present |

These are counts of the existing representation, **not counts of independent stories or eligible cities**. At this initial planning audit, the latest public archive had been identified but not yet downloaded or imported. No production schema, data, model, scheduled job or website was changed by that audit. The subsequent isolated import is documented in the update above.

The public [model page](https://pausanias.symmachus.org/places/manto-survival-model.html) has no eligible runs for its current release. This is compatible with the historical July results remaining in the database under the March release; it does not mean the July work never happened.

### Immediate gaps that change the study design

1. Existing “local neighbours” mix narrative place edges with `somewhere_in_or_near` parent/sibling relations. They are not an independently defined geographic comparison set.
2. Existing “large places” are the top 5% by degree or PageRank. These are **narrative hubs**, not independently established cities rather than villages.
3. The importer flattens exported paths into edges and derives one latest date from loose row text. An inspected March CSV bundles work, author and period identifiers in expanded paths. Before trusting dates or counts, normalize direct witnesses and relation targets explicitly; audit whether metadata references, reciprocal relations and parallel export representations multiply a single assertion.
4. The present cutoff defaults to 180 CE and excludes named Pausanias evidence. Other sources before 180 can nevertheless be contemporary with the outcome. This is insufficient for a genuinely earlier predictive baseline.
5. Absence of a ruin phrase defaults to “survives” in the provisional MANTO labels. The 873:9 class imbalance makes these unsuitable as ground truth.
6. A single name can identify multiple distinct towns. For example, current `Aegae` links include Achaia, Euboia, Macedonia and an unlocatable place; `Aegina` links include a city, an island and another locality. Collapsing spelling aliases by MANTO ID fixes duplicate rows but does **not** fix a label mistakenly assigned to several different places.

## 2. Define the study population and the endpoint first

### Unit of analysis

Use one **historically resolved settlement at a defined baseline date**, not one name, passage, MANTO geographic object or modern coordinate. Maintain an explicit crosswalk from settlement identity to MANTO IDs, Pleiades IDs, place-name occurrences and spatial locations.

- Separate inhabited settlement, polis/civic community, village, district, island, mountain, sanctuary and monument.
- A city and its island are not interchangeable. A sanctuary near a city is not automatically the city itself.
- Keep city territory, settlement point and associated cult sites separate; a documented assignment can attach a sanctuary tradition to a community without merging their identities.
- Preserve relocation, synoecism, refoundation, name change and uncertain identity as explicit relationships. Decide whether the outcome concerns the same physical site or continuity of the community; report both when evidence supports them.
- Resolve an ambiguous name at the **passage occurrence** level using book, route, neighbouring named places and scholarly gazetteer evidence. Do not broadcast one name-level label to every candidate.

First restrict the outcome study to Pausanias's covered regions and an independent inventory of eligible settlements, including abandoned places. Establishing that inventory only from places with rich MANTO profiles or positive Pausanias mentions would select on the variables being tested.

### Two honest estimands

**A. Prognostic persistence study, if feasible.** Proposed starting specification: settlements positively attested as inhabited around **1 CE**, predictors from independent witnesses whose latest plausible date is before that baseline, and habitation status in approximately **150–180 CE**, refined to Pausanias's local observation where possible. The baseline and risk set must be fixed using coverage and historical feasibility, not whichever choice gives a stronger result. A 100 CE landmark is a separately reported sensitivity with its own eligible cohort and features, not a way to reuse already-abandoned places as “future” failures.

**B. Endpoint-status association, if baseline occupation cannot be established.** Test whether earlier recorded mythic profiles distinguish inhabited and abandoned settlements at Pausanias's endpoint, conditional on the observed cohort. This is still useful, but it is not a longitudinal survival study. Do not silently call it one.

With only an endpoint label, fit binary/multinomial models. Cox or other time-to-event models require defensible occupation and abandonment intervals, entry times and censoring. They are a later extension, not the starting method.

### Outcome protocol

Primary endpoint: **an inhabited settlement/community at the endpoint**. Separately code:

- Inhabited.
- Explicitly abandoned/uninhabited at endpoint.
- Reduced to a village or dependent community but still inhabited.
- Relocated, merged or refounded.
- Ruins/monuments reported without sufficient evidence about inhabitants.
- Contradictory or unknown.

For the primary binary comparison, inhabited and inhabited-but-reduced count as positive; explicitly abandoned counts as negative. Report alternative civic-survival and continuity definitions separately. Do not force ambiguous ruins or relocations into the binary outcome.

Pausanias 10.4's Panopeus, occupied despite lacking expected civic buildings, illustrates why civic grandeur and habitation are different outcomes ([passage and research commentary](https://periegesis.abm.uu.se/en/reports.php?reportid=323)). A cult surviving at a ruined town likewise does not establish settlement habitation.

Use Pausanias passages as evidence, not automatic truth labels. Two reviewers should code passage, temporal scope, exact quotation, entity identity and status, initially blind to distinctiveness scores. Adjudicate disagreements. Archaeological/epigraphic checks should be independent where available; record contradictions rather than resolving them in favour of the model. Missing from Pausanias is not a negative label.

**Do not promote the old Pleiades “no post-Hellenistic tag” heuristic to gold labels.** An absent date tag is not observed abandonment, and Roman-period attestation can describe ruins. Pleiades distinguishes conceptual places, locations, names and their temporal attestations ([conceptual overview](https://pleiades.stoa.org/help/conceptual-overview)). Its dates can flag records for review, not decide habitation automatically.

## 3. Build two separate graphs

### Geographic comparison graph

Construct this from the resolved settlement cohort, independently of mythical similarity and outcome labels.

Proposed primary definition: all other eligible settlements within **50 km great-circle distance**, with normalized weights proportional to `exp(-distance / 25 km)`. This is a transparent starting scale, not a claim that 50 km was a universal ancient social neighbourhood.

Prespecified alternatives:

- Fixed radii 25 and 100 km.
- Five nearest eligible settlements, with the actual distance distribution reported and a 100 km cap; fewer than five is allowed.
- Where evidence permits, estimated land/sea travel time, mountain barriers and historically attested routes. Do not substitute modern road journeys.
- Separate sea-connected island/coastal neighbours from overland neighbours; straight-line proximity across a mountain or water can be socially misleading.

Report the number and types of neighbours and effective weighted sample size. No neighbours means an unavailable local-comparison score, not perfect distinctiveness. No reliable coordinates means a missing spatial comparison, not a distance of 9,999 km.

Pleiades representative coordinates are a useful start. Store location type, uncertainty radius/polygon, period, possible alternative locations and the reason for any representative point. Regional centroids must not masquerade as town sites. Recompute features over plausible coordinate draws or alternative locations; return score intervals and neighbour-set stability.

### Mythic evidence graph

Use separate tables for settlements, figures, narrative assertions/ties, relations/roles and witness attestations. Retain direction, variant, participants, location and source citation. MANTO ties can carry origins, destinations, agents, instruments and other qualifiers; they are richer than a bag of names ([data-collection method](https://www.manto-myth.org/blog/data-collection-the-manto-method)).

Keep at least these layers:

1. **Local identity associations:** founder, eponym, ruler, local cult, burial/relic, recurring ritual or games, where evidence actually attributes these to the community.
2. **Broader narrative contact:** visits, journey endpoints, battles, genealogical connections and panhellenic participation.
3. **Story-pattern profile:** relation/action plus roles, compared with names removed, preserving meaningful distinctions among variants.

A battle at a place, a god appearing everywhere, and a city's unique founder are not equivalent evidence of local identity. Begin with the existing canonical action vocabulary, then have a classicist review its meaning and ambiguous mappings. “Same action” is a coarse motif, not proof of the same story.

Do not project every pair of entities in a tie into a relation. Keep text authors, bibliographic objects and bookkeeping classifications out of the mythic-figure layer. Review historical humans, mythic figures and gods separately where this affects interpretation.

## 4. Date the witness, not the story

Each assertion needs:

- Direct surviving witness/work and passage or artifact.
- Witness date interval and confidence.
- Any claimed indirect source, its attributed date and whether independently preserved.
- Mythical/narrated event time, kept in a separate field.
- Evidence of a genuinely local tradition versus a modern inference from an event location.

For a strict pre-baseline feature, require at least one independently attested witness with an upper date bound before the baseline. Exclude Pausanias, later and uncertain-date-only support. An old oral tradition or archaic artifact known only because Pausanias reports it is **not independently observed pre-Pausanias evidence**. MANTO explicitly distinguishes those direct and indirect sources ([source discussion](https://www.manto-myth.org/blog/things-mentioned-by-pausanias-or-an-excuse-to-talk-about-secondary-sources)).

Where both early and late sources attest the same claim, retain the early support and exclude the late support rather than discarding the whole claim or counting it twice. Treat uncertain date intervals as intervals, not a regex-derived precise year. Source/work date overrides need bibliography and review, not ad hoc adjustments to improve coverage.

Run three clearly separated corpora:

1. Strict baseline-dated independent evidence: the main predictive analysis.
2. Broader, still independently dated pre-Pausanias evidence: endpoint association and sensitivity only.
3. All-source, including Pausanias: descriptive atlas and a leakage diagnostic, never advertised as earlier prediction.

Absence in an author can be a narrative omission rather than ignorance or absence of tradition. Source-stratified and leave-one-author-out analyses are therefore essential ([MANTO chronology study](https://www.manto-myth.org/blog/mythic-chronology-in-pausanias-preliminary-data-analysis)).

## 5. Quantify distinctiveness, integration and asymmetric resemblance

The following are proposed definitions, not observed findings. Freeze them before looking at outcome associations.

Let `x_if` indicate that settlement i has an eligible, reviewed local-identity association with figure f. Binary presence is the primary representation, so ten exported rows do not count as ten traditions. A sensitivity can use capped counts of genuinely independent witnesses. Let `df_f` be the number of eligible settlements associated with f and `N` the number in the fixed reference corpus. Rarity weight: `r_f = 1 + log((N+1)/(df_f+1))`.

### Primary: local hero-profile distinctiveness

For settlements i and j, rarity-weighted Jaccard similarity is:

`S(i,j) = sum_f r_f min(x_if,x_jf) / sum_f r_f max(x_if,x_jf)`.

Define local distinctiveness:

`D_i = 1 - sum_j w_ij S(i,j)`, over the independent geographic neighbours.

The weights sum to one. Higher D means less resemblance to the observed neighbourhood. Empty or inadequately observed profiles remain missing/low-information, not maximally distinctive. Give every score its witness coverage, location uncertainty and stability interval.

Also report similarity to the single most similar neighbour. A settlement can differ from the neighbourhood average yet closely resemble one neighbouring metropolis.

### Secondary, interpretable dimensions

- **Local-only share:** rarity-weighted fraction of i's supported figures absent from its geographic neighbours. Distinguish this from global exclusivity. Absence is “not attested in this corpus,” not proof that another settlement lacked the tradition.
- **Global exclusivity and integration:** share exclusive to i; share tied to widely distributed figures; number of independently supported long-range connections. Do not collapse “own traditions” and “panhellenic connections” onto opposite ends of one scale. Both may coexist.
- **Story-pattern distinctiveness:** Jensen–Shannon divergence between i's smoothed action/role distribution and the weighted neighbourhood mixture, using log base 2 so divergence is in [0,1]. Also report cosine similarity for continuity with existing code. A shared generic foundation motif alone is weak evidence of borrowing.
- **Different-hero, same-pattern overlap:** shared reviewed motif/role configurations for which the settlements' participating heroes differ. Keep this distinct from overlap in the same heroes. Existing `shared_action_patterns` is a useful coarse baseline, not the final semantic definition.
- **Identity diversity:** effective number of figures/motifs from entropy, reported separately from distinctiveness. Variety does not imply uniqueness.

Do not put all of these correlated summaries into the first model. Prespecify D as the primary distinctiveness predictor, one independent integration measure, and at most one substantively motivated interaction. Treat the rest as diagnostics and later hypotheses.

### Village–city resemblance and possible influence

Assign baseline city/village/civic status and, where possible, settlement extent from historical/archaeological evidence independent of MANTO centrality and endpoint status. Otherwise say “narrative hub,” not “city.” Keep unknown status explicit.

For a village v and nearby city c, define directional profile containment:

`C(v->c) = sum_f r_f min(x_vf,x_cf) / sum_f r_f x_vf`.

Report both directions and their difference. A high village-to-city containment but low city-to-village containment says that the observed village repertoire is largely a subset of the city's. Larger, better-documented repertoires mechanically produce this pattern, so compare with evidence/size-matched city–village pairs and source-balanced nulls.

For each village, compare the nearby independently identified city with alternative nearby villages/cities at similar distance and documentation. If studying pairs statistically, account for shared villages and shared cities; pairs are not independent samples.

Actual borrowing or influence needs more: dated independent attestations, historical contact and close narrative variants consistent with transmission. Earlier surviving documentation is not necessarily invention. Without that evidence, use “asymmetric resemblance,” “shared tradition,” or “compatible with influence,” not “borrowed from.”

## 6. Control unequal observation and measurement uncertainty

The largest risk is confusing unusual survival of evidence with unusual local culture.

- Count independent works/witness traditions, assertions, relation types, date bins and source diversity for each settlement. Ancient authors copying a common source are not independent confirmations.
- Plot distinctiveness against evidence volume. Rarefy well-attested places to comparable support; stratify by coverage; compare high-confidence-only and fuller cohorts.
- Bootstrap by work/source family as well as settlement/region, rather than resampling individual export rows.
- Use shrinkage for sparse motif distributions and report low-information cases without rankings. Pilot the support threshold without seeing outcomes; do not invent a universal minimum based on an appealing score distribution.
- Construct constrained bipartite nulls preserving place repertoire size and figure ubiquity, with source/date strata and geographical matching where feasible. Report null mean, interval and standardized excess; verify swap mixing. Unconstrained rewiring erases meaningful geography and is not a sufficient control.
- Propagate uncertain links and coordinates with multiple plausible assignments. Never make uncertain alternatives into multiple independently labelled training rows.
- Compare exact-ID/manually reviewed, transliteration-reviewed and broader link cohorts. The current `reviewed=false` even on deterministic links means algorithmic confidence is not scholarly verification.
- Treat missing features with explicit missingness indicators and training-fold imputation, not huge numeric sentinels. Audit whether imputation predicts missing documentation rather than survival.
- Report an inclusion-flow table: geographic objects → settlements → baseline eligibility → geolocation → dated mythic evidence → independently adjudicated endpoints → final analytical cohort. Describe exclusions by region, settlement scale and status when known.

A minimum pilot should review roughly **80–120 settlements** across two contrasting regions, with ambiguous names, thin/rich profiles and city/village pairs deliberately included. This is a planning target, not a power calculation. Double-code endpoint labels and difficult identity mappings; include all available putative failures in the pilot regions, not only an easy balanced subset. Separate the enriched audit sample from estimates of population prevalence.

## 7. Prediction, explanation and causal limits

### Models

On the same eligible settlements and the same held-out folds, compare:

- **B0:** intercept/class prevalence; report the majority baseline.
- **B1:** parsimonious pre-baseline geography, settlement scale/status and region structure.
- **B2:** B1 plus independent pre-baseline attestation coverage/source diversity.
- **M1:** B2 plus the prespecified distinctiveness score.
- **M2:** M1 plus integration and, only if feasible, distinctiveness × integration.

Start with ridge logistic regression or a carefully regularized hierarchical logistic model. Use an ordinal/multinomial sensitivity for inhabited, reduced, relocated and abandoned states where sample sizes permit. Estimate adjusted predicted differences over a meaningful change such as the interquartile range of D, not only standardized coefficients.

Candidate baseline covariates include settlement scale, age, coastal/harbour access, terrain and connectivity, distance to an independently defined city and region. Include wars, political incorporation or other shocks only with their own temporal evidence and a declared role. Post-baseline size or prosperity may mediate the relation and cannot be silently treated as a pre-existing confounder.

A causal diagram should distinguish underlying settlement scale, connectivity and wealth; traditions; literary recording/preservation; selection into MANTO/Pausanias; and later habitation. Evidence volume is partly measurement and may partly reflect real cultural processes: show results with and without that adjustment. No feasible adjustment removes all selection and reverse causation here. The defensible claim is incremental association/prediction, not a causal survival benefit.

### Evaluation

- Resolve identity before folds. Group aliases, alternative IDs and site/community continuity variants so none crosses train/test boundaries.
- Primary validation: leave-one-region-out or spatial block folds with a buffer, sized to the neighbour scale. Report pooled held-out predictions and the number of independent regions, not only a mean of folds. Random stratified CV is a secondary comparison with July results.
- Tune regularization, imputation, any learned weights/features and thresholds inside training folds. Use nested spatial validation where sample size permits. Otherwise prespecify a small model and explicitly label the result exploratory.
- A fixed, label-free external MANTO reference graph can include held-out places if the intended task is prediction for known places with their narratives available. Declare this transductive setting. Also test stricter geographic holdout with training-fitted rarity/normalization, and never use neighbour survival labels or full-cohort supervised feature selection.
- Check performance and residual spatial autocorrelation by region, source coverage, settlement type and link confidence; add leave-one-author/source-family-out sensitivity.
- Report log loss/Brier score and calibration, ROC AUC, PR AUC for the scarce abandonment class, balanced accuracy, both class recalls and confusion matrices. Class-weighted logistic scores need calibration evaluation; they are not automatically calibrated probabilities.
- Compare the **paired incremental** performance of M1 versus B2 on identical folds. Obtain uncertainty from resampling appropriate geographic units and label/link realizations; distinguish uncertainty across regions from repeat-split variability.
- If a held-out region contains only one class, do not fabricate that fold's AUC/balanced accuracy. Report suitable losses, the class count, and pooled metrics with the limitation.
- Model selection, scale selection and motif exploration must not be judged on the final held-out region. Correct for multiple testing or keep the exploratory variants explicitly exploratory.

The historical 51 negative observations cannot support dozens of freely selected features and interactions. Before claiming sufficient power, simulate plausible effects with the observed class balance, spatial clustering, missingness and label error. If confidence intervals remain wide, the useful outcome is a well-validated atlas and a clearer null/uncertain result, not a more complex classifier.

## 8. Concrete synthesis pipeline

No production implementation is part of this plan. Prefer typed relational tables, foreign keys and indexes in the project's existing PostgreSQL style; do not introduce JSON/JSONB staging or opaque application-data columns.

| Stage | Reuse / proposed addition | Stored output and gate |
| --- | --- | --- |
| 0. Freeze scope | Existing release checker; new analysis manifest | Exact release, archive hash, code commit, cutoffs, cohort version, reviewer protocol and licence. No mutable “latest” during a run. |
| 1. Stage release | Extend importer in an isolated scratch DB | Versioned raw archive plus typed assertion/witness/role tables. Compare old/new schema, IDs, counts, relation vocabulary and references before promotion. |
| 2. Resolve settlements | Extend place linking | `study_settlements`, `settlement_entity_links`, `place_occurrence_links`, `settlement_locations`, `settlement_status_evidence`; preserve uncertainty and decisions. |
| 3. Normalize evidence | New source and assertion layer | `source_witnesses`, `assertions`, `assertion_attestations`, `assertion_participants`; distinguish date kinds and deduplicate representations, not independent witnesses. |
| 4. Build neighbours | New independent spatial builder | `settlement_neighbours` with radius/travel scenario, distance, weight and location-draw provenance. No narrative-based neighbourhood selection. |
| 5. Build profiles | Extend connectedness/geography features | Versioned figure/motif profiles and `local_identity_features`, with support and uncertainty. Features computed without endpoint labels. |
| 6. Adjudicate outcomes | Reuse passage claims as candidates | `settlement_endpoint_labels` plus claim/reviewer tables, exact passage citations, baseline eligibility and conflict decisions. |
| 7. Evaluate | Extend survival predictor | `study_folds`, `study_predictions`, `study_metrics` and model specification, with one settlement per unit and frozen spatial splits. |
| 8. Synthesize | Reuse feature catalog/site components | Source-backed settlement profiles, regional maps, neighbour comparisons, uncertainty and a cohort-level research report. Publish only after review. |

Every stage should be reproducible, idempotent, release-scoped and resumable. A new release produces a diff and new versioned outputs, not silent replacement of a published analysis. Record merges/splits of MANTO entities across releases rather than assuming IDs and meanings never change.

### What the settlement profile should show

For each settlement: identity and type at baseline; map and uncertain location; closest comparison settlements and why selected; documented local figures/motifs; shared and distinctive elements with citations; neighbour containment and similarity; support/uncertainty; adjudicated endpoint; and any held-out prediction clearly distinguished from observed status.

Example phrasing, not a computed result: “The surviving pre-baseline evidence for settlement A shares two founders' motifs with nearby B but names different heroes. Its hero repertoire is comparatively distinctive among five mapped neighbours, although it rests on only two independent works.”

An LLM may turn structured evidence into a readable account, but must not invent source dates, borrowing directions, cultural ownership or causal explanations. Require citation IDs for every substantive sentence, validate the numbers against stored features, and flag unsupported or contradictory statements for review. Quantification stays deterministic and inspectable; synthesis is a presentation layer.

### Tests and acceptance gates

- Foreign-key and identity uniqueness checks; no unintended many-to-many join expansion.
- Source-role separation and stable assertion IDs; explicit tests for mirrored CSV relations, repeated exports and mixed early/late witnesses.
- Strict cutoff tests, including Pausanias-only indirect archaic testimony, uncertain date intervals and contemporary non-Pausanias sources.
- No predictor from endpoint text, endpoint city status or outcome-derived source counts.
- Spatial fixtures: known distances, no self-neighbours, missing/uncertain coordinates, islands, ties at radius boundaries and zero neighbours.
- Similarity fixtures: identical/disjoint profiles, empty support, ubiquitous versus exclusive figures, different figures with the same motif, and asymmetric subset profiles.
- No alias/continuity overlap across folds; preprocessing fitted in training folds; held-out predictions complete and unique.
- Source citation round trips from every feature contribution and generated statement to original evidence.
- Reproducing the old cohort is an engineering regression check, not a requirement that the new study reproduce the old accuracy.

## 9. Practical order of work and stopping rules

1. **Inventory and release audit.** This plan establishes the public release, installed release and reusable code. Next inspect the full current Manual and v3 archive in staging, before assuming the older export schema still applies.
2. **Two-region feasibility pilot.** Assemble 80–120 candidate settlements; review ambiguous identities, independently date sources and adjudicate habitation. Produce coverage and disagreement reports before fitting any outcome model.
3. **Descriptive pilot.** Compute the prespecified geographic comparisons and a handful of interpretable profiles. Classicists should inspect high/low scores and source evidence without choosing definitions to fit survival.
4. **Freeze the analysis protocol.** Select the historical baseline and eligible cohort using feasibility alone. Freeze feature definitions, primary hypothesis, spatial folds and reporting thresholds. If genuine baseline occupation cannot be established, explicitly switch to the narrower endpoint-association estimand.
5. **Run the modest predictive study.** Compare against geography/scale/attestation baselines; report uncertainty and negative results. Expand the sample or labels only through a documented protocol, not selective repair of inconvenient cases.
6. **Build the recurring synthesis pipeline.** Only after the pilot passes, extend importer/typed schema, profiles, evaluation and report generation. Separate public atlas deployment from statistical analysis and retain old versioned results.

Stop short of a predictive headline if the main signal disappears under source/region holdouts, depends on uncertain place links, cannot be distinguished from unequal documentation, or requires outcome-contemporary evidence. Such results would still answer which parts of the hypothesis the surviving evidence can and cannot test.

## Sources and verification limits

Local evidence: repository files named above; `database/schema.sql`; `DATABASE_CONFIG.md` on the fetched remote; read-only queries in the companion audit SQL; cached March export inspected only for representative structure. The database was read with `default_transaction_read_only=on` and bounded statement timeouts on the documented current PG18 endpoint. The deliberately retired PG16 copy was not reopened.

Public primary/project sources: [MANTO v3](https://zenodo.org/records/23079055); [Nodegoat publication](https://manto.unh.edu/publication.s/2616/); [MANTO documentation](https://www.manto-myth.org/documentation); [data-collection method](https://www.manto-myth.org/blog/data-collection-the-manto-method); [direct and indirect sources](https://www.manto-myth.org/blog/things-mentioned-by-pausanias-or-an-excuse-to-talk-about-secondary-sources); [mythic chronology analysis](https://www.manto-myth.org/blog/mythic-chronology-in-pausanias-preliminary-data-analysis); [Pleiades conceptual model](https://pleiades.stoa.org/help/conceptual-overview); [Panopeus study/passages](https://periegesis.abm.uu.se/en/reports.php?reportid=323).

The Manual's linked Drive content was not readable through the public web tool in this pass. The full v3 schema, archive bytes, source-date accuracy, human endpoint labels and actual predictive performance have **not** been validated. No contemporary city ranking, borrowing claim or survival effect is asserted here. The next step is an audited pilot, not a production-wide import or a causal conclusion.

## 10. Expanded brief: a public Symmachus research website

The follow-up request adds a dedicated website, a higher-level network with overlays, graph-neural-network experimentation, an evidence-backed list of settlement survival/non-survival, and an independently operated scheduled deployment. These are the proposed additions to the research programme; the infrastructure and production implementation have not been performed by this planning task.

### Site structure

Proposed site identity: a MANTO research atlas under Symmachus, with `manto.symmachus.org` a candidate hostname to verify before configuring it. Keep a clear relationship to the existing [Pausanias project](https://pausanias.symmachus.org/), while giving this study its own versioned results and operational identity.

1. **Overview:** the actual question, latest processed release and analysis version, coverage, what is measured, and conclusions supported by the current stage. If only a pilot is ready, say so.
2. **Settlement atlas:** linked map/network/table with region, type-at-baseline, time slice, evidence coverage and source filters. Unmapped places remain discoverable in the table.
3. **Compare neighbours:** choose a settlement, view the geographic comparison set, shared heroes, different-hero/shared-motif patterns, directional containment and source citations. Label “similarity” separately from any reviewed transmission hypothesis; avoid a copying leaderboard.
4. **Higher-level networks:** settlement communities and region-to-region connections, with an explicit switch between geography, mythic similarity and historical affiliations.
5. **Survival evidence register:** every included Pausanias settlement, habitation/civic/continuity status, observation date/temporal scope, passage number, original Greek, permitted translation, evidence excerpt, confidence and review history. Include disputed, unlinked and unknown cases, not just binary successes/failures.
6. **Models and validation:** baseline, feature model and GNN comparisons on identical held-out cohorts; calibration, failure cases and uncertainty. Show predicted probability separately from the historical label. No apparent confidence from a score computed on the training set.
7. **Methods, data and releases:** definitions, source dates and licence, inclusion/exclusion flow, downloadable permitted derived tables, release diffs, reproducibility manifest and known limitations.

For each evidence-register row, keep the place occurrence and passage link authoritative. Name-based grouping may assist browsing but must not merge Aegae's different towns. Excerpts should retain enough context to tell an abandoned town from an earlier destruction followed by rebuilding. Sources disagreeing about habitation should be visible side by side. Do not publish reviewer-sensitive annotations or unlicensed source dumps by default.

### Higher-level network design

Start with a multiplex graph rather than one uninterpretable network:

- Geographic/travel proximity.
- Shared named figures, weighted for ubiquity and observation coverage.
- Shared reviewed motifs/roles, with named-figure overlap shown separately.
- Documented political, genealogical or foundation links, with date and source.

Coarsen this in two independently named ways: historical geographical regions (where boundaries and dates are defensible) and algorithmic narrative communities. An algorithmic cluster is a group of similar records, **not proof of a historical cultural group**. Report community stability across sources, release versions, scale parameters and uncertainty draws. Do not choose clustering resolution to maximize survival separation.

Aggregate inter-group connections using a size/degree/source-adjusted measure, not just the number of raw edges, which makes large groups dominate. Provide raw totals alongside normalized values and a constrained-null comparison. Allow drill-down from a group edge to contributing settlement pairs and then to actual assertions and citations. Clearly distinguish narrative hub size from estimated settlement population/area.

Useful overlays: independent settlement status and extent at baseline; endpoint habitation; reviewed/uncertain identity; witness date distribution; source author/work; coordinate precision; region; distance/travel category; cult/foundation/burial/other motif; data coverage; held-out model residuals. An overlap can suggest a research question but does not by itself explain a causal pathway.

Use accessible colours, scalable static summaries for large graphs, searchable tables, keyboard-accessible evidence panels and compact mobile views. Maps and network positions are alternative views, not interchangeable coordinates. Evidence, filters and provenance must survive shareable URLs so a scholar can cite the exact comparison.

### Graph neural network comparison

The GNN is a requested experiment, not the presumed best model. The historical labelled cohort is too small to assume a flexible network will generalize.

- Benchmark the same low-dimensional logistic models first; optionally add a shallow tree/boosting baseline and unsupervised graph-embedding classifier, with equal tuning discipline.
- Use a small GraphSAGE or relation-aware heterogeneous GNN, with settlement, figure and assertion node types and explicit relation types. Begin with one or two message-passing layers, low-dimensional embeddings, strong regularization and early stopping. Tune only on inner training/validation partitions.
- Input attributes must be eligible pre-baseline features. Exclude outcome labels, Pausanias evidence, endpoint-status fields, post-baseline civic classifications and free-text descriptions containing ruins/survival statements. Pretrained text/name embeddings can carry later historical knowledge: omit them from the primary temporal benchmark.
- Keep geography and narrative edges as separate channels and compare ablations: geography-only, narrative-only, both, shuffled/degree-matched graph and node-features-only. This shows whether message passing learns more than proximity, document volume or degree.
- Primary test: geographically held-out settlements/regions with no test labels used in training, early stopping, hyperparameter choice or neighbour aggregation. For a strict inductive experiment remove held-out nodes/edges from training; evaluate on the declared available graph at inference. Report a separately labelled transductive experiment if the whole label-free graph is available beforehand.
- Respect buffer zones and entity-continuity groups. A graph split by random nodes is not a sufficient independence test. Prevent neighbours' labels, label-derived node features and all-source texts from entering messages.
- Fix an equal, modest search budget and report results across several seeds without selecting the best test seed. Compare paired held-out predictions, calibration and uncertainty to the simpler models. Document effective labelled sample size, not just total graph nodes.
- Use edge/feature ablations and retrieved source evidence to explain predictions. An attention weight or graph explainer is not historical proof of influence. If the GNN fails to improve held-out performance, publish that comparison and retain the simpler model.

The concrete added output is a model comparison page plus stored out-of-fold predictions, not a neural-network demonstration divorced from the research question.

### Operational design and approval boundary

Reuse the repository's established static publishing and monitoring patterns after a separate infrastructure inspection. Proposed flow: a dedicated unprivileged Raksasa service account reads the authorized source snapshot, runs version-pinned processing, builds into a temporary release directory, validates it and atomically promotes the accepted build on Merah. Retain the previous build for rollback; a failed or partial computation must leave the current site unchanged. A read-only source export or minimally scoped database reader is preferable to granting the new job broad production-write rights.

Proposed scheduling: inexpensive release discovery at a moderate cadence, processing only a new verified release or explicitly requested analysis version. Expensive GNN/LLM runs should have a declared budget and must not repeat on every check. Use locking, timeout/backoff, checksums and stable job IDs. The existing Pausanias reporting channel is the default destination for approved operational messages, rather than creating a duplicate channel; verify the exact channel first. Report changed release, completion and actionable failure, not routine no-change noise.

Infrastructure inspection must confirm the exact hostname, DNS zone/proxy/TLS policy, Merah vhost path and service role, Raksasa job account, source access, cron cadence and existing Slack destination before changes. A possible least-privilege deployment key would be dedicated to this job, stored only under the Raksasa service account, and authorized on Merah solely to publish the intended vhost directory, with no port/agent/X11 forwarding and no unrestricted interactive shell where supported. Do not copy an existing broad personal key.

**Creating that key or other persistent access, installing it, granting database rights, or changing security-sensitive network configuration requires the applicable action-time approval for the exact inspected scope.** Creating the requested account, schedule, vhost, DNS record or channel must likewise follow the relevant confirmation rules. This plan is not a claim that any of these changes have occurred or are approved merely because their design is listed here. A separate deployment worker should present the concrete key/account/target proposal before those actions, then verify DNS, HTTPS, access restrictions, cron behavior, atomic publish/rollback and Slack delivery without manufacturing unnecessary paid work.
