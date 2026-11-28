# Generation report · Pausanias 1.29.16

28 November 2026 UTC · Exchange run `c1d8e76a59b74939bb443d4429fb9988`

The saved classical-texts launch and mounted Pausanias checkout were verified. The checkout fast-forwarded to `58b245d725249b85bf5a20db7296725c467fdd8e` before setup. The prescribed Python 3.12 runtime, frozen dependency sync and authenticated S3 corpus read passed. The exchange acquired the claim, hydrated and verified 204 accepted pages, and selected 1.29.16 from the validated complete export.

## Page and checks

*The works of Lycurgus* pairs a panorama of a trireme under repair at the Zea shipsheds with a smaller study of the Acropolis dedications. The complete English runs below the panorama in two measured columns. The page passed native-size, thumbnail, historical orientation, content, text-fit and OCR review against the two anchors and six preceding pages. The local reader and PDF page 206 were verified. [Page plan](page_plan.md) · [Review](review.md)

## Checkpoint and replacement decision

- Source commit `ed45ccf9bdb1746de0241ac50ed8f7c1786b88c5` pushed to `main`.
- New result `f0846e5da6e14b8aad78ed3ccdae5981` checkpointed after the exchange downloaded and verified the immutable PNG plus all 11 source and component files. The S3 catalogue read-back confirmed the result, file hashes and accepted page entry.
- The single persisted replacement draw was `0.48758052719081435`. The threshold is 0.20. The exchange stored `skipped` with an empty target, verified by S3 read-back.
- The result awaits the next overnight Raksasa PostgreSQL import and website build.
