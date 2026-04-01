# Claude Code Source Capability Map

This file is a compact, source-only inventory of what the committed `src/`
snapshot clearly implements, what it gates behind build or product variants,
and what remains only partially inspectable in this bundle.

It deliberately avoids three things:

- inferring public release status from code structure alone
- mixing provenance or discovery-story claims into the technical verdict
- treating loose headline slogans as if they were exact repository metrics

## Scope And Method

- Only the committed snapshot under `src/` is used.
- "Implemented" means there is executable code, wired UI, service logic, or a
  clearly connected runtime path in this snapshot.
- "Gated" means the surface exists, but is controlled by `feature(...)`, build
  variants, entitlements, platform checks, or similar constraints.
- "Partial" means an entrypoint or reference exists, but the imported or
  backing subsystem is not fully present here.
- This file does not attempt to infer public rollout status, upstream
  repository lineage, or disclosure chronology.

## Measured Snapshot

- `1,902` source files under `src/`
- `513,237` lines of TS/TSX/JS/JSX
- `89` unique all-caps `feature('FLAG')` symbols by exact grep
- `941` total `feature('...')` call sites by exact grep
- `86` command surfaces
- `42` tool directories

Those counts are stable enough to headline because the counting rules are
explicit. They are preferable to vague categories like "runtime gates" unless
the counting method is disclosed.

## Broadly Implemented Runtime Spine

| Runtime area | Source evidence | Reading |
| --- | --- | --- |
| Session persistence + compaction | `src/utils/sessionStorage.ts`, `src/services/compact/compact.ts` | Long-lived transcript state is a first-class runtime substrate, not a thin chat wrapper. |
| Query + model orchestration | `src/QueryEngine.ts`, `src/services/api/claude.ts`, `src/main.tsx` | The central model loop is broad, stateful, and deeply integrated. |
| Permissioned tool execution | `src/tools/`, shell safety modules, hook plumbing, approval UI | Tool orchestration is one of the most mature and defended subsystems in the tree. |
| Remote sessions + CCR | `src/cli/`, remote transports, teleport flows, ingress logic | Remote execution is structural, not peripheral. |
| Extension plumbing | MCP, plugins, bundled skills, hooks, browser-facing tool surfaces | The codebase behaves like a runtime platform, not only a terminal UI. |
| Interactive UI + terminal surfaces | `src/screens/REPL.tsx`, `src/components/`, `src/ink/`, terminal panel utilities | The interactive shell application is a major part of the product surface. |

## Specialized Capability Families

These families are clearly implemented, but many of them are gated, scoped, or
not safe to describe as universal baseline behavior.

| Capability family | Source evidence | Best reading |
| --- | --- | --- |
| Buddy / companion | `src/buddy/`, `src/components/PromptInput/PromptInput.tsx`, `src/screens/REPL.tsx`, `src/utils/config.ts` | A substantial companion subsystem with explicit UI, persistence, and runtime behavior. |
| KAIROS family | `src/main.tsx`, `src/tools/BriefTool/BriefTool.ts`, `src/services/mcp/channelNotification.ts` | Large cross-cutting family spanning assistant mode, brief, proactive, and channels; strongly variant-driven. |
| Auto-Dream | `src/services/autoDream/` | Real background memory-consolidation subsystem with scheduler, locks, and completion logic. |
| UDS inbox + concurrent sessions | `src/tools.ts`, `src/main.tsx`, `src/utils/messages/systemInit.ts`, `src/utils/concurrentSessions.ts` | Real peer/session messaging surface behind a build flag. |
| Ultraplan + Ultrareview | `src/commands/ultraplan.tsx`, `src/utils/ultraplan/ccrSession.ts`, `src/commands/review/`, `src/services/api/ultrareviewQuota.ts` | Dedicated remote planning and review flows that already look product-shaped. |
| Voice mode | `src/services/voiceStreamSTT.ts`, prompt footer UI, REPL integration | Real speech-input surface, but explicitly gated by `VOICE_MODE`. |
| Claude in Chrome | `src/commands/chrome/chrome.tsx`, `src/utils/claudeInChrome/`, `src/services/mcp/client.ts` | Browser integration is implemented, not hypothetical. |
| Team memory + multi-agent coordination | `src/services/teamMemorySync/`, `src/tools/TeamCreateTool/`, multi-agent spawn paths | Real collaboration and memory stack, but variant- and entitlement-aware. |
| Computer Use + Advisor | `src/utils/computerUse/`, approval UI, advisor tool wiring in `src/services/api/claude.ts` | Deeply implemented, but platform- or product-slice-scoped rather than baseline-on. |

## Snapshot Limits

| Claim area | Why the snapshot is limited |
| --- | --- |
| Self-hosted runner + environment runner | `src/entrypoints/cli.tsx` contains real fast paths, but the imported implementation directories are not present in this snapshot. |
| Daemon-related modes | The snapshot clearly contains daemon workers, assistant daemon mode, and cron-related daemon behavior. It does not cleanly prove a broader always-on service story beyond those observed slices. |
| Public release status | Code structure can show implementation, gating, and platform scope. It cannot by itself prove whether something is publicly released, default-on, or customer-tier-limited. |
| Provenance / discovery story | Upstream lineage, exposure path, and discovery chronology are attribution questions, not source-structure findings. |

## Bottom Line

- This snapshot contains a mature core runtime, not a toy CLI.
- Around that core sits a large ring of specialized capabilities, many of them
  gated, scoped, or variant-driven.
- The safest source-backed language is "implemented", "gated", "scoped", and
  "partially inspectable" rather than "definitely public" or "fully shipped".

Use `docs/feature-atlas.html` for the rendered English page and
`docs/feature-atlas-zh.html` for the Chinese-first page with English
counterparts.
