# 1.29.9 generation report — 21 November 2026

The 21 November Sydney run used the saved classical-texts environment at
`/workspace/pausanias`. The supplied exact selector, selected and live
executor identity, runtime source configuration/version, and the three
published Pausanias, Zenobius and Prosodia Catholica checkout fingerprints
agreed with the verified catalogue provenance in the 1.29.8 page plan.
The source configuration and launch selector use distinct namespaces.
The only refreshed checkout was the clean Pausanias work branch, fast-forwarded
from `1597fdd9bbcc25e2f015510b94f27cf789b5baf0` to
`1084828d3072cf5f85ae7134bef975c0c0fe2204` from the expected origin.

Read the published runtime guidance and the repository's AGENTS.md,
CLAUDE.md, graphic-book cloud workflow and README. The prescribed existing
Python reported 3.12.14, frozen no-download uv sync passed, and a read-only
S3 HeadObject returned HTTP 200 using the saved AWS binding. The prescribed
absolute uv, UV_PYTHON and UV_CACHE_DIR were used throughout.

Run `f40a8ab4ba094ac2b2ead3a43568afa6` acquired the shared lease at
01:02:57 UTC. The export dated 2026-11-20T18:15:43.263591+00:00 contains
3,170 passages, 3,170 translations and 197 accepted pages. The helper's
`begin` and `next` selected 1.29.9. Hydration verified all 197 accepted
pages and their recorded component files. The unchanged title image was
verified against the existing asset manifest.

Reviewed the 1.1.4 and 1.1.5 quality anchors and the actual 1.29.3–1.29.8
PNGs and plans. Chose the asymmetric diagonal diptych. The final page
shows the Argive reinforcement from a distant hillside and the Thessalian
cavalry from a closer lateral position. The first infantry raster was
revised to improve viewpoint and scale variety. Both final scenes passed
the semantic, historical, suitability, composition and visual gates.
The complete 565-character, 88-word exact English fit at 56px, and all
eight text fields matched native OCR. The full review and audit files
record the geometry, checks and images.

The 5,578,241-byte final PNG has SHA-256
`2462a302c2d58046692228439440399e9e012a43d37482121363387082358efa`.
The source translation row records hash
`611e515cda2426ad1d86ea8c6e1493559076f4eeb751dd45b9b75a88a92e9126`.
The local build and visual review passed for the Chromium reader and the
199-page PDF, with 198 illustrated passages and the title page.

## Exchange results and replacement decision

Pushed the scoped new-page sources to origin/main at
`302fddfaf7fbd23bb40d491ea29350e8c5633a2b`. The exchange helper verified
immutable S3 read-back of the page and all 13 submitted files before
checkpointing new result `e77871da00c645f89d306503469ad637`.

The one persisted draw was `0.05209213488415898`, within the 20% window.
The eligible catalogue order excluded the six latest pages, the two style
anchors and previous successful replacements. The first of 178 shuffled
eligible pages, 1.4.4, qualified on inspection and was persisted as the
only target. Its original remained canonical and its source and binary
component stayed intact. The candidate uses one low-angle storm panorama
between two horizontal English bands. The 166-word English fits at 53px
and all eight fields matched native OCR. Full-size and thumbnail inspection
against the original and its eight neighbours passed. The temporary 199-page
PDF and the Chromium reader used only the substituted 1.4.4 candidate.

Pushed the scoped replacement sources to origin/main at
`fa3b6cfb9422f5c81cbc2093b46cf7411919607f`. The exchange archived and
verified the old PNG at catalogued hash
`b15f9b6562ccceb183e0a0145c44616b47777f24bf79eb8198cc2107985794aa`.
It verified the candidate and all 11 result-file records, including that
archive, before checkpointing replacement result
`202b74cb095e49299bf96177ce564c57`. The persisted replacement outcome is
`accepted`. Both results have `import_status=pending` in the shared
catalogue. Raksasa handles the original-hash check, PostgreSQL import
and public website publication in its next overnight run.
