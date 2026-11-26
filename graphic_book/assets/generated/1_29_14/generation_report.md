# 26 November 2026 Sydney generation report

The scheduled launch supplied the live classical-texts catalogue
verification for saved selector
`7512863f-09f4-4e48-8323-0b0fc383a354~asenvcfg_90a558a103808191ac872767429b7689`.
The managed runtime status was current and its environment ID agreed
with the selected shell. The runtime source configuration and version
matched the verified [1.29.8 provenance](../1_29_8/page_plan.md).
The mounted Pausanias, Zenobius, Prosodia Catholica and Word Garden
origins and revisions matched the classical-texts checkout fingerprints.

The clean Pausanias checkout fast-forwarded from
`1597fdd9bbcc25e2f015510b94f27cf789b5baf0` to verified `origin/main`
at `7b298719897f58633f7ff5b4937daf2cf3a76834`. The prescribed Python
reported 3.12.14 and the absolute uv executable passed the frozen,
no-download setup. A signed S3 HEAD returned HTTP 200 for the shared
catalogue with its existing AWS authentication.

Run `9c5af141da8f4b8d85774ca08aefeb8e` acquired the claim at
01:02:50 UTC. Both `begin` and the post-hydration `next` returned
1.29.14. The validated PostgreSQL export dated 25 November 2026 at
18:15:42 UTC contained 3,170 passages and translations, and 202 accepted
pages. The exchange verified those pages. Supplemental reads verified
297 catalogue objects and cached files, including the existing cover.

*Five Attic triremes* shows a single close maritime painting beside
the continuous English reading. The [page plan](page_plan.md) compares
three compositions, the visual anchors 1.1.4 and 1.1.5, and actual
preceding pages 1.29.8–1.29.13. The [review](review.md) records the
native and thumbnail comparisons, the five padded fields, the exact
109-word translation at 62 px, and checks in the local HTML reader
and 204-page PDF.

The renderer, prompt, plan, and review were pushed and verified on
`origin/main` at `855a4f0e2fa958713b5b63c7acfe7208dd08a243`.
The exchange read back the final PNG and all five accompanying files,
including the component raster, and verified their SHA-256 and byte
counts. It conditionally checkpointed result
`d8f6637def504f479fe091f0e614a8a8` at 01:10:50 UTC. The catalogue
points to the 8,113,967-byte final PNG at SHA-256
`a112d8119f98d75c2ab3518506f4ebd3af83f1a0fe32aec80d9aca0f922419ec`.

The persisted replacement draw was `0.48483243929842845`. The exchange
reused that draw when recording `skipped`, with an empty target.
The new result is pending the next overnight PostgreSQL import and
website build on Raksasa.
