# Claude Code Source Analysis Bundle

This repository packages a deep source-level analysis of the Claude Code snapshot in `src/`, plus HTML reports, architecture visuals, GIF walkthroughs, and maintainer/user guides.

## Provenance Note

Anthropic maintains an official public Claude Code repository at [`anthropics/claude-code`](https://github.com/anthropics/claude-code).

This repository is not that official Anthropic repository. It is an independent analysis, documentation, and visualization bundle built around the Claude Code source snapshot committed here under `src/`.

It does not claim affiliation with Anthropic, and it does not make claims about the provenance relationship between this snapshot and Anthropic's current upstream repository.

Around March 31, 2026, community and media coverage widely credited Chaofan Shou ([@Fried_rice on X](https://x.com/Fried_rice/status/2038894956459290963)) with publicly flagging the source-map exposure that drew attention to this code snapshot. This repository includes that attribution as a reference point, but does not independently verify "first discovery" priority claims.

## Start Here

- [Open interactive landing page](https://kejian-tong.github.io/claudecode-source/)
- [Open source capability map (English)](https://kejian-tong.github.io/claudecode-source/feature-atlas.html)
- [Open source capability map (中文)](https://kejian-tong.github.io/claudecode-source/feature-atlas-zh.html)
- [Open full HTML analysis report](https://kejian-tong.github.io/claudecode-source/report.html)
- [Read full Markdown analysis report](ANALYSIS_REPORT.md)
- [Read compact source capability summary](FEATURE_ATLAS.md)
- [Read user-facing guide](USER_GUIDE.md)
- [Read engineering guide](MAINTAINER_GUIDE.md)
- [Browse visual assets](docs/assets/)

## What This Bundle Covers

- A large source snapshot under `src/`
- An interactive documentation landing page under `docs/`
- A full HTML analysis report and a full Markdown analysis report
- Architecture diagrams, runtime GIFs, hotspot/risk visuals, and extension maps
- Separate user and maintainer guides

## Key Conclusions

- This is a product-scale terminal agent runtime, not a small CLI.
- The core runtime is deeply implemented and mature; a large outer ring is gated, preview, or internal-only.
- The strongest areas are tool safety, session persistence, compaction, and extension architecture.
- The biggest liabilities are hotspot files, `utils/` centralization, and feature-flag complexity.

## Repository Layout

- `src/` — analyzed source snapshot
- `docs/` — landing page, HTML report, and visual assets
- `scripts/` — generators for diagrams and report assets

The root `README.md` is intentionally short. The detailed analysis now lives in [`ANALYSIS_REPORT.md`](ANALYSIS_REPORT.md).
