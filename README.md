# Claude Code Source Analysis Bundle

This repository packages a deep source-level analysis of the Claude Code snapshot in `src/`, plus HTML reports, architecture visuals, GIF walkthroughs, and maintainer/user guides.

## Start Here

- Interactive HTML landing page: [`docs/index.html`](docs/index.html)
- Full Markdown analysis report: [`ANALYSIS_REPORT.md`](ANALYSIS_REPORT.md)
- Full HTML analysis report: [`docs/report.html`](docs/report.html)
- Root HTML report copy: [`CODEBASE_ANALYSIS_REPORT.html`](CODEBASE_ANALYSIS_REPORT.html)
- User-facing guide: [`USER_GUIDE.md`](USER_GUIDE.md)
- Engineering guide: [`MAINTAINER_GUIDE.md`](MAINTAINER_GUIDE.md)
- Visual assets: [`docs/assets/`](docs/assets/)

## How To Access The HTML Properly

GitHub's normal file browser shows `.html` files as source, not as rendered pages.

The cleanest way to view the HTML reports is to enable GitHub Pages for this repository:

1. Open `Settings` -> `Pages`
2. Under `Build and deployment`, choose `Deploy from a branch`
3. Select branch `main`
4. Select folder `/docs`
5. Save

After GitHub Pages is enabled, the rendered pages will be:

- `https://kejian-tong.github.io/claudecode-source/`
- `https://kejian-tong.github.io/claudecode-source/report.html`

## What This Bundle Covers

- A large source snapshot under `src/`
- An interactive documentation landing page under `docs/`
- A full HTML analysis report and a full Markdown analysis report
- Architecture diagrams, runtime GIFs, hotspot/risk visuals, and extension maps
- Separate user and maintainer guides

## Key Conclusions

- This is a product-scale terminal agent runtime, not a small CLI.
- The core looks shipped and mature; a large outer ring is gated, preview, or internal-only.
- The strongest areas are tool safety, session persistence, compaction, and extension architecture.
- The biggest liabilities are hotspot files, `utils/` centralization, and feature-flag complexity.

## Repository Layout

- `src/` — analyzed source snapshot
- `docs/` — landing page, HTML report, and visual assets
- `scripts/` — generators for diagrams and report assets

The root `README.md` is intentionally short. The detailed analysis now lives in [`ANALYSIS_REPORT.md`](ANALYSIS_REPORT.md).
