# Claude Code Maintainer Guide

This guide is written for engineers reading or changing this repository snapshot as a codebase, not as end users of the product.

## 1. The Correct Mental Model

Claude Code is not “a chat UI with some tools.”

It behaves more like a terminal-native agent runtime with these major layers:

1. Entry surfaces and startup routing
2. QueryEngine session state and turn construction
3. Model streaming and tool-use interpretation
4. Permission-gated tool orchestration
5. Transcript persistence and compaction
6. Extension surfaces: MCP, skills, hooks, plugins, remote/agent flows

When something looks confusing, the first question should be:

- is this behavior decided at startup
- during input normalization
- inside QueryEngine
- in the shared tool execution path
- or during persistence / compaction / resume

That classification usually narrows the search space quickly.

## 2. Read Order For New Maintainers

If you are new to the codebase, read these in roughly this order:

1. `src/entrypoints/cli.tsx`
2. `src/main.tsx`
3. `src/QueryEngine.ts`
4. `src/query.ts`
5. `src/services/tools/toolExecution.ts`
6. `src/services/tools/toolOrchestration.ts`
7. `src/utils/sessionStorage.ts`
8. `src/services/compact/compact.ts`
9. `src/services/mcp/client.ts`
10. `src/utils/hooks.ts`
11. `src/utils/plugins/pluginLoader.ts`

Why this order:

- `cli.tsx` and `main.tsx` explain startup branching and what “full runtime” actually means
- `QueryEngine.ts` and `query.ts` explain the core conversation loop
- `toolExecution.ts` explains the real trust boundary
- `sessionStorage.ts` and `compact.ts` explain why long-lived state works
- `mcp/client.ts`, `hooks.ts`, and `pluginLoader.ts` explain the extension pressure on the system

## 3. Snapshot-Level Facts

This repo snapshot contains:

- 1,902 analyzed source files under `src/`
- 513,237 lines of source
- 90 unique `feature(...)` flags
- 645 dynamic imports
- 86 command directories
- 42 directories under `src/tools`
- 104 hook-related files under `src/hooks`
- 23 files under `src/services/mcp`

Top directories by LOC:

- `utils/` — 180,487 LOC
- `components/` — 81,892 LOC
- `services/` — 53,683 LOC
- `tools/` — 50,863 LOC
- `commands/` — 26,528 LOC
- `ink/` — 19,859 LOC
- `hooks/` — 19,232 LOC

Largest files:

- `src/cli/print.ts`
- `src/utils/messages.ts`
- `src/utils/sessionStorage.ts`
- `src/utils/hooks.ts`
- `src/screens/REPL.tsx`
- `src/main.tsx`
- `src/utils/bash/bashParser.ts`
- `src/utils/attachments.ts`
- `src/services/api/claude.ts`
- `src/services/mcp/client.ts`

## 4. The Real Hotspots

The main engineering hotspots are not evenly distributed.

### `src/utils/`

This is the single most important structural smell in the snapshot.

- It is 35.2% of total analyzed LOC
- It contains cross-cutting runtime logic, not “helper” code
- It is where message shaping, hooks, session storage, shell parsing, plugins, auth, and permission logic accumulate

If you are planning refactors, this is the first place that wants clearer internal boundaries.

### `src/services/tools/` plus `src/tools/`

This is where safety, orchestration, product capability, and model agency meet.

- `toolExecution.ts` is the critical runtime file
- changes here can affect permissions, hooks, tool serialization, telemetry, and transcript shape
- Bash/PowerShell are especially sensitive because they add extra safety layers on top of the shared execution path

### `src/services/compact/` and `src/utils/sessionStorage.ts`

This is the continuity layer of the product.

- if this layer breaks, long-lived sessions stop feeling coherent
- compaction is not a secondary maintenance path; it is essential runtime behavior
- resume behavior, lite metadata, relinking, and summary boundaries are subtle and easy to regress

### `src/main.tsx`, `src/query.ts`, `src/QueryEngine.ts`

These files form the central runtime trunk.

- startup decisions live here
- context construction lives here
- model interaction and turn control live here

These are high-value reading targets and high-risk change targets.

## 5. How Common Changes Actually Flow

### Adding or changing a tool

Usually touch:

- `src/tools/<ToolName>/`
- `src/tools.ts`
- `src/services/tools/toolExecution.ts`
- sometimes permission helpers in `src/utils/permissions/`

Be careful about:

- validation behavior
- transcript-visible output shape
- permission prompts
- pre/post tool hooks
- serialization vs concurrency assumptions

### Changing permissions or trust behavior

Usually touch:

- `src/utils/permissions/filesystem.ts`
- `src/utils/permissions/pathValidation.ts`
- `src/utils/permissions/PermissionUpdate.ts`
- `src/services/tools/toolExecution.ts`

Be careful about:

- session vs persistent rules
- Windows vs Unix path behavior
- internal paths with special handling
- classifier-driven denials and hook retries

### Changing startup or product-mode behavior

Usually touch:

- `src/entrypoints/cli.tsx`
- `src/main.tsx`
- settings sources in `src/utils/settings/`
- feature checks

Be careful about:

- fast paths vs full runtime
- mode-specific initialization order
- auth/policy before UI
- dynamic import boundaries

### Changing session persistence or compaction

Usually touch:

- `src/utils/sessionStorage.ts`
- `src/services/compact/compact.ts`
- `src/services/compact/sessionMemoryCompact.ts`
- `src/services/compact/microCompact.ts`

Be careful about:

- transcript compatibility
- boundary markers and relinking
- resume behavior
- session title / lite metadata persistence
- automatic vs manual compaction paths

### Changing MCP, skills, hooks, or plugins

Usually touch:

- `src/services/mcp/`
- `src/tools/SkillTool/`
- `src/utils/hooks.ts`
- `src/utils/plugins/`
- `src/plugins/`
- `src/skills/`

Be careful about:

- what is discovered at startup vs loaded lazily
- what survives compaction
- whether capability is local, remote, plugin-provided, or MCP-provided
- how permission and hook semantics compose with those surfaces

## 6. Source-Backed Judgments

### What looks mature

- The runtime story is coherent from entrypoint to persistence.
- Tool safety is not hand-wavy; there is meaningful design around permission and shell risk.
- Session persistence and compaction show operational maturity.
- MCP and skill integration are substantive enough to shape the architecture.

### What looks structurally weak

- `utils/` has become too central.
- Several files are large enough that local reasoning becomes expensive.
- The codebase carries variant complexity through feature flags and dynamic import branching.
- Commands, tools, hooks, remote flows, skills, and plugins create surface-area risk faster than LOC alone suggests.

### What I would refactor first

- Split `utils/` into clearer domains: session, permissions, prompt/message shaping, plugin/skill surfaces, shell safety
- reduce the biggest hotspot files where state transitions and transcript shape are mixed together
- make extension-surface boundaries more explicit so MCP/plugins/skills/hooks do not all feel like they terminate in the same few central files

## 7. Debugging Map By Symptom

If you see this symptom, start here:

- Startup path seems wrong: `src/entrypoints/cli.tsx`, `src/main.tsx`
- Prompt context feels wrong: `src/QueryEngine.ts`, `src/query.ts`, `src/utils/systemPrompt.ts`
- Slash commands / attachments / history behave oddly: `src/utils/processUserInput/`, `src/history.ts`, `src/utils/messages.ts`
- Permission prompt is surprising: `src/services/tools/toolExecution.ts`, `src/utils/permissions/filesystem.ts`
- Bash or PowerShell safety issue: `src/tools/BashTool/`, `src/tools/PowerShellTool/`, `src/utils/bash/`
- Resume / title / transcript issue: `src/utils/sessionStorage.ts`
- Long session falls apart: `src/services/compact/compact.ts`, `src/services/compact/sessionMemoryCompact.ts`, `src/services/compact/microCompact.ts`
- MCP integration issue: `src/services/mcp/client.ts`, `src/services/mcp/auth.ts`, `src/services/mcp/config.ts`
- Skill / plugin behavior issue: `src/tools/SkillTool/`, `src/utils/plugins/`, `src/skills/`
- REPL/UI issue: `src/screens/REPL.tsx`, `src/components/`, `src/ink/`

## 8. Safe Working Practices

- Read the runtime path before changing shared utility code.
- Assume transcript shape changes are risky unless proven otherwise.
- Treat permission changes as product and security changes, not merely UX changes.
- Treat compaction changes as persistence changes, not merely token-saving changes.
- If a feature is gated, search the feature flag and the dynamic import path before editing.
- When a file feels “obviously central,” verify whether it is also on the persistence or permission path before touching it.

## 9. Git And Release Hygiene For This Snapshot

This project directory is now an independent Git repo boundary.

Included:

- `src/`
- `docs/`
- `README.md`
- `ANALYSIS_REPORT.md`
- `CODEBASE_ANALYSIS_REPORT.html`
- `USER_GUIDE.md`
- `MAINTAINER_GUIDE.md`
- `scripts/`

Ignored:

- `.venv-assets/`
- `.DS_Store`
- Python cache files

Before pushing:

- review `git status` from this directory, not from the home directory
- confirm generated assets under `docs/assets/` are the ones you want public
- decide whether you want both source scripts and generated outputs in the same commit
- if using GitHub Pages, `docs/index.html` is now ready to act as the landing page

## 10. Bottom Line

This snapshot is best described as a mature but increasingly monolithic runtime platform.

The most important insight for future maintainers is:

- the product’s complexity is not mainly in the UI
- it is in the runtime boundaries between startup, context construction, tool safety, persistence, compaction, and extension surfaces

If you keep that mental model, the codebase becomes much easier to navigate and much harder to accidentally oversimplify.
