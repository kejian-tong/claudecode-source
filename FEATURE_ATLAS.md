# Hidden / Gated Feature Atlas

This is the compact, source-backed version of the "hidden features" discussion around this snapshot.

It is stricter than social-media posters:

- implemented feature areas are separated from product-release claims
- gated or partial surfaces are marked as such
- unstable headline counts are called out as approximations unless the counting rule is explicit

## Bottom Line

- We already had the underlying analysis in `ANALYSIS_REPORT.md`, but not this compact atlas-style summary.
- The sample poster is directionally right about many surprising capabilities in the tree.
- It still overstates maturity in a few places and mixes together compile-time flags, runtime gates, and public-release assumptions.

## Metric Hygiene

- `1,902` source files under `src/`
- `513,237` lines of TS/TSX/JS/JSX
- `89` unique all-caps `feature('FLAG')` symbols by exact grep
- `941` total `feature('...')` call sites by exact grep

Two implications follow from that:

- Headline counts like `89 feature flags` are well-supported.
- Headline counts like `500+ runtime gates` or `47+ agent tools` depend heavily on counting methodology and should be labeled as approximations, not hard facts.

## Verdict On The Sample Poster

**Mostly correct in direction**

- BUDDY / companion
- KAIROS assistant-mode family
- Auto-Dream
- UDS inbox / cross-session messaging
- teleport / remote session transfer
- Ultraplan
- Ultrareview
- Voice mode
- Advisor
- Claude in Chrome
- Terminal Panel
- plugin / marketplace plumbing
- multi-agent swarm / coordinator surfaces

**Needs caveats**

- "Daemon" is too strong as written
- "Self-hosted runner" is only partially inspectable in this snapshot
- `500+ runtime gates` is not a stable, source-neutral metric
- provenance claims like "source leaked" are not code-structure findings

## Strongly Supported Claims

| Feature / claim | Source evidence | Best reading |
| --- | --- | --- |
| Buddy / companion pet system | `src/buddy/types.ts`, `src/buddy/CompanionSprite.tsx`, `src/components/PromptInput/PromptInput.tsx`, `src/screens/REPL.tsx`, `src/utils/config.ts` | Real implemented feature area. Strongly source-backed and gated behind `feature('BUDDY')`. The poster's "pet" framing is fair. |
| KAIROS assistant-mode family | `src/main.tsx`, `src/tools/BriefTool/BriefTool.ts`, `src/services/mcp/channelNotification.ts` | Real, large feature family. Includes assistant mode, brief, proactive, and channels, but clearly gated and variant-driven. |
| Auto-Dream memory consolidation | `src/services/autoDream/autoDream.ts`, `src/services/autoDream/consolidationPrompt.ts`, `src/services/autoDream/config.ts` | Real background memory-consolidation subsystem. The "dream" label is literal in the source. |
| UDS inbox / cross-session messaging | `src/tools.ts`, `src/main.tsx`, `src/utils/messages/systemInit.ts`, `src/utils/concurrentSessions.ts` | Real messaging and peer/session coordination surface behind `feature('UDS_INBOX')`. |
| Teleport / remote session transfer | `src/utils/teleport.tsx`, `src/main.tsx`, `src/services/api/sessionIngress.ts` | Real remote-session creation, transfer, and resume path. Strongly supported. |
| Ultraplan | `src/commands/ultraplan.tsx`, `src/utils/processUserInput/processUserInput.ts`, `src/utils/ultraplan/ccrSession.ts` | Real remote planning mode. The poster's "cloud planning" interpretation is directionally right. |
| Ultrareview | `src/commands/review.ts`, `src/commands/review/reviewRemote.ts`, `src/commands/review/ultrareviewEnabled.ts`, `src/services/api/ultrareviewQuota.ts` | Real remote review path with quota / billing logic. Strongly supported. |
| Voice mode | `src/services/voiceStreamSTT.ts`, `src/components/PromptInput/Notifications.tsx`, `src/components/PromptInput/PromptInputFooterLeftSide.tsx`, `src/screens/REPL.tsx` | Real voice/STT mode, but build-gated by `feature('VOICE_MODE')`. |
| Advisor | `src/utils/advisor.ts`, `src/commands/advisor.ts`, `src/services/api/claude.ts` | Real server-side advisor tool surface with model gating and dedicated result blocks. |
| Claude in Chrome | `src/commands/chrome/chrome.tsx`, `src/utils/claudeInChrome/setup.ts`, `src/services/mcp/client.ts`, `src/main.tsx` | Real browser integration surface with extension onboarding and in-process MCP support. |
| Terminal Panel | `src/utils/terminalPanel.ts` | Real built-in terminal sidecar toggled with `Meta+J`, with tmux persistence when available. |
| Plugin marketplace | `src/main.tsx`, `src/services/plugins/PluginInstallationManager.ts`, `src/commands/plugin/*` | Real marketplace and plugin distribution surface, not a stray placeholder. |
| Team memory (`TEAMMEM`) | `src/services/teamMemorySync/*`, `src/utils/claudemd.ts`, `src/utils/sessionFileAccessHooks.ts` | Real sync and memory-handling subsystem, but explicitly gated. |
| Coordinator / swarms | `src/main.tsx`, `src/utils/toolPool.ts`, `src/tools/TeamCreateTool/TeamCreateTool.ts`, `src/tools/shared/spawnMultiAgent.ts` | Real multi-agent team / coordinator machinery. The "swarm" framing is source-backed. |
| Computer Use MCP | `src/utils/computerUse/*`, `src/main.tsx`, `src/components/permissions/ComputerUseApproval/ComputerUseApproval.tsx` | Deep implementation exists, but it appears build- and platform-constrained rather than a universal default feature. |
| AFK / away summary | `src/services/awaySummary.ts`, `src/services/api/errors.ts` | Real "while you were away" recap behavior exists. The broad idea is correct. |

## Places Where The Poster Overstates Things

| Claim | Why it needs a caveat |
| --- | --- |
| `Daemon` as a fully general background service mode | I do **not** see a clean `feature('DAEMON')` product surface in this snapshot. I do see assistant daemon mode, daemon workers, and cron/SDK daemon references in `src/main.tsx` and `src/utils/cronScheduler.ts`. So the implementation direction is real, but the poster text is more confident than the source justifies. |
| `Self-hosted runner` as a finished inspectable subsystem | `src/entrypoints/cli.tsx` has a real `feature('SELF_HOSTED_RUNNER')` fast path for `claude self-hosted-runner`, but the imported `../self-hosted-runner/main.js` target is **not present in this snapshot**. So the entry path is real, but this repo snapshot does not let us inspect the full implementation. |
| `500+ runtime gates` as a hard number | This depends on whether you count only `feature(...)`, or also GrowthBook checks, auth checks, entitlement checks, environment checks, platform checks, and policy branches. It is not a stable single metric without a counting rule. |
| `Source leaked` as part of code analysis | That is a provenance/distribution claim, not a code-structure conclusion. The code can support "hidden feature" claims; it cannot by itself prove the external disclosure story. |

## Corrections To Specific Headline Numbers

- `89 feature flags`: supported by exact all-caps `feature('FLAG')` grep.
- `1,884 files / 512,000+ LOC`: directionally close, but this bundle's own measured snapshot is `1,902` files and `513,237` LOC.
- `70+ slash commands`: plausible in spirit, but our cleaner bundle metric is `86` command surfaces, which is broader than just slash commands.
- `47+ agent tools`: possible depending on what gets counted as an agent surface, but this is not one of the stable metrics I would lead with.

## My Final Judgment

If the question is "is this poster nonsense?", the answer is **no**.

If the question is "is it rigorous enough to publish as a source-backed technical summary without caveats?", the answer is **also no**.

The strongest corrected summary is:

- Claude Code's core runtime looks shipped and mature.
- Around that core sits a large ring of gated, preview, enterprise, ant-only, or build-variant functionality.
- The sample poster catches many real feature families, but it sometimes promotes "implemented and gated" into "definitely public and productized".

## Recommended Use

Use this file when you want the shortest rigorous answer.

Use `docs/feature-atlas.html` when you want the same conclusion in a one-page browser-friendly layout.
