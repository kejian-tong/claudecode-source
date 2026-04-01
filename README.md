# Claude Code Source Analysis Bundle

This repository packages a deep source-level analysis of the Claude Code snapshot in `src/`, plus HTML reports, architecture visuals, GIF walkthroughs, and maintainer/user guides.

It also now includes an additional independently written source-analysis report in both Chinese and English, with Markdown and PDF outputs under `reports/`.

## Disclaimer And Intended Use

This repository is an independent analysis, documentation, and visualization bundle built for learning, research, technical commentary, and educational use.

It is not an official Anthropic repository, product release, or commercial distribution of Claude Code. Nothing in this repository should be read as granting any license, trademark permission, redistribution right, or commercial-use right to Anthropic-owned code, marks, or services.

If you want to use Claude Code commercially, operationally, or in production, use Anthropic's official channels, terms, and licenses instead of relying on this repository.

If you are a rights holder and believe something here should be corrected, limited, or removed, please contact the repository owner through GitHub.

## Official Channels And Source Context

Anthropic publicly distributes Claude Code through official channels, including:

- the official GitHub repository: [`anthropics/claude-code`](https://github.com/anthropics/claude-code)
- the official npm package: [`@anthropic-ai/claude-code`](https://www.npmjs.com/package/@anthropic-ai/claude-code)

This repository is separate from those official channels. It analyzes the source snapshot committed here under `src/` as a standalone technical artifact.

Community discussion around this snapshot has generally described it as source recovered from official Anthropic-distributed Claude Code client artifacts, including publicly shipped bundled files and exposed source-map paths. This repository treats that as contextual background, not as a fully reconstructed provenance chain.

This repository does not independently certify the exact extraction workflow, package version, or file-by-file provenance relationship between the committed `src/` tree and Anthropic's current upstream releases. It only states that Claude Code itself is officially distributed by Anthropic through the channels above.

In particular, this README does not repeat specific package-version claims unless they are independently verifiable from primary sources. For example, the npm registry currently does not list `@anthropic-ai/claude-code@2.1.88`, so that exact version label is not stated here as an established fact.

Around March 31, 2026, community reporting widely credited Chaofan Shou ([@Fried_rice on X](https://x.com/Fried_rice/status/2038894956459290963)) with publicly drawing attention to this snapshot. That attribution is included only as historical context, not as a source-code conclusion.

## Start Here

- [Open interactive landing page](https://kejian-tong.github.io/claudecode-source/)
- [Open source capability map (English)](https://kejian-tong.github.io/claudecode-source/feature-atlas.html)
- [Open source capability map (中文)](https://kejian-tong.github.io/claudecode-source/feature-atlas-zh.html)
- [Open full HTML analysis report](https://kejian-tong.github.io/claudecode-source/report.html)
- [Read full Markdown analysis report](ANALYSIS_REPORT.md)
- [Read independent Chinese source-analysis report](reports/claude-code-source-analysis.zh.md)
- [Read independent English source-analysis report](reports/claude-code-source-analysis.en.md)
- [Open Chinese PDF report](reports/claude-code-source-analysis.zh.pdf)
- [Open English PDF report](reports/claude-code-source-analysis.en.pdf)
- [Read compact source capability summary](FEATURE_ATLAS.md)
- [Read user-facing guide](USER_GUIDE.md)
- [Read engineering guide](MAINTAINER_GUIDE.md)
- [Browse visual assets](docs/assets/)

## What This Bundle Covers

- A large source snapshot under `src/`
- An interactive documentation landing page under `docs/`
- A full HTML analysis report and a full Markdown analysis report
- A separate independently written bilingual source-analysis report in `reports/`
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
- `reports/` — independent Chinese and English source-analysis reports in Markdown and PDF
- `scripts/` — generators for diagrams, report assets, and PDF export helpers

The root `README.md` is intentionally short. The detailed analysis now lives in [`ANALYSIS_REPORT.md`](ANALYSIS_REPORT.md).
