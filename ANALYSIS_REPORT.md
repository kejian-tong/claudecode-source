# Claude Code Source Analysis Report

## Presentation Bundle

This repository snapshot now includes a small documentation bundle for GitHub browsing and GitHub Pages style presentation:

- `docs/index.html` — interactive landing page / source atlas
- `docs/report.html` — full HTML version of the analysis report
- `docs/assets/` — architecture diagrams, GIF walkthroughs, treemap, risk heatmap, lifecycle, and ecosystem visuals
- `USER_GUIDE.md` — user-facing explanation of how the runtime behaves
- `MAINTAINER_GUIDE.md` — engineering-facing guide for reading and changing the codebase

## Scope

This repository snapshot appears to contain only the `src/` tree. There is no package manifest, lockfile, build config, CI config, or test suite in the working directory, so this report is an analysis of the implementation source that is present, not the full delivery pipeline around it.

All findings below are grounded in the code under `src/`.

For source context, Anthropic officially distributes Claude Code through at
least its public GitHub repository and the public npm package
`@anthropic-ai/claude-code`. Community discussion around this snapshot has
generally described it as code recovered from official Anthropic-distributed
client artifacts, including bundled files and exposed source-map paths.

I treat that as contextual background, not a fully reconstructed provenance
chain. In particular, I do **not** assert a specific extraction workflow or
package-version claim unless it is independently verifiable from primary
sources. For example, the npm registry currently does not list
`@anthropic-ai/claude-code@2.1.88`, so that exact version label is not used
here as an established fact.

## Executive Summary

This is a large, production-grade TypeScript/Bun codebase for a terminal-first AI coding product. It is not a small CLI with a few commands. It is a product platform that combines:

- an interactive React/Ink REPL
- a headless SDK/structured I/O path
- a large tool-calling runtime
- an MCP client and MCP server surface
- agent spawning, teammate/swarm workflows, remote sessions, and worktree isolation
- plugins, skills, hooks, and marketplace distribution
- session persistence, compaction, and recovery
- enterprise policy, managed settings, sync, and telemetry infrastructure

The dominant architectural character is a pragmatic product monolith with strong extension points. The codebase is clearly optimized for shipping many features behind build/runtime gates while keeping startup fast and preserving security boundaries around shell execution, tool permissions, and external integrations.

It is impressive in breadth and operational maturity, but it also carries the usual costs of a long-lived platform monolith: very large hotspot files, soft module boundaries, a heavy `utils/` gravity well, substantial feature-flag variant complexity, and a lot of singleton/module-scope state.

My overall judgment is:

- Strong product-engineering codebase
- Security-conscious and performance-conscious
- Extension-heavy by design
- Harder to reason about than it should be in its current size
- In need of more explicit architectural boundaries and better verification coverage

## Product Design And UX Model

This codebase is best understood as a terminal-native operating environment, not
as a single chat screen with tools attached.

Three product-design choices are especially clear from the source:

### 1. The product is organized around workflow continuity

The runtime assumes users do not finish work in one short turn. That is why the
code invests so heavily in:

- transcript persistence
- resume and named sessions
- compaction and session-memory recovery
- background tasks and remote sessions
- terminal panel, IDE bridges, and browser-adjacent surfaces

The product design message is implicit but strong: preserve working context,
preserve task momentum, and let the session survive interruptions.

### 2. The interface is multi-surface, not single-surface

The same conceptual runtime is exposed through several distinct interaction
modes:

- interactive REPL/TUI
- headless structured I/O / SDK mode
- MCP server mode
- remote session and bridge flows
- IDE and browser-adjacent integrations

This is an important product-design fact. Claude Code is not designed as “the
CLI version” of something else. The terminal shell is one primary surface of a
broader runtime.

### 3. Human control is built into the experience model

The UX model is not “full autonomy first.” The source repeatedly routes through:

- permission prompts
- tool approvals
- policy checks
- pre/post hooks
- teammate permission mediation
- managed settings and enterprise controls

That makes the product feel less like an unconstrained agent and more like a
supervised execution environment where the user remains the final authority at
the trust boundary.

## Security Model And Trust Boundaries

The security work in this codebase is strong enough that it deserves to be read
as an architectural subsystem, not a grab bag of validations.

### Primary trust boundaries

The code enforces several distinct boundaries:

1. Model output vs runtime execution
2. Runtime vs local filesystem
3. Runtime vs shell invocation
4. Local process vs remote/MCP/plugin surfaces
5. Foreground session vs background agents/teammates
6. User settings vs remotely managed or enterprise policy inputs

That boundary thinking is visible across tools, permissions, hooks, MCP, and
session handling.

### How the defense-in-depth model works

The safety stack is layered rather than singular:

- schema validation on tool inputs and outputs
- permission modes and rule provenance
- parser-aware Bash and PowerShell validation
- read-only/path safety checks
- hook interception before and after tool execution
- approval UI for high-risk actions
- explicit managed-settings security review flows
- telemetry and audit-style state transitions around tool use

This is materially stronger than the “regex around shell commands” pattern that
many AI tool-runners stop at.

### Security posture by subsystem

- Shell tools: strongest and most mature security surface
- File tools: guarded by permission and path logic
- MCP/plugin surfaces: broader trust boundary, therefore more compatibility and policy risk
- Agent/team surfaces: safe in concept, but increase lifecycle and authority complexity
- Session storage: mostly operationally robust, but sensitive because it is the continuity substrate

### Residual security risks

The source still carries real risk areas:

- global/module-scope state can blur authority boundaries
- variant-heavy behavior makes exhaustive verification difficult
- extension surfaces widen the trusted-computing boundary
- giant hotspot files are harder to secure-review with confidence

## Engineering Practice And Delivery Maturity

Even from a partial snapshot, the engineering style is visible.

### What looks mature

- startup-performance discipline via fast paths, dynamic imports, and import ordering
- strong schema/type usage for settings, tools, MCP, and API payloads
- explicit compatibility handling in transcripts and persisted state
- operational instrumentation and analytics hygiene
- real attention to recovery paths, retries, and degraded-mode behavior

This is the engineering profile of a team that has already hit production-scale
edge cases.

### What looks incomplete or obscured by the snapshot

The snapshot does **not** include:

- tests worth evaluating as a verification system
- package manifests or lockfiles
- CI configuration
- release automation
- commit history showing architectural intent over time

That means I can assess implementation maturity much better than delivery
maturity. The code often looks production-hardened, but the full engineering
practice around build, release, and regression prevention is not fully visible
here.

### Engineering weaknesses visible from code alone

- hotspot files are too large for comfortable ownership
- `utils/` has become an application layer
- feature-flag branching increases path explosion
- compiler-transformed UI files reduce readability
- singleton/module-scope patterns raise coupling and teardown risk

## Feature Maturity Map

The earlier version of this report did **not** explicitly separate clearly shipped features from preview or future-facing ones.

This section is therefore an inference from source evidence, not a claim about external marketing or release history. The classification below is based on:

- whether a capability has normal command/UI/runtime paths
- whether it has broad supporting implementation across services, tools, and persistence
- whether the source explicitly marks it as `preview`, `experimental`, `ant-only`, `internal only`, or build/runtime gated

### Quick maturity table for notable gated features

| Feature family | Key source evidence | Best reading from source |
| --- | --- | --- |
| BUDDY / companion | `src/buddy/`, `PromptInput.tsx`, `REPL.tsx`, config/app state all reference it; runtime paths gated by `feature('BUDDY')` | Real implemented feature, but gated rather than universally on |
| Voice mode | `src/services/voiceStreamSTT.ts` says it is only reachable in builds gated by `feature('VOICE_MODE')` | Real implemented feature under rollout/build gating |
| KAIROS / Brief / Proactive / Channels | Large cross-cutting surface in `src/main.tsx`, commands, tools, and UI; repeatedly feature-gated | Major staged-release / variant family, not baseline behavior |
| TEAMMEM | `src/services/teamMemorySync/*` is substantial, but guarded by `feature('TEAMMEM')` | Real sync subsystem, but conditional rollout/build surface |
| Computer Use MCP | `src/utils/computerUse/*` plus CLI `--computer-use-mcp` entry path | Deep implementation, but platform/build constrained rather than default |
| PowerShell tool | Full `src/tools/PowerShellTool/*` exists; tip registry explicitly says `preview` | Implemented preview feature |
| Remote canonical skills | `src/tools/SkillTool/SkillTool.ts` labels them `ant-only experimental` | Experimental / limited-distribution surface |

### Clearly shipped / core product surfaces

These look like features that are already part of the main product shape in this snapshot:

- CLI + REPL interaction model
- headless structured I/O / SDK path
- transcript persistence, resume, and compaction
- permissioned tool runtime for file, shell, web, and MCP-backed execution
- plugin marketplace plumbing and skill execution
- hooks as a real product/runtime surface, not a hidden implementation detail

Why I classify them this way:

- they have broad implementation depth rather than single-file stubs
- they appear in startup, UI, runtime, and persistence layers
- they are treated as normal product surfaces in `main.tsx`, tool orchestration, and session storage code

### Preview / gated / phased-rollout surfaces

These look real, but not universally enabled or fully rolled out:

- Voice mode
- PowerShell tool
- BUDDY / companion pet surface
- KAIROS assistant mode and its related brief / channel / proactive surfaces
- Team memory sync (`TEAMMEM`)
- Agent triggers / scheduler surfaces
- remote canonical skills
- computer-use MCP surface

Why I classify them this way:

- `src/services/voiceStreamSTT.ts` says voice is only reachable in builds gated by `feature('VOICE_MODE')`
- `src/services/tips/tipRegistry.ts` explicitly labels the PowerShell tool as `preview`
- `src/buddy/` is a real feature area, but `PromptInput.tsx`, `REPL.tsx`, config, and app state all gate it behind `feature('BUDDY')`
- many KAIROS / PROACTIVE / TEAMMEM paths are marked `ant-only`, feature-gated, or GrowthBook-gated in `src/main.tsx`, `src/components/`, and `src/services/`
- `src/tools/SkillTool/SkillTool.ts` explicitly describes remote canonical skills as `ant-only experimental`
- `src/utils/computerUse/` and the `--computer-use-mcp` CLI path show a substantial implementation, but it is platform/build constrained rather than a universal surface

### Internal-only / future-facing / build-variant surfaces

These appear present in the codebase but not as universal public features:

- internal-only hooks or runtime shims
- research capture and some API metadata paths marked internal-only
- computer-use / special MCP channel capabilities that are runtime-gated
- some upsell- or entitlement-adjacent surfaces that appear in selective builds rather than the universal baseline

Why I classify them this way:

- `src/moreright/useMoreRight.tsx` explicitly says the real hook is internal only
- several API and analytics comments refer to ant-only or internal-only behavior
- some MCP channel and computer-use paths depend on experimental capabilities and gated builds
- BUDDY / companion is implemented deeply enough to be real, but still looks like a gated feature rather than an always-on core surface

### Bottom line on release status

The codebase does **not** look like “mostly unreleased software.” It looks like a shipped core product with a large experimental perimeter.

My best source-grounded reading is:

- the core runtime, session model, tool execution path, MCP base, skills, plugins, hooks, and resume/compact behavior are already productized
- a second ring of capabilities is under phased rollout, entitlement gating, or build-variant control
- a smaller ring is internal-only, experimental, or clearly future-facing

## Repository At A Glance

### High-level metrics

| Metric | Value |
| --- | ---: |
| Source files under `src/` | 1,902 |
| TS files | 1,332 |
| TSX files | 552 |
| JS files | 18 |
| Approx. source LOC (`.ts/.tsx/.js/.jsx`) | 513,237 |
| Top-level command entries under `src/commands` | 101 |
| Top-level tool directories under `src/tools` | 42 |
| `buildTool(...)` call sites | 40 |
| `dynamic import(...)` occurrences | 645 |
| `require(...)` occurrences | 277 |
| `type` declarations | 9,277 |
| `interface` declarations | 116 |
| `class` declarations | 188 |
| `TODO` markers | 138 |
| Files importing `react/compiler-runtime` | 395 |
| Exact all-caps `feature('FLAG')` symbols | 89 |
| Exact `feature('...')` call sites | 941 |

### Top folders by source size

| Folder | Files | LOC |
| --- | ---: | ---: |
| `utils` | 564 | 180,487 |
| `components` | 389 | 81,892 |
| `services` | 130 | 53,683 |
| `tools` | 184 | 50,863 |
| `commands` | 207 | 26,528 |
| `ink` | 96 | 19,859 |
| `hooks` | 104 | 19,232 |
| `bridge` | 31 | 12,613 |
| `cli` | 19 | 12,355 |
| `screens` | 3 | 5,980 |

### Largest files

| File | LOC |
| --- | ---: |
| `src/cli/print.ts` | 5,594 |
| `src/utils/messages.ts` | 5,512 |
| `src/utils/sessionStorage.ts` | 5,105 |
| `src/utils/hooks.ts` | 5,022 |
| `src/screens/REPL.tsx` | 5,005 |
| `src/main.tsx` | 4,683 |
| `src/utils/bash/bashParser.ts` | 4,436 |
| `src/utils/attachments.ts` | 3,997 |
| `src/services/api/claude.ts` | 3,419 |
| `src/services/mcp/client.ts` | 3,348 |
| `src/utils/plugins/pluginLoader.ts` | 3,302 |
| `src/commands/insights.ts` | 3,200 |

### Coupling signals

The strongest top-level internal import edges are:

| Edge | Count |
| --- | ---: |
| `utils -> utils` | 2,408 |
| `components -> components` | 1,021 |
| `components -> utils` | 871 |
| `tools -> utils` | 698 |
| `services -> utils` | 674 |
| `commands -> utils` | 362 |

This is the clearest structural signal in the repo: `utils/` is not just a helper folder. It is the shared substrate of the application.

## What This System Actually Is

At a product level, this codebase is a hybrid of:

- CLI application
- terminal UI framework
- conversational runtime
- tool execution engine
- agent orchestration layer
- extension platform
- enterprise integration surface

The major runtime surfaces are:

1. Interactive REPL/TUI
2. Headless structured I/O / SDK mode
3. MCP server mode
4. Remote session / bridge / assistant viewer modes

The result is not a layered CRUD app. It is a multi-surface interaction engine where the same core concepts recur everywhere:

- messages
- tools
- commands
- permissions
- sessions
- tasks
- settings
- hooks
- models
- agents

## Technology Stack

From the imports and architecture, the main stack appears to be:

- Runtime/build: Bun, with heavy use of `bun:bundle` feature gating
- Language: TypeScript
- TUI/UI: React + Ink
- CLI argument layer: Commander
- Validation: Zod
- Model integration: Anthropic SDK
- MCP: `@modelcontextprotocol/sdk`
- Networking: axios, ws, undici, SSE/WebSocket/stdio transports
- Telemetry: OpenTelemetry plus custom analytics sink
- Persistence: JSON/JSONL files under a Claude config home, plus sidecar metadata

One important observation: many React/Ink files in this snapshot already contain `react/compiler-runtime` artifacts. That suggests the repository snapshot includes React-compiler-transformed source or checked-in transformed output for at least part of the UI layer. That makes the code less pleasant to read than normal authored TSX.

## End-to-End Control Flow

### 1. Bootstrap entrypoint and fast-path dispatch

`src/entrypoints/cli.tsx` is a lean bootstrap dispatcher, not the whole app. It handles fast paths for things like:

- `--version`
- prompt dumping
- daemon/bridge/remote-control paths
- background session commands
- environment runner / self-hosted runner
- some worktree/tmux paths

This file is explicitly written to avoid loading the full application for cheap operations. That is a sign of mature startup-performance tuning.

### 2. Full app initialization

`src/main.tsx` is the real application bootstrap and one of the architectural centers of gravity. It does all of the following:

- startup profiling
- prefetching MDM and keychain work
- command registration
- config and policy loading
- auth/bootstrap fetching
- plugin/skill/tool initialization
- managed settings
- analytics setup
- model and permission initialization
- session restore / resume / teleport / remote setup

The comments in this file are unusually explicit about startup cost and import ordering. This is not accidental engineering. Startup latency is a first-class concern.

### 3. Interactive vs headless split

After initialization, the system forks into two main runtime styles:

- `src/screens/REPL.tsx` for the interactive terminal UI
- `src/cli/print.ts` for the headless structured output / SDK path

This split is important. The product is not “just a REPL” and not “just an SDK.” It is both, and the codebase has explicit machinery to make the core query/tool lifecycle reusable across both.

### 4. User input normalization

`src/utils/processUserInput/processUserInput.ts` handles user input as a multi-stage normalization pipeline:

- prompt mode vs command mode
- slash command parsing
- attachments and images
- IDE context
- ultraplan keyword handling
- hook execution
- query/no-query decision

This is more sophisticated than typical CLI command parsing. User input is treated as a rich event that can become messages, commands, attachments, or hook-triggered behavior before it ever reaches the model.

### 5. Query lifecycle

The core query flow lives in:

- `src/QueryEngine.ts`
- `src/query.ts`

`QueryEngine` is effectively the conversation/session owner for headless mode. It manages:

- mutable message history
- read-file state
- usage aggregation
- orphaned permission handling
- tool denial tracking
- turn-scoped skill discovery state

`query.ts` contains the lower-level turn loop:

- message normalization
- system/user context assembly
- model call execution
- tool round-tripping
- auto compaction / reactive compact / token budgets
- stop hooks and recovery paths

This split is sensible: one layer owns conversational state, the other owns a single query loop.

### 6. Tool execution

The tool runtime spans:

- `src/Tool.ts`
- `src/tools.ts`
- `src/services/tools/toolExecution.ts`
- `src/services/tools/toolOrchestration.ts`

This subsystem is one of the strongest parts of the codebase. It has:

- typed tool definitions
- input/output schemas
- permission mediation
- progress reporting
- telemetry
- concurrency partitioning
- context modification after tool calls
- MCP/resource/tool blending

The orchestration layer distinguishes concurrency-safe tool batches from serial tool batches. That is a strong design choice because it captures a real semantic property instead of merely “Promise.all everything.”

### 7. State and UI updates

Interactive state is managed through:

- `src/state/AppStateStore.ts`
- `src/state/AppState.tsx`
- `src/state/store.ts`
- `src/state/onChangeAppState.ts`

This is a custom external store approach, not Redux. The store is broad and application-centric, containing:

- settings
- permission context
- task state
- plugin state
- MCP state
- notifications
- speculation state
- bridge and remote session state
- teammate/team context
- history, attribution, todos, and more

It is a practical fit for a TUI app, but it is also a sign that the app state is very broad and spans too many domains.

### 8. Persistence and resume

`src/utils/sessionStorage.ts` is another architectural pillar. It manages:

- transcript paths
- JSONL persistence
- session metadata
- sidecar data
- worktree/session restore
- transcript reading limits
- compatibility with old transcript formats
- ephemeral progress filtering

This explains why resume, background sessions, remote tasks, and compaction can coexist. The session system is not superficial; it is a major subsystem.

## Subsystem Analysis

## Bootstrap, Startup, and Runtime Variants

This codebase is heavily optimized for startup cost and runtime variants.

Evidence:

- `src/entrypoints/cli.tsx` is mostly fast-path dispatch with dynamic imports.
- `src/main.tsx` explicitly overlaps expensive startup work like MDM reads and keychain prefetch.
- There are 645 dynamic imports and 277 `require(...)` calls across the repo.
- There are 89 exact all-caps `feature('FLAG')` symbols and 941 `feature('...')` call sites.

Interpretation:

- The team is intentionally minimizing cold-start work.
- Build variants matter a lot.
- The product surface has grown enough that dead-code elimination is an architectural tool, not a build detail.

The downside is complexity. Build-time behavior and runtime behavior are both variant-rich. That is powerful, but it makes the code harder to reason about statically.

## REPL, Ink, and Interaction Model

The UI layer is not a thin wrapper. `src/screens/REPL.tsx` alone is roughly 5,000 lines and imports from almost every major subsystem:

- input/history
- permissions
- tasks
- MCP
- hooks
- plugins
- IDE integration
- speculation
- voice
- cost tracking
- remote sessions
- session restore
- surveys/callouts/notifications

This is effectively the application shell for interactive mode.

Strengths:

- the REPL is clearly feature-rich
- the code supports many overlays and operational states
- AppState subscription patterns are reasonably optimized

Weaknesses:

- `REPL.tsx` is a hotspot and a maintenance risk
- the interactive shell knows too much about too many domains
- the compiler-transformed output style makes manual reasoning worse

This file is a prime candidate for further decomposition into domain-specific controllers.

## Query Engine and Conversation Runtime

The conversation runtime is structurally sound.

`src/QueryEngine.ts` frames the long-lived conversation/session state, while `src/query.ts` owns the lower-level turn loop. That separation is exactly what I would want in a product that must support both SDK/headless and UI modes.

What is notably good here:

- usage and budget accounting are first-class
- permission denials are tracked
- file-read state is cached and cloned carefully
- thinking configuration and system prompt assembly are explicit
- compact/snip/history edge cases are documented

This is not toy tool-calling code. It shows the scars of production incidents and long-running session behavior.

## Tooling Architecture

The tool system is a major strength.

`src/tools.ts` aggregates tool definitions with feature-gated inclusion rules. `src/Tool.ts` defines a rich tool contract and `ToolUseContext`. `src/services/tools/toolExecution.ts` and `toolOrchestration.ts` handle execution, permissions, hooks, progress, telemetry, and tool-result processing.

Important characteristics:

- tools are schema-validated
- tools can declare concurrency safety
- tool execution is richly instrumented
- tool execution integrates with hooks and permissions
- MCP tools and built-in tools coexist in a common pool

This is closer to a small tool execution platform than a typical CLI helper layer.

## Permissions and Shell Safety

This subsystem is probably the most operationally mature part of the codebase.

Relevant files include:

- `src/utils/permissions/permissionSetup.ts`
- `src/utils/permissions/permissions.ts`
- `src/tools/BashTool/bashSecurity.ts`
- `src/tools/BashTool/readOnlyValidation.ts`
- `src/tools/PowerShellTool/...`

What stands out:

- dangerous auto-mode permission rules are explicitly modeled
- Bash validation blocks command substitution, zsh-specific escape hatches, malformed tokens, and suspicious shell constructs
- read-only command validation is allowlist/flag-parser driven rather than naïve regex
- PowerShell gets separate treatment rather than being hand-waved
- the system thinks in terms of permission modes, allow/deny/ask rules, and source-specific rule provenance

This is serious security work. The code clearly reflects lessons learned from shell-tool exploitation paths.

## Agents, Tasks, and Teammates

The agent runtime is more advanced than “spawn a background task.”

Relevant files:

- `src/tools/AgentTool/AgentTool.tsx`
- `src/tasks/LocalAgentTask/LocalAgentTask.tsx`
- `src/tasks/RemoteAgentTask/RemoteAgentTask.tsx`
- `src/tasks/InProcessTeammateTask/...`
- `src/utils/swarm/inProcessRunner.ts`

The system supports:

- local agents
- remote agents
- in-process teammates
- background vs foreground behavior
- worktree isolation
- remote isolation
- permission mediation from leader to teammate
- progress summaries and notifications

This is a substantial orchestration layer. It also means concurrency, lifecycle, and cancellation semantics are everywhere.

Architecturally, this is powerful but costly. The agent/task abstractions are real, but they also drive a lot of cross-cutting state and message-routing complexity.

## MCP Integration

The MCP subsystem is broad and deeply integrated.

Relevant files:

- `src/services/mcp/client.ts`
- `src/services/mcp/config.ts`
- `src/services/mcp/MCPConnectionManager.tsx`
- `src/entrypoints/mcp.ts`

Capabilities include:

- stdio, SSE, streamable HTTP, and WebSocket transport support
- auth and step-up handling
- MCP tools, commands, and resources
- enable/disable/reconnect behavior
- config deduplication and policy filtering
- an MCP server mode that exposes Claude Code tools outward

This is significant because the product is not merely “MCP-compatible.” MCP is embedded into the architecture as a first-class extension and transport mechanism.

The complexity here is justified by the feature set, but `services/mcp/client.ts` is large enough that it deserves additional internal decomposition by concern:

- transport/session lifecycle
- auth/refresh/retry
- tool call normalization
- output persistence/truncation
- resource discovery

## Plugins and Marketplace System

The plugin system is also platform-level, not incidental.

Relevant files:

- `src/utils/plugins/pluginLoader.ts`
- `src/utils/plugins/marketplaceManager.ts`
- command and UI flows under `src/commands/plugin`

Capabilities include:

- plugin discovery from multiple sources
- marketplace declarations and caching
- versioned cache paths and seed caches
- zip cache extraction
- manifest validation
- settings/hook integration
- source allow/block policy
- background installation state

This is mature extension-platform engineering. The loader and marketplace code show real concern for:

- backwards compatibility
- cache reuse
- reproducibility
- policy enforcement
- safe filesystem behavior

The cost is that plugin behavior now intersects with commands, hooks, settings, MCP, LSP, and UI state. That coupling is already visible in the code.

## Skills and Hooks

The skill and hook subsystems are central to extensibility.

Relevant files:

- `src/skills/loadSkillsDir.ts`
- `src/skills/bundledSkills.ts`
- `src/utils/hooks.ts`
- generated/public hook surfaces in `src/entrypoints/sdk/coreTypes.ts`

Observations:

- skills can come from disk, bundled assets, plugins, and MCP
- bundled skills can lazily materialize reference files to disk safely
- hooks span many lifecycle events, not just pre/post command hooks
- the SDK exposes a serious hook/event surface

The hook event list includes:

- tool lifecycle
- prompt submission
- session start/end
- compact lifecycle
- permission events
- task events
- teammate idle
- config changes
- worktree events
- file changes

That is a strong extensibility story, but it creates another axis of behavior that is difficult to test exhaustively.

## Session Persistence, Recovery, and Compaction

This product is built around long-running sessions, not request/response stateless calls.

Relevant files:

- `src/utils/sessionStorage.ts`
- `src/services/compact/compact.ts`
- `src/services/compact/*`

The compaction subsystem is notable because it does more than summarize old messages. It understands:

- image/document stripping
- attachment reinjection
- skill and memory reinjection budgets
- post-compact cleanup
- transcript continuity
- prompt-too-long recovery behavior

This is real operational engineering for context-window management in production.

## API and Model Integration

`src/services/api/claude.ts` is large because it is doing real work:

- request shaping
- header/beta negotiation
- effort/thinking config resolution
- usage/cost tracking
- fallback/retry
- cache behavior
- streaming
- tool schema conversion
- first-party vs provider-specific behavior

This is not an SDK wrapper. It is a policy and orchestration layer around model invocation.

## LSP and IDE Integration

The LSP system is a smaller but important subsystem.

Relevant files:

- `src/services/lsp/manager.ts`
- `src/services/lsp/LSPServerManager.ts`
- `src/services/lsp/LSPServerInstance.ts`

It uses lazy singleton initialization, async startup, and plugin-aware reinitialization. That shows the codebase cares about code intelligence as part of the interactive environment rather than treating it as an optional bolt-on.

## Enterprise and Sync Services

Several services show clear enterprise/product-platform maturity:

- `src/services/remoteManagedSettings/index.ts`
- `src/services/settingsSync/index.ts`
- `src/services/teamMemorySync/index.ts`
- `src/remote/RemoteSessionManager.ts`

Patterns that recur:

- fail-open behavior when appropriate
- checksum/ETag or delta-based sync
- OAuth/API-key-aware auth behavior
- background polling with retry
- explicit security checks
- policy-aware enablement

This is the kind of infrastructure you only build when the CLI is already a serious product surface.

## Architectural Patterns

## 1. Feature-flag-first architecture

The codebase uses 89 exact all-caps `feature('FLAG')` symbols and 941 `feature('...')` call sites. The most common families are:

| Flag | Count |
| --- | ---: |
| `KAIROS` | 154 |
| `TRANSCRIPT_CLASSIFIER` | 107 |
| `TEAMMEM` | 51 |
| `VOICE_MODE` | 46 |
| `BASH_CLASSIFIER` | 45 |
| `KAIROS_BRIEF` | 39 |
| `PROACTIVE` | 37 |
| `COORDINATOR_MODE` | 32 |
| `BRIDGE_MODE` | 28 |
| `EXPERIMENTAL_SKILL_SEARCH` | 21 |
| `CONTEXT_COLLAPSE` | 20 |
| `KAIROS_CHANNELS` | 19 |

This is excellent for variant control and dead-code elimination, but it means architecture cannot be understood from a single runtime path alone.

## 2. Performance-aware lazy loading

The repo has a strong performance profile:

- dynamic imports are common
- fast paths are explicit
- startup comments are detailed and concrete
- heavy modules are deferred

This is a healthy sign. The team is clearly measuring and tuning startup cost.

## 3. Product monolith centered on `utils/`

`utils/` is effectively the internal platform layer. That can work, but here it has become a dependency gravity center.

Pros:

- fast feature development
- easy reuse
- fewer ceremony-heavy abstractions

Cons:

- boundaries become conventional rather than enforced
- “helper” modules accumulate domain logic
- import coupling becomes hard to untangle later

## 4. Strong schema and type orientation

With 9,277 `type` declarations and pervasive Zod use, the codebase is clearly type-driven.

That is a good fit for:

- tool schemas
- SDK surfaces
- plugin and marketplace manifests
- settings validation
- MCP payloads

## 5. Security-conscious shell/tool model

The shell and permissions model is one of the strongest architectural threads in the repo. It is not just “ask before running bash.” It contains layered analysis and path/flag validation logic.

## Strengths

## 1. Broad, coherent product scope

Despite its size, the repo does not feel random. The major subsystems line up with a clear product: interactive coding agent, extensible tool runtime, remote/enterprise-capable collaboration surface.

## 2. Strong operational realism

This codebase shows evidence of real production use:

- resume/recovery logic
- transcript compatibility handling
- size caps and OOM guards
- retry/backoff
- plugin and marketplace caches
- remote session polling
- prompt compaction and post-compact repair

## 3. Good security posture around dangerous capabilities

The shell/tool safety work is materially better than what most AI tool-runner codebases implement.

## 4. Serious extension model

Plugins, skills, hooks, MCP, agents, and SDK surfaces are all first-class. This is platform thinking, not just feature shipping.

## 5. Startup-performance discipline

The code is very obviously written by people who care about startup and interaction latency.

## 6. Telemetry and analytics hygiene

`src/services/analytics/index.ts` uses marker types to force explicit verification of telemetry-safe string data. That is a subtle but strong engineering move.

## Risks and Technical Debt

## 1. Oversized hotspot files

The largest files are large enough to be architecture risks, not just style issues.

Hotspots:

- `src/cli/print.ts`
- `src/utils/messages.ts`
- `src/utils/sessionStorage.ts`
- `src/utils/hooks.ts`
- `src/screens/REPL.tsx`
- `src/main.tsx`

These files are likely where change risk, onboarding cost, and bug regression risk concentrate.

## 2. `utils/` has become an application layer

This is the biggest structural smell in the repo. `utils/` is doing:

- domain logic
- orchestration
- persistence
- policy
- telemetry
- platform interop

That is workable until it stops being workable. The import-edge data suggests the repo is already well into that zone.

## 3. Variant complexity from feature flags

89 exact feature symbols and 941 call sites is not merely “configurable.” It means there are many effectively different products compiled from the same source tree. That increases:

- testing burden
- mental overhead
- dead-path rot risk
- integration risk when cross-flag behavior changes

## 4. Global/module-scope state

`src/bootstrap/state.ts`, singleton managers, caches, and module-level latches are practical, but they also create hidden coupling and subtle ordering concerns. In a codebase this large, that becomes expensive.

## 5. React-compiler-transformed files checked into the snapshot

395 files import `react/compiler-runtime`. That makes the UI layer less legible than authored TSX and raises the cost of code review and architecture analysis.

## 6. Verification gap in this snapshot

I found effectively no conventional test files in this repository snapshot. That does not prove the full project lacks tests, but it does mean this source snapshot does not visibly include them.

That matters because this codebase has:

- many runtime variants
- lots of feature gates
- shell safety rules
- remote/session recovery logic
- plugin marketplace logic

This kind of system benefits disproportionately from strong integration and regression tests.

## 7. Missing repository context

Because this snapshot only contains `src/`, important engineering context is absent:

- package/dependency pinning
- build steps
- lint/test commands
- CI
- contributor docs

That limits reproducibility and makes external analysis harder.

## Recommended Refactor Priorities

## Near-term

- Split `REPL.tsx`, `main.tsx`, `cli/print.ts`, `utils/sessionStorage.ts`, and `utils/hooks.ts` into controller/service modules with narrow ownership.
- Create architecture docs for the actual core runtime model: bootstrap, query loop, tool execution, persistence, remote/session flows.
- Add subsystem contract tests around permissions, shell safety, session restore, compaction, MCP config dedup, and plugin loading.
- Draw a clear line between “utility” code and “domain/platform” code. `utils/` is too broad.

## Mid-term

- Introduce explicit internal boundaries for session, tool, extension, and policy domains.
- Reduce direct `components -> utils` and `tools -> utils` dependency sprawl by routing through domain services.
- Isolate feature-flag branching closer to leaf modules so core flows have fewer variant branches.
- Separate transport concerns from policy concerns in large MCP and API modules.

## Longer-term

- Treat the platform as a set of bounded internal subsystems rather than a single source monolith.
- Invest in build-variant testing across the highest-risk feature-flag combinations.
- Consider keeping authored UI source and generated compiler output separate if both need to exist in-repo.

## Files To Read First

If I were onboarding an engineer to this codebase, I would have them read these in roughly this order:

1. `src/entrypoints/cli.tsx`
2. `src/main.tsx`
3. `src/QueryEngine.ts`
4. `src/query.ts`
5. `src/Tool.ts`
6. `src/tools.ts`
7. `src/services/tools/toolExecution.ts`
8. `src/services/tools/toolOrchestration.ts`
9. `src/state/AppStateStore.ts`
10. `src/screens/REPL.tsx`
11. `src/utils/sessionStorage.ts`
12. `src/utils/permissions/permissionSetup.ts`
13. `src/tools/BashTool/bashSecurity.ts`
14. `src/services/mcp/client.ts`
15. `src/utils/plugins/pluginLoader.ts`

That sequence gives a much faster picture of the system than reading by directory name.

## Final Thoughts

This is a serious codebase.

It is not elegant in the minimalistic sense, and it is not especially easy to hold in your head, but it is clearly solving hard real product problems:

- long-lived conversational state
- tool execution safety
- extension ecosystems
- remote collaboration
- enterprise policy and managed config
- startup latency
- session recovery

The repo’s biggest strengths are not stylistic. They are operational: safety, breadth, and hard-earned runtime behavior.

The repo’s biggest weakness is structural concentration. Too much responsibility lives in a handful of enormous files and in the broad, under-bounded `utils/` layer.

If this codebase were mine, I would not try to “rewrite it cleanly.” I would preserve its proven runtime behavior and invest in:

- boundary clarification
- hotspot decomposition
- higher-confidence regression coverage
- stronger architectural documentation

That would improve maintainability without sacrificing the real product maturity already present here.
