# Rhetoric and Epichoric Source Markers

Exploratory comparison for Greta, run on 2026-06-22 against the live
`raksasa` PostgreSQL database.

## Data Surface

- Sentence table: `greek_sentences`.
- Labels: `sentence_greta_both_tags`, prompt version
  `greta-inspired-myth-history-other`.
- Total labelled sentences: 11,302.
- Main contrast: mythic-only vs historical-only sentences.
- Bucket counts: mythic 2,887; historical 3,093; both 184; other 5,138.

The main comparison excludes `both` and `other` rows. The test unit is the
sentence, not the section or passage.

## Marker Definitions

All matching was accent-insensitive and folded final sigma to sigma.

- `λέγουσι/λέγεται report formula`: `λέγουσι(ν)`, `λέγεται`, `λέγονται`,
  `λέγει`, `λέγειν`.
- `λέγω/φημί report formula`: the previous set plus `φασί(ν)` and `φησί(ν)`.
- Direct epichoric term: `ἐπιχώρι*` or `ἐγχώρι*`.
- Source-marked epichoric formula: a report formula in the same sentence as a
  direct epichoric term or `ἐξηγητ*`.
- Broad local-source proxy: a direct epichoric term, `ἐξηγητ*`, or a report
  formula in the same sentence as `αὐτοί`/related self-reference forms.

## Main Results

| Feature | Mythic | Historical | Odds ratio | 95% CI | Fisher p | Book-controlled CMH p |
| --- | ---: | ---: | ---: | ---: | ---: | ---: |
| `λέγουσι/λέγεται` report formula | 440/2,887 (15.24%) | 112/3,093 (3.62%) | 4.77 | 3.85-5.91 | 5.90e-57 | 8.91e-47 |
| `λέγω/φημί` report formula | 842/2,887 (29.17%) | 190/3,093 (6.14%) | 6.28 | 5.31-7.42 | 1.78e-129 | 4.94e-108 |
| Direct epichoric term | 32/2,887 (1.11%) | 25/3,093 (0.81%) | 1.37 | 0.81-2.31 | 0.287 | 0.248 |
| Source-marked epichoric formula | 19/2,887 (0.66%) | 7/3,093 (0.23%) | 2.80 | 1.20-6.50 | 0.0166 | 0.00759 |
| Broad local-source proxy | 74/2,887 (2.56%) | 41/3,093 (1.33%) | 1.95 | 1.33-2.86 | 0.000632 | 0.00153 |

## Sensitivity: Excluding Books 4 and 8

| Feature | Mythic | Historical | Odds ratio | 95% CI | Fisher p | Book-controlled CMH p |
| --- | ---: | ---: | ---: | ---: | ---: | ---: |
| `λέγουσι/λέγεται` report formula | 373/2,263 (16.48%) | 96/2,392 (4.01%) | 4.70 | 3.73-5.93 | 1.52e-47 | 2.12e-39 |
| `λέγω/φημί` report formula | 699/2,263 (30.89%) | 163/2,392 (6.81%) | 6.10 | 5.08-7.32 | 1.90e-104 | 7.89e-88 |
| Direct epichoric term | 30/2,263 (1.33%) | 20/2,392 (0.84%) | 1.58 | 0.90-2.77 | 0.118 | 0.0885 |
| Source-marked epichoric formula | 18/2,263 (0.80%) | 6/2,392 (0.25%) | 3.03 | 1.24-7.41 | 0.0126 | 0.00587 |
| Broad local-source proxy | 64/2,263 (2.83%) | 34/2,392 (1.42%) | 2.00 | 1.32-3.04 | 0.000992 | 0.00163 |

## Interpretation

The indirect-discourse/reporting contrast is strong. On the narrow
`λέγουσι/λέγεται` definition, mythic sentences are about 4.8 times as likely as
historical sentences to contain the formula. On the broader `λέγω/φημί`
definition, the odds ratio rises to about 6.3. This survives a simple
book-stratified Mantel-Haenszel check and the usual Books 4/8 exclusion.

Direct `ἐπιχώριος`/`ἐγχώριος` vocabulary alone is not a clear mythic/historical
difference. It is also semantically noisy: some historical hits are not source
claims at all, but descriptions such as local shields or local men.

The more source-specific local/epichoric measures are more interesting. A
reporting formula with an epichoric or guide term is rare, but mythic-skewed
(0.66% vs 0.23%; OR 2.80). The broader local-source proxy shows a similar
direction (2.56% vs 1.33%; OR 1.95). This suggests that the notable pattern is
not simply "Pausanias uses the word local more in myth"; rather, local source
framing appears more often around mythic material.

## Example Hits

Mythic source-marked epichoric examples:

- 10.24.3: Κύπριοι ... Θεμιστώ τε αὐτῷ μητέρα εἶναι τῶν τινα ἐπιχωρίων
  γυναικῶν λέγουσι ...
- 10.32.9: Τιθορέᾳ δὲ οἱ ἐπιχώριοι τεθῆναί φασιν ἀπὸ Τιθορέας νύμφης ...
- 1.13.8: ταῦτα ... αὐτοὶ λέγουσιν Ἀργεῖοι καὶ ὁ τῶν ἐπιχωρίων ἐξηγητὴς
  Λυκέας ...

Historical source-marked epichoric examples:

- 10.33.9: οἱ δὲ ἐπιχώριοι τοιάδε ἐπʼ αὐτῇ λέγουσι·
- 5.21.9: τὰ δὲ ἐπίλοιπα ... οἱ ἐξηγηταὶ λέγουσιν οἱ Ἠλείων ...
- 8.28.1: λέγουσι δὲ οἱ ἐπιχώριοι καὶ τάδε, ὡς Ἀλέξανδρος ...

## Caveats

This is a surface-marker model, not a full syntactic or rhetorical classifier.
It is good enough for a first comparative statistic on the question Greta
raised, but the source-specific counts should be spot-checked before being used
as paper evidence. The direct epichoric measure especially should not be read as
"epichoric source" without the reporting/guide context.

The current live database did not yet have the `sentence_discourse_mode_tags`
table. Once that lane is populated, the same comparison should be rerun with the
LLM `sources_traditions_discussion` label as a higher-recall control.
