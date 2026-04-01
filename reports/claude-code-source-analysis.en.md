# Claude Code Source Deep-Dive Report (English)

Target analyzed: `/Users/oliver/Desktop/claudecode-source` current source tree  
Analysis date: 2026-04-01  
Note: This report is based only on direct source inspection and codebase statistics from the current tree. The two PDFs provided by the user were not used as evidence.

## 1. Executive Summary

This codebase is not a thin command-line wrapper around a model API. It is a product-scale terminal agent runtime. Its real center of gravity is not "chat", but five infrastructure layers working together: tool orchestration, permission and sandbox enforcement, session/transcript persistence, context compaction and cache management, and multi-agent plus remote execution.

At implementation level, the key value of Claude Code does not come only from model invocation. It comes from the runtime built around the model. `src/query.ts`, `src/QueryEngine.ts`, `src/services/api/claude.ts`, `src/utils/messages.ts`, and `src/utils/sessionStorage.ts` form a long-lived session kernel. `src/Tool.ts`, `src/tools.ts`, and `src/services/tools/*` form a schedulable tool execution layer. `src/utils/permissions/*` and `src/utils/sandbox/sandbox-adapter.ts` implement defense in depth. `src/services/mcp/client.ts`, `src/utils/plugins/pluginLoader.ts`, and `src/skills/loadSkillsDir.ts` make MCP, plugins, and skills first-class platform features rather than peripheral add-ons.

My overall judgment is that this repository is closer to a stateful agent OS/runtime than to a single-turn CLI chatbot. It has already crossed into the territory of task systems, remote control, agent swarms, permission governance, and prompt-cache economics.

## 2. Method and Scope

- I directly analyzed 1,902 TypeScript/JavaScript files under `src/`, totaling about 513,237 lines of code.
- I read and cross-checked the major modules covering bootstrap, REPL/TUI, query loop, tool system, permissions, file and shell safety, API and prompt/cache handling, session storage, compaction and memory, multi-agent tasks, MCP/plugins/skills, and remote/bridge execution.
- I also gathered structure-level metrics: directory distribution, very large files, counts of command/tool/task directories, feature-flag counts, and React Compiler evidence.
- The current workspace does not include standard top-level metadata such as `package.json`, lockfiles, or build config, so this report focuses on runtime architecture rather than build reproducibility.

## 3. Quantitative Codebase Profile

- `src/utils`: 564 files, 180,487 lines. This is both utility code and a major container for core runtime logic.
- `src/components`: 389 files, 81,892 lines. The terminal UI is large and feature-dense.
- `src/services`: 130 files, 53,683 lines.
- `src/tools`: 184 files, 50,863 lines.
- `src/commands`: 207 files, 26,528 lines.
- `src/ink`: 96 files, 19,859 lines.
- `src/hooks`: 104 files, 19,232 lines.
- `src/bridge`: 31 files, 12,613 lines.

Within the current tree I found:

- 86 command directories.
- 42 tool directories.
- 5 task directories.
- 89 unique feature flags.
- 395 files importing `react/compiler-runtime`, which strongly suggests compiler-processed or artifact-influenced source output.

The largest hotspots are equally revealing:

- `src/cli/print.ts`: 5,594 lines.
- `src/utils/messages.ts`: 5,512 lines.
- `src/utils/sessionStorage.ts`: 5,105 lines.
- `src/utils/hooks.ts`: 5,022 lines.
- `src/screens/REPL.tsx`: 5,006 lines.
- `src/main.tsx`: 4,684 lines.
- `src/services/api/claude.ts`: 3,419 lines.
- `src/services/mcp/client.ts`: 3,348 lines.
- `src/utils/plugins/pluginLoader.ts`: 3,302 lines.

That distribution means the real complexity is concentrated in message normalization, session persistence, main orchestration, terminal interaction, API shaping, and plugin/MCP infrastructure.

## 4. Architectural Interpretation

From the way the tree is organized, Claude Code can be modeled as seven layers:

- Bootstrap and mode selection: CLI entrypoints, initialization, global state, routing into different runtime modes.
- Interaction and rendering: REPL, component tree, customized Ink/terminal rendering.
- Query execution: conversation loop, message flow, tool use, interruption/stop handling, retries and recovery.
- Capability execution: built-in tools, MCP tools, skills, commands, plugins.
- Safety and governance: permission rules, classifiers, path safety, shell safety, sandboxing.
- Session and context: message normalization, transcript persistence, compaction, memory, attachments, context assembly.
- Extension and distribution: multi-agent tasks, background execution, remote sessions, bridge, SDK/control protocols.

Those layers are not loosely stitched together. They are coupled by stable runtime objects: messages, tools, permission contexts, transcript records, and task state. The primary axis of the system is not the UI tree; it is stateful execution.

## 5. Bootstrap and Runtime Topology

The startup path clearly reflects a multi-mode product.

- `src/entrypoints/cli.tsx:126` and `src/entrypoints/cli.tsx:160` show that the CLI entrypoint can branch into bridge mode very early instead of always booting REPL first.
- `src/main.tsx:585` is the main runtime entrypoint, while `src/main.tsx:957`, `src/main.tsx:2597`, `src/main.tsx:3329`, `src/main.tsx:3467`, `src/main.tsx:4327`, and `src/main.tsx:4331` show that it also orchestrates managed settings, telemetry, remote session setup, and bridge delegation.
- `src/entrypoints/init.ts:247`, `src/entrypoints/init.ts:307`, and `src/entrypoints/init.ts:311` show that telemetry is intentionally initialized only after trust-sensitive startup work has completed.

This makes `main.tsx` much more than a simple command dispatcher. It is a high-responsibility startup coordinator for multiple deployment shapes. Another strong signal is `src/bootstrap/state.ts`, which centralizes a large amount of mutable runtime state. That improves convenience, but it also increases implicit coupling and raises the cost of reasoning about lifecycle behavior.

## 6. REPL, TUI, and Terminal Runtime

`src/screens/REPL.tsx` is large because REPL is a core business surface, not a shell wrapper.

- `src/replLauncher.tsx` lazy-loads REPL-related modules to reduce cold-start cost.
- `src/components/App.tsx` provides top-level context providers for state and performance statistics.
- `src/screens/REPL.tsx` handles input, message flow, permission prompts, remote sessions, background task navigation, history restore, notifications, and IDE/LSP coordination.
- `src/ink.ts` and `src/ink/ink.tsx` show that this is not stock Ink usage. The runtime customizes alternate screen handling, selection/search/highlighting, cursor behavior, render diffing, and performance tracking.

The product surface here is the terminal itself. Claude Code is implementing something much closer to a desktop-grade interface inside a terminal than a conventional line-based shell utility.

## 7. Query Loop and Message Kernel

The core execution path lives in `src/query.ts` and `src/QueryEngine.ts`.

- `src/query.ts:164` defines `MAX_OUTPUT_TOKENS_RECOVERY_LIMIT`, showing explicit recovery logic for max-output-token failures.
- `src/query.ts:563`, `src/query.ts:735`, and `src/query.ts:914` repeatedly construct `StreamingToolExecutor`, which means tool execution is embedded inside the streaming conversation loop rather than bolted on afterward.
- `src/query.ts:713` and `src/query.ts:719` tombstone orphaned messages, indicating that failed stream fragments are handled as consistency repair, not simply dropped.
- `src/query.ts:1382` wires `runTools(...)` directly into the main query loop, making tool calls a first-class state transition.

`src/QueryEngine.ts` looks like the headless/SDK-facing conversation kernel:

- `src/QueryEngine.ts:184` explicitly defines the reusable conversation engine abstraction.
- `src/QueryEngine.ts:451`, `src/QueryEngine.ts:609`, `src/QueryEngine.ts:728`, and `src/QueryEngine.ts:834` repeatedly call `recordTranscript(...)`, which means transcript persistence is on the critical path.
- `src/QueryEngine.ts:460`, `src/QueryEngine.ts:614`, `src/QueryEngine.ts:848`, `src/QueryEngine.ts:978`, and `src/QueryEngine.ts:1078` explicitly flush session storage at critical boundaries.

`src/utils/messages.ts` is the normalization and repair layer:

- `src/utils/messages.ts:1305` starts handling orphaned server-side tool uses.
- `src/utils/messages.ts:4980` starts filtering orphaned thinking-only assistant messages.
- `src/utils/messages.ts:5123` and `src/utils/messages.ts:5305` handle orphaned tool results and duplicate result cleanup.

The architectural implication is important: Claude Code treats message correctness as a runtime systems problem. It does not assume the model always produces perfectly aligned tool/message structures under interruption, retries, or replay.

## 8. The Tool System Is a Scheduler, Not a Wrapper

The tool layer behaves more like an execution framework than a simple function-calling adapter.

- `src/Tool.ts:123` defines `ToolPermissionContext` and `src/Tool.ts:158` defines `ToolUseContext`. Those objects carry permission state, app state, progress plumbing, and transcript-aware execution context.
- `src/Tool.ts:285`, `src/Tool.ts:416`, `src/Tool.ts:519`, and `src/Tool.ts:623` show that tools can specify interrupt behavior, permission acquisition, progress rendering, and per-thread content replacement state.
- `src/tools.ts:345` and `src/tools.ts:364` show `assembleToolPool(...)` merging built-in and MCP tools with deterministic ordering, clearly for prompt-cache stability.
- `src/services/tools/toolOrchestration.ts:19`, `src/services/tools/toolOrchestration.ts:36`, `src/services/tools/toolOrchestration.ts:66`, `src/services/tools/toolOrchestration.ts:118`, and `src/services/tools/toolOrchestration.ts:152` separate concurrency-safe execution from serial execution.
- `src/services/tools/toolExecution.ts:504`, `src/services/tools/toolExecution.ts:521`, `src/services/tools/toolExecution.ts:611`, `src/services/tools/toolExecution.ts:812`, and `src/services/tools/toolExecution.ts:1693` unify progress, final results, failures, and user interrupts.
- `src/services/tools/toolHooks.ts:40`, `src/services/tools/toolHooks.ts:194`, `src/services/tools/toolHooks.ts:336`, and `src/services/tools/toolHooks.ts:436` show pre-hook, post-hook, and failure-hook integration.

The result is that tools are not secondary capabilities bolted onto chat. They are the execution substrate.

## 9. Permissions, Path Safety, Shell Safety, and Sandbox

This is one of the biggest differentiators between Claude Code and a typical open-source agent CLI. Safety is layered, not singular.

Permission rules:

- `src/utils/permissions/permissions.ts:111` shows rule-source handling for `cliArg`, `command`, `session`, and other sources.
- `src/utils/permissions/permissions.ts:483` onward tracks denial state.
- `src/utils/permissions/permissions.ts:594`, `src/utils/permissions/permissions.ts:664`, and `src/utils/permissions/permissions.ts:854` show classifier-assisted auto mode plus fail-closed behavior.
- `src/utils/permissions/permissions.ts:1067` starts the core decision path, while `src/utils/permissions/permissions.ts:1262` and `src/utils/permissions/permissions.ts:1425` cover mode behavior, allow/ask/deny handling, and managed-rule-only tightening.

Dangerous permission stripping:

- `src/utils/permissions/permissionSetup.ts:94` defines dangerous Bash permission detection.
- `src/utils/permissions/permissionSetup.ts:240` defines dangerous Task permission detection.

Filesystem safety:

- `src/utils/permissions/filesystem.ts:95` treats `.claude/skills/...` specially.
- `src/utils/permissions/filesystem.ts:224` ensures Claude's own config files remain sensitive.
- `src/utils/permissions/filesystem.ts:1081`, `src/utils/permissions/filesystem.ts:1104`, and `src/utils/permissions/filesystem.ts:1124` carefully sequence read deny, read ask, and implicit read allow semantics.
- `src/utils/permissions/filesystem.ts:1219`, `src/utils/permissions/filesystem.ts:1252`, `src/utils/permissions/filesystem.ts:1303`, and `src/utils/permissions/filesystem.ts:1360` show write safety ordering, `.claude/**` session exceptions, safety-check precedence, and acceptEdits/sandbox shortcuts.
- `src/utils/permissions/filesystem.ts:1622`, `src/utils/permissions/filesystem.ts:1727`, and `src/utils/permissions/filesystem.ts:1771` allow selected internal runtime paths such as session memory, tasks, and bundled skill references.

Shell safety:

- `src/tools/BashTool/bashSecurity.ts:28`, `src/tools/BashTool/bashSecurity.ts:205`, `src/tools/BashTool/bashSecurity.ts:289`, `src/tools/BashTool/bashSecurity.ts:497`, `src/tools/BashTool/bashSecurity.ts:851`, `src/tools/BashTool/bashSecurity.ts:2247`, and `src/tools/BashTool/bashSecurity.ts:2286` show shell validation for `$()`, backticks, quoted heredocs, control characters, and multiline command semantics.
- `src/tools/BashTool/readOnlyValidation.ts:1876`, `src/tools/BashTool/readOnlyValidation.ts:1951`, and `src/tools/BashTool/readOnlyValidation.ts:1978` show that read-only auto-approval is tightly constrained.
- `src/tools/PowerShellTool/readOnlyValidation.ts:118`, `src/tools/PowerShellTool/readOnlyValidation.ts:1064`, and `src/tools/PowerShellTool/readOnlyValidation.ts:1168` show a parallel PowerShell read-only validation path rather than a Bash-only design.

Sandbox:

- `src/entrypoints/sandboxTypes.ts:12`, `src/entrypoints/sandboxTypes.ts:47`, `src/entrypoints/sandboxTypes.ts:91`, and `src/entrypoints/sandboxTypes.ts:117` define network and filesystem schema plus control over unsandboxed command escape hatches.
- `src/utils/sandbox/sandbox-adapter.ts:149`, `src/utils/sandbox/sandbox-adapter.ts:172`, and `src/utils/sandbox/sandbox-adapter.ts:181` convert Claude Code settings into sandbox-runtime configuration and support managed-domain-only behavior.
- `src/utils/sandbox/sandbox-adapter.ts:230` and `src/utils/sandbox/sandbox-adapter.ts:247` explicitly deny writes to `settings.json` and `.claude/skills` to prevent sandbox escape through config mutation.
- `src/utils/sandbox/sandbox-adapter.ts:302`, `src/utils/sandbox/sandbox-adapter.ts:330`, and `src/utils/sandbox/sandbox-adapter.ts:350` merge permission-rule-derived and sandbox-config-derived restrictions.
- `src/utils/sandbox/sandbox-adapter.ts:702`, `src/utils/sandbox/sandbox-adapter.ts:738`, and `src/utils/sandbox/sandbox-adapter.ts:775` show command wrapping, initialization, and live config updates.

The practical shape of the safety model is:

- Rule engine decides allow/deny/ask.
- Classifier narrows risk in auto mode.
- Path logic blocks dangerous internal locations.
- Shell semantic validation inspects command structure.
- OS sandbox enforces final filesystem and network restrictions.

This is true defense in depth.

## 10. File Tools Have a Wide Operational Surface

The file tools are much broader than simple text read/write utilities.

- `src/tools/FileReadTool/FileReadTool.ts:61` imports PDF handling, `src/tools/FileReadTool/FileReadTool.ts:59` imports notebook handling, and `src/tools/FileReadTool/FileReadTool.ts:50` imports image resizing.
- `src/tools/FileReadTool/FileReadTool.ts:181` warns on token-limit overages for large content.
- `src/tools/FileReadTool/FileReadTool.ts:470`, `src/tools/FileReadTool/FileReadTool.ts:484`, and `src/tools/FileReadTool/FileReadTool.ts:489` distinguish native PDF/image paths from blocked device-file reads.
- `src/tools/FileReadTool/FileReadTool.ts:904`, `src/tools/FileReadTool/FileReadTool.ts:991`, `src/tools/FileReadTool/FileReadTool.ts:1008`, `src/tools/FileReadTool/FileReadTool.ts:1089`, and `src/tools/FileReadTool/FileReadTool.ts:1142` show PDF page extraction, whole-PDF transfer, and token-budget-aware image compression.
- `src/tools/FileEditTool/FileEditTool.ts:345` and `src/tools/FileEditTool/FileEditTool.ts:493` show settings-file validation and LSP notifications on file change/save.

The file tools are therefore not just model affordances. They are system components integrated with permissions, token budgeting, and IDE/LSP behavior.

## 11. Prompt, System Prompt, and Cache Engineering

This is a particularly strong engineering area. Many agent projects treat prompts as static strings. This one does not.

- `src/constants/prompts.ts:114`, `src/constants/prompts.ts:115`, and `src/constants/prompts.ts:573` define and insert `SYSTEM_PROMPT_DYNAMIC_BOUNDARY`, clearly separating cacheable prefix from dynamic prompt material.
- `src/utils/api.ts:119` defines `toolToAPISchema(...)`; `src/utils/api.ts:223` can inject `defer_loading`; `src/utils/api.ts:338`, `src/utils/api.ts:364`, and `src/utils/api.ts:374` skip the boundary and split the system prompt into blocks.
- `src/services/api/claude.ts:1174`, `src/services/api/claude.ts:1231`, and `src/services/api/claude.ts:1237` show deferred tool handling when tool search is enabled.
- `src/services/api/claude.ts:1376` calls `buildSystemPromptBlocks(...)`.
- `src/services/api/claude.ts:3053`, `src/services/api/claude.ts:3112`, `src/services/api/claude.ts:3141`, `src/services/api/claude.ts:3164`, and `src/services/api/claude.ts:3213` manage `cache_edits` and `cache_reference` insertion with explicit deduplication and placement rules.
- `src/utils/forkedAgent.ts:51`, `src/utils/forkedAgent.ts:57`, `src/utils/forkedAgent.ts:131`, and `src/utils/forkedAgent.ts:489` show that forked agents are built around cache-safe parameters.
- `src/services/compact/microCompact.ts:335` and `src/services/compact/microCompact.ts:369` show that micro-compaction tries to preserve cached prefix semantics through cache edits instead of brute-force prompt rewrites.

The key implication is that prompt caching is a first-class architectural constraint. Tool ordering, system prompt segmentation, forked agents, and compaction all serve cache-hit stability and long-session economics.

## 12. Session Storage, Transcripts, Compaction, and Memory

This is another heart of the system.

- `src/utils/sessionStorage.ts:558`, `src/utils/sessionStorage.ts:622`, and `src/utils/sessionStorage.ts:841` show queueing plus timed and explicit flush behavior.
- `src/utils/sessionStorage.ts:1408` defines `recordTranscript(...)`.
- `src/utils/sessionStorage.ts:1583` exposes flush as an explicit operation.
- `src/utils/sessionStorage.ts:2098`, `src/utils/sessionStorage.ts:2171`, and `src/utils/sessionStorage.ts:2188` show orphaned sibling/tool-result recovery paths.
- `src/utils/sessionStorage.ts:3229` even documents append-only chain branching caused by rewind/ctrl-z scenarios.

Compaction and memory extend that persistence layer:

- `src/context.ts` injects git state, `CLAUDE.md`, and current date into runtime context.
- `src/services/compact/compact.ts`, `src/services/compact/autoCompact.ts`, and `src/services/compact/microCompact.ts` form the long-session compaction system.
- `src/services/SessionMemory/sessionMemory.ts` uses forked agents to extract session memory, which means memory itself is agentized and background-capable.

The product implication is that Claude Code is not a stateless per-turn chat client. It maintains an explicit history chain that can be persisted, repaired, summarized, forked, and replayed.

## 13. Multi-Agent, Background Tasks, and Team-Oriented Execution

Multi-agent support here is not a demo feature. It is a formal runtime capability backed by task infrastructure.

- `src/Task.ts:7-13` defines `local_bash`, `local_agent`, `remote_agent`, `in_process_teammate`, `local_workflow`, `monitor_mcp`, and `dream`.
- `src/tools/AgentTool/AgentTool.tsx:87`, `src/tools/AgentTool/AgentTool.tsx:96`, and `src/tools/AgentTool/AgentTool.tsx:99` show schema-level support for background execution, permission mode, and isolation mode.
- `src/tools/AgentTool/AgentTool.tsx:273`, `src/tools/AgentTool/AgentTool.tsx:278`, and `src/tools/AgentTool/AgentTool.tsx:361` explicitly restrict teammate nesting and certain background combinations, which is what a production task model looks like.
- `src/tools/AgentTool/AgentTool.tsx:567`, `src/tools/AgentTool/AgentTool.tsx:569`, `src/tools/AgentTool/AgentTool.tsx:577`, `src/tools/AgentTool/AgentTool.tsx:590`, and `src/tools/AgentTool/AgentTool.tsx:592` show that worker agents rebuild their own tool pool under their own permission context and can run inside isolated worktrees.
- `src/tools/AgentTool/runAgent.ts:315`, `src/tools/AgentTool/runAgent.ts:412`, `src/tools/AgentTool/runAgent.ts:721`, and `src/tools/AgentTool/runAgent.ts:844` show worktree awareness, permission mode override, cache-safe sharing, and cleanup of background shell tasks.
- `src/tasks/LocalAgentTask/LocalAgentTask.tsx:488`, `src/tasks/LocalAgentTask/LocalAgentTask.tsx:553`, `src/tasks/RemoteAgentTask/RemoteAgentTask.tsx:415`, and `src/tasks/RemoteAgentTask/RemoteAgentTask.tsx:422` show that local and remote agents are taskified, persisted, and user-visible.

This is consistent with a true agent platform, not a one-shot subroutine interface.

## 14. MCP, Plugins, and Skills: Extensibility as a Core Goal

MCP:

- `src/services/mcp/client.ts:9`, `src/services/mcp/client.ts:16`, and `src/services/mcp/client.ts:88` show support for SSE, streamable HTTP, and WebSocket transport.
- `src/services/mcp/client.ts:620`, `src/services/mcp/client.ts:673`, `src/services/mcp/client.ts:709`, `src/services/mcp/client.ts:783`, `src/services/mcp/client.ts:814`, and `src/services/mcp/client.ts:879` show full handling of auth, OAuth providers, proxies, TLS, and multiple transport variants.
- `src/services/mcp/client.ts:2315` and `src/services/mcp/client.ts:3201` show needs-auth caching and token-expiry recovery behavior.
- `src/entrypoints/mcp.ts:35`, `src/entrypoints/mcp.ts:59`, `src/entrypoints/mcp.ts:99`, `src/entrypoints/mcp.ts:150`, and `src/entrypoints/mcp.ts:192` show that Claude Code can itself expose its tools as an MCP server.

Plugins:

- `src/utils/plugins/pluginLoader.ts:5`, `src/utils/plugins/pluginLoader.ts:17`, and `src/utils/plugins/pluginLoader.ts:28` state marketplace, git-repo, and manifest-validation goals directly at the top of the file.
- `src/utils/plugins/pluginLoader.ts:121`, `src/utils/plugins/pluginLoader.ts:979`, and `src/utils/plugins/pluginLoader.ts:1101` show zip caching, manifest loading, and validation.
- `src/utils/plugins/pluginLoader.ts:1882`, `src/utils/plugins/pluginLoader.ts:1938`, and `src/utils/plugins/pluginLoader.ts:1961` show marketplace plugin resolution, enterprise policy filtering, and parallel loading.
- `src/utils/plugins/pluginLoader.ts:3096`, `src/utils/plugins/pluginLoader.ts:3137`, and `src/utils/plugins/pluginLoader.ts:3161` split full loading from cache-only loading for startup performance reasons.

Skills:

- `src/skills/loadSkillsDir.ts:133`, `src/skills/loadSkillsDir.ts:156`, and `src/skills/loadSkillsDir.ts:181` show skill frontmatter support for hooks, path scoping, model choice, and effort.
- `src/skills/loadSkillsDir.ts:447`, `src/skills/loadSkillsDir.ts:578`, `src/skills/loadSkillsDir.ts:771`, and `src/skills/loadSkillsDir.ts:986` show parsing, conditional activation, and dynamic activation.

The architectural conclusion is straightforward: extensibility is not an afterthought. MCP, plugins, skills, and commands are treated as core runtime concepts and are deeply integrated with permissions, startup cost management, and execution flow.

## 15. Remote Sessions, Bridge, and Control Protocols

This section further proves that Claude Code is not just a local CLI.

- `src/remote/RemoteSessionManager.ts:95`, `src/remote/RemoteSessionManager.ts:194`, `src/remote/RemoteSessionManager.ts:278`, `src/remote/RemoteSessionManager.ts:295`, and `src/remote/RemoteSessionManager.ts:310` show connection management, permission request forwarding, message sending, and interrupts for remote sessions.
- `src/bridge/bridgeMain.ts:1980` shows bridge as a major standalone runtime mode rather than a helper script.
- `src/cli/structuredIO.ts` and `src/entrypoints/sdk/controlSchemas.ts` define structured control paths and protocol schemas.
- `src/entrypoints/agentSdkTypes.ts:120`, `src/entrypoints/agentSdkTypes.ts:132`, `src/entrypoints/agentSdkTypes.ts:144`, `src/entrypoints/agentSdkTypes.ts:164`, `src/entrypoints/agentSdkTypes.ts:182`, `src/entrypoints/agentSdkTypes.ts:207`, `src/entrypoints/agentSdkTypes.ts:223`, `src/entrypoints/agentSdkTypes.ts:237`, `src/entrypoints/agentSdkTypes.ts:251`, `src/entrypoints/agentSdkTypes.ts:272`, and `src/entrypoints/agentSdkTypes.ts:442` are especially notable because many SDK-facing functions still throw `not implemented`.

My interpretation is that this source tree looks more like an internal or extracted Claude Code CLI/TUI runtime snapshot than a complete public SDK workspace. The evidence is:

- Public SDK surface shape exists, but many operational functions are placeholders.
- Standard build/package metadata is absent from the current tree.
- The real implementation mass is overwhelmingly on the CLI/TUI/runtime/bridge side rather than on a standalone SDK package surface.

## 16. The Strongest Engineering Qualities

- Long-lived sessions, tool execution, persistence correctness, permission flow, and cache-hit stability are treated as one architectural problem.
- Prompt-cache engineering is far more sophisticated than in most agent products.
- Safety is multi-layered rather than dependent on a single approval UI.
- Extensibility investment is substantial; MCP, plugins, and skills are not superficial.
- The system already has the shape of a remote-capable, multi-agent execution platform.

## 17. Main Risks and Technical Debt

- There are too many very large hotspot files: `main.tsx`, `REPL.tsx`, `messages.ts`, `sessionStorage.ts`, `api/claude.ts`, `cli/print.ts`, and `pluginLoader.ts` are all in high-maintenance territory.
- `src/bootstrap/state.ts` indicates heavy reliance on global mutable state, which increases implicit coupling and makes lifecycle regressions harder to reason about.
- `utils/` carries too much core logic, which suggests architectural drift in abstraction boundaries.
- The feature-flag surface is large: at least 89 visible flags, with high-frequency flags such as `KAIROS`, `TRANSCRIPT_CLASSIFIER`, `TEAMMEM`, `VOICE_MODE`, `BASH_CLASSIFIER`, `PROACTIVE`, `COORDINATOR_MODE`, and `BRIDGE_MODE`. That implies many live and experimental product branches coexisting in one code surface.
- The terminal rendering layer is highly customized, which improves product quality but increases cross-platform and rendering-regression complexity.
- The current snapshot lacks full build/test/package metadata, so external reproducibility and provenance are limited.

## 18. Final Conclusion

If Claude Code is described merely as "a command-line tool that calls Claude", that description materially understates what this codebase is.

A more accurate description is:

It is a terminal agent runtime platform built around a large model, whose value lies in embedding model capability into an execution system that is schedulable, permission-aware, recoverable, extensible, remote-capable, and multi-agent-capable.

Based on the source evidence, the real moat is not just good model wiring. It is that the system has already operationalized several difficult problems at once:

- Making tools part of stable execution semantics.
- Making long sessions sustainable in cost, cache behavior, persistence, and consistency.
- Making automation usable under layered permission, path, shell, and sandbox constraints.
- Unifying local, remote, plugin, MCP, skill, and multi-agent execution inside one runtime.

That is why the codebase reads much more like an agent OS inside a terminal than like a chat application.

## 19. Appendix: Key Source Anchors

- Bootstrap and modes: `src/entrypoints/cli.tsx:126,160`; `src/main.tsx:585,957,2597,3329,3467,4327,4331`; `src/entrypoints/init.ts:247,307,311`
- Query loop: `src/query.ts:164,563,713,719,1382`; `src/QueryEngine.ts:184,451,460,693,728,834,1078`
- Message repair: `src/utils/messages.ts:1305,4980,5123,5305`
- Session storage: `src/utils/sessionStorage.ts:558,622,841,1408,1583,2098,2171,3229`
- Tool framework: `src/Tool.ts:123,158,285,416,519,623`; `src/tools.ts:345,364`; `src/services/tools/toolOrchestration.ts:19,36,66,118,152`
- Permissions and filesystem: `src/utils/permissions/permissionSetup.ts:94,240`; `src/utils/permissions/permissions.ts:111,483,594,854,1067,1262,1425`; `src/utils/permissions/filesystem.ts:95,224,1081,1219,1252,1303,1622,1727,1771`
- Shell and sandbox: `src/tools/BashTool/bashSecurity.ts:28,289,497,851,2247,2286`; `src/tools/BashTool/readOnlyValidation.ts:1876,1951,1978`; `src/tools/PowerShellTool/readOnlyValidation.ts:118,1064,1168`; `src/entrypoints/sandboxTypes.ts:12,47,91,117`; `src/utils/sandbox/sandbox-adapter.ts:149,172,230,247,302,330,702,738,775`
- File tools: `src/tools/FileReadTool/FileReadTool.ts:61,181,470,484,904,991,1089`; `src/tools/FileEditTool/FileEditTool.ts:345,493`
- Prompt/cache: `src/constants/prompts.ts:114,573`; `src/utils/api.ts:119,223,338,364`; `src/services/api/claude.ts:1174,1231,1376,3053,3164,3213`; `src/utils/forkedAgent.ts:51,57,131,489`; `src/services/compact/microCompact.ts:335,369`
- Multi-agent and tasks: `src/Task.ts:7-13`; `src/tools/AgentTool/AgentTool.tsx:87,96,99,273,567,569,577,590,592`; `src/tools/AgentTool/runAgent.ts:315,412,721,844`; `src/tasks/LocalAgentTask/LocalAgentTask.tsx:488,553`; `src/tasks/RemoteAgentTask/RemoteAgentTask.tsx:415,422`
- MCP/plugins/skills: `src/services/mcp/client.ts:620,673,709,783,814,879,2315,3201`; `src/entrypoints/mcp.ts:35,59,99,150,192`; `src/utils/plugins/pluginLoader.ts:5,121,979,1882,1938,1961,3096,3137,3161`; `src/skills/loadSkillsDir.ts:133,156,181,447,771,986`
- Remote and SDK: `src/remote/RemoteSessionManager.ts:95,194,278,295,310`; `src/bridge/bridgeMain.ts:1980`; `src/entrypoints/agentSdkTypes.ts:120,132,144,164,182,207,223,237,251,272,442`
