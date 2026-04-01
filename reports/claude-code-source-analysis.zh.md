# Claude Code 源码独立深度分析报告（中文）

分析对象：`/Users/oliver/Desktop/claudecode-source` 当前源码树  
分析日期：2026-04-01  
说明：本报告仅基于当前源码树的直接阅读、结构统计和模块交叉验证，不以用户提供的两份 PDF 作为证据来源。

## 1. 执行摘要

这份源码不是“给模型套一层命令行外壳”的轻量项目，而是一套产品级的终端 Agent 运行时。它的真正重心不是聊天 UI，而是五类基础设施：工具编排、权限与沙箱、会话与转录存储、上下文压缩与缓存、以及多代理与远程执行。

从实现层面看，Claude Code 的核心竞争力并不只来自模型调用，而是来自围绕模型构建出的运行时工程。`src/query.ts`、`src/QueryEngine.ts`、`src/services/api/claude.ts`、`src/utils/messages.ts`、`src/utils/sessionStorage.ts` 共同构成了“长生命周期会话内核”；`src/Tool.ts`、`src/tools.ts`、`src/services/tools/*` 构成了可调度的工具执行层；`src/utils/permissions/*` 与 `src/utils/sandbox/sandbox-adapter.ts` 构成了多层安全防线；`src/services/mcp/client.ts`、`src/utils/plugins/pluginLoader.ts`、`src/skills/loadSkillsDir.ts` 则把 MCP、插件、技能做成了一级能力，而不是附属扩展。

我的总体判断是：这份代码更接近“状态化 agent OS / runtime”而不是“单轮问答 CLI”。它已经显著超出了通用聊天应用的工程边界，进入了任务系统、远程控制、代理编队、权限治理和缓存经济学共同驱动的复杂软件系统范畴。

## 2. 研究方法与范围

- 直接分析了 `src/` 下 1,902 个 TypeScript/JavaScript 源文件，总计约 513,237 行代码。
- 重点通读和交叉验证的模块覆盖：启动链路、REPL/TUI、查询循环、工具系统、权限系统、文件与 shell 安全、API 与 prompt/cache、会话存储、压缩与记忆、多代理任务、MCP/插件/技能、远程会话与 bridge。
- 对代码库做了结构统计，包括目录分布、超大文件、命令/工具/任务目录数量、特性开关数量、React Compiler 产物痕迹等。
- 当前工作区未包含常规的 `package.json`、lockfile、构建配置等顶层元数据，因此本报告聚焦“运行时代码架构”而非构建链复现。

## 3. 代码库量化画像

- `src/utils`：564 个文件，180,487 行。这里既有基础工具，也承载了大量核心业务逻辑，显示出明显的“重心下沉到 utils”现象。
- `src/components`：389 个文件，81,892 行。终端 UI 体量很大，说明这不是只有输入框和输出流的简单 TUI。
- `src/services`：130 个文件，53,683 行。
- `src/tools`：184 个文件，50,863 行。
- `src/commands`：207 个文件，26,528 行。
- `src/ink`：96 个文件，19,859 行。
- `src/hooks`：104 个文件，19,232 行。
- `src/bridge`：31 个文件，12,613 行。

在当前树中可识别出：

- 86 个命令目录。
- 42 个工具目录。
- 5 个任务目录。
- 89 个唯一 feature flag。
- 395 个文件直接引用 `react/compiler-runtime`，说明这份源码树已经带有明显的编译优化/产物痕迹。

最大的几个热点文件也很说明问题：

- `src/cli/print.ts`：5,594 行。
- `src/utils/messages.ts`：5,512 行。
- `src/utils/sessionStorage.ts`：5,105 行。
- `src/utils/hooks.ts`：5,022 行。
- `src/screens/REPL.tsx`：5,006 行。
- `src/main.tsx`：4,684 行。
- `src/services/api/claude.ts`：3,419 行。
- `src/services/mcp/client.ts`：3,348 行。
- `src/utils/plugins/pluginLoader.ts`：3,302 行。

这组分布意味着系统的复杂度主要集中在“消息规范化、会话持久化、主流程编排、终端交互、API 适配、插件/MCP”六个方向。

## 4. 整体架构判断

从源码组织方式看，Claude Code 可以抽象成七层：

- 启动与模式选择层：CLI 入口、初始化、全局状态、模式路由。
- 交互与渲染层：REPL、组件树、定制化 Ink/终端渲染。
- 查询执行层：对话循环、消息流、工具调用、停止/中断、重试恢复。
- 能力执行层：内置工具、MCP 工具、技能、命令、插件。
- 安全治理层：权限规则、分类器、路径安全、shell 安全、沙箱。
- 会话与上下文层：消息规范化、转录存储、压缩、记忆、附件、上下文构建。
- 扩展与分布式层：多代理、后台任务、远程会话、bridge、SDK/control 协议。

这七层并不是松散拼装，而是通过稳定的数据结构耦合在一起。真正的“主线对象”不是界面组件，而是消息、工具、权限上下文、会话存储记录和任务状态。

## 5. 启动链路与运行时拓扑

启动路径非常典型地体现了“多模式产品”特征。

- `src/entrypoints/cli.tsx:126`, `src/entrypoints/cli.tsx:160` 表明 CLI 入口会在极早阶段把流程分流到 bridge 等专用模式，而不是无条件进入 REPL。
- `src/main.tsx:585` 是主运行时入口；`src/main.tsx:957`, `src/main.tsx:2597`, `src/main.tsx:3329`, `src/main.tsx:3467`, `src/main.tsx:4327`, `src/main.tsx:4331` 显示它同时负责任务化启动、远程会话配置、遥测、以及某些模式下再委派给 bridge。
- `src/entrypoints/init.ts:247`, `src/entrypoints/init.ts:307`, `src/entrypoints/init.ts:311` 表明初始化阶段会在“信任建立后”再启动遥测，并串联设置、证书、代理、受管配置等前置条件。

这说明主入口并不是一个“把用户输入送给模型”的薄层，而是一个具备多前置状态、多部署形态、多入口模式的产品启动器。另一个重要信号是 `src/bootstrap/state.ts` 的存在，它集中承载了大量运行时单例状态。优点是横向共享方便，缺点是状态边界变得更难推理，也提高了主流程的隐式耦合度。

## 6. REPL、TUI 与终端交互层

`src/screens/REPL.tsx` 的体量已经足以说明：REPL 是业务核心，不是 UI 壳。

- `src/replLauncher.tsx` 延迟加载 REPL 相关模块，减少冷启动开销。
- `src/components/App.tsx` 作为顶层 provider 汇总状态、性能统计、FPS 等上下文。
- `src/screens/REPL.tsx` 承接输入、消息流、权限提示、远程会话、后台任务导航、恢复历史、通知、IDE/LSP 协调等大量职责。
- `src/ink.ts` 和 `src/ink/ink.tsx` 不是简单使用社区 Ink，而是在其基础上做了更深的终端行为定制，包括 alternate screen、选择/搜索/高亮、光标管理、渲染差分与性能统计。

这个设计告诉我们，Claude Code 的“产品面”不是网页，而是终端本身。它在终端里实现了接近桌面应用的交互密度，因此 UI 层并不能独立看待，必须和任务状态、权限流、远程控制、转录存储一起理解。

## 7. 查询循环与消息内核

系统最核心的执行路径在 `src/query.ts` 和 `src/QueryEngine.ts`。

- `src/query.ts:164` 定义了 `MAX_OUTPUT_TOKENS_RECOVERY_LIMIT`，说明系统对模型“输出过长/被截断”的异常有专门恢复机制。
- `src/query.ts:563`, `src/query.ts:735`, `src/query.ts:914` 多次构造 `StreamingToolExecutor`，说明工具执行被视为流式会话的一部分，而不是后处理阶段。
- `src/query.ts:713`, `src/query.ts:719` 会 tombstone orphaned messages，意味着失败的流式片段不是简单丢弃，而是进入显式修复路径。
- `src/query.ts:1382` 把 `runTools(...)` 直接接到主查询循环上，说明工具调用是对话状态机内部的一等动作。

`src/QueryEngine.ts` 则更像头less/SDK 版本的会话内核：

- `src/QueryEngine.ts:184` 直接表明这是一个可复用的 conversation engine。
- `src/QueryEngine.ts:451`, `src/QueryEngine.ts:609`, `src/QueryEngine.ts:728`, `src/QueryEngine.ts:834` 多处调用 `recordTranscript(...)`，说明转录记录并不是外围日志，而是查询过程中的核心一致性步骤。
- `src/QueryEngine.ts:460`, `src/QueryEngine.ts:614`, `src/QueryEngine.ts:848`, `src/QueryEngine.ts:978`, `src/QueryEngine.ts:1078` 多次显式 flush session storage，说明系统把“持久化时机”当作执行正确性的一部分来处理。

配套地，`src/utils/messages.ts` 是消息标准化与修复层：

- `src/utils/messages.ts:1305` 起处理 orphaned server tool use。
- `src/utils/messages.ts:4980` 起专门过滤 orphaned thinking-only assistant messages。
- `src/utils/messages.ts:5123`, `src/utils/messages.ts:5305` 起处理 orphaned tool_result 与重复结果去重。

这里最关键的工程特征是：Claude Code 把“消息一致性”做成了一套严肃的运行时问题。它不是简单相信模型永远按协议输出，而是为中断、流式失败、工具错配、恢复播放等情况建立了大量修复逻辑。

## 8. 工具系统不是附属层，而是调度内核

Claude Code 的工具系统更像调度框架，不像普通 function calling 包装器。

- `src/Tool.ts:123` 定义 `ToolPermissionContext`，`src/Tool.ts:158` 定义 `ToolUseContext`。这两个上下文对象横跨权限、状态、进度、AppState、转录等多维信息。
- `src/Tool.ts:285`, `src/Tool.ts:416`, `src/Tool.ts:519`, `src/Tool.ts:623` 说明一个工具对象不仅有输入/输出 schema，还有中断行为、权限上下文获取、进度 UI、上下文替换状态等更丰富的生命周期接口。
- `src/tools.ts:345`, `src/tools.ts:364` 的 `assembleToolPool(...)` 会把内置工具与 MCP 工具合并后排序，明显是在为 prompt cache 稳定性服务。
- `src/services/tools/toolOrchestration.ts:19`, `src/services/tools/toolOrchestration.ts:36`, `src/services/tools/toolOrchestration.ts:66`, `src/services/tools/toolOrchestration.ts:118`, `src/services/tools/toolOrchestration.ts:152` 表明系统会区分可并发执行与必须串行执行的工具。
- `src/services/tools/toolExecution.ts:504`, `src/services/tools/toolExecution.ts:521`, `src/services/tools/toolExecution.ts:611`, `src/services/tools/toolExecution.ts:812`, `src/services/tools/toolExecution.ts:1693` 则把进度、最终结果、异常、用户中断统一编排。
- `src/services/tools/toolHooks.ts:40`, `src/services/tools/toolHooks.ts:194`, `src/services/tools/toolHooks.ts:336`, `src/services/tools/toolHooks.ts:436` 说明前置 hook、后置 hook、失败 hook 都被纳入统一生命周期。

结论是：工具系统在 Claude Code 里不是模型调用的补充，而是执行语义的中心。真正复杂的地方不是“让模型会调工具”，而是“如何让工具在一个长期会话、可恢复、可持久化、可授权、可并发的系统里运行”。

## 9. 权限、路径安全、shell 安全与沙箱

这一层是 Claude Code 与大量开源 agent CLI 最本质的差异之一。它不是单点防护，而是多层叠加。

权限规则层：

- `src/utils/permissions/permissions.ts:111` 显示规则来源至少覆盖 `cliArg`、`command`、`session` 等；结合代码可见还包括 policy/project/local 等来源。
- `src/utils/permissions/permissions.ts:483` 起维护 denial tracking。
- `src/utils/permissions/permissions.ts:594`, `src/utils/permissions/permissions.ts:664`, `src/utils/permissions/permissions.ts:854` 表明 auto mode 下还会配合分类器与 fail-closed 策略。
- `src/utils/permissions/permissions.ts:1067` 起是核心决策入口，`src/utils/permissions/permissions.ts:1262` 起进入模式、allow 规则和 ask/deny 转换逻辑，`src/utils/permissions/permissions.ts:1425` 起还支持“只允许受管规则”的收紧模式。

危险权限剥离与计划模式：

- `src/utils/permissions/permissionSetup.ts:94` 定义危险 Bash 权限识别。
- `src/utils/permissions/permissionSetup.ts:240` 定义危险 Task 权限识别。

文件系统安全：

- `src/utils/permissions/filesystem.ts:95` 起对 `.claude/skills/...` 做细粒度特判。
- `src/utils/permissions/filesystem.ts:224` 明确 Claude 自身配置文件默认需要额外确认。
- `src/utils/permissions/filesystem.ts:1081`, `src/utils/permissions/filesystem.ts:1104`, `src/utils/permissions/filesystem.ts:1124` 把 read deny、read ask、隐式 read allow 的先后顺序写得非常谨慎。
- `src/utils/permissions/filesystem.ts:1219`, `src/utils/permissions/filesystem.ts:1252`, `src/utils/permissions/filesystem.ts:1303`, `src/utils/permissions/filesystem.ts:1360` 体现了写权限判定中的 deny、session 级 `.claude/**` 特例、安全检查优先级与 acceptEdits/sandbox mode 快速通道。
- `src/utils/permissions/filesystem.ts:1622`, `src/utils/permissions/filesystem.ts:1727`, `src/utils/permissions/filesystem.ts:1771` 说明 session-memory、tasks、bundled skill references 等内部路径有专门 allowlist。

Shell 安全：

- `src/tools/BashTool/bashSecurity.ts:28`, `src/tools/BashTool/bashSecurity.ts:205`, `src/tools/BashTool/bashSecurity.ts:289`, `src/tools/BashTool/bashSecurity.ts:497`, `src/tools/BashTool/bashSecurity.ts:851`, `src/tools/BashTool/bashSecurity.ts:2247`, `src/tools/BashTool/bashSecurity.ts:2286` 显示 Bash 安全并非字符串黑名单，而是专门处理 `$()`、反引号、quoted heredoc、控制字符与多行语义的组合验证。
- `src/tools/BashTool/readOnlyValidation.ts:1876`, `src/tools/BashTool/readOnlyValidation.ts:1951`, `src/tools/BashTool/readOnlyValidation.ts:1978` 显示只读自动放行也经过严格判定。
- `src/tools/PowerShellTool/readOnlyValidation.ts:118`, `src/tools/PowerShellTool/readOnlyValidation.ts:1064`, `src/tools/PowerShellTool/readOnlyValidation.ts:1168` 表明 PowerShell 路径并不是缺席，而是做了近似对等的只读校验体系。

沙箱层：

- `src/entrypoints/sandboxTypes.ts:12`, `src/entrypoints/sandboxTypes.ts:47`, `src/entrypoints/sandboxTypes.ts:91`, `src/entrypoints/sandboxTypes.ts:117` 定义了网络、文件系统、是否允许 unsandboxed commands 等完整 schema。
- `src/utils/sandbox/sandbox-adapter.ts:149`, `src/utils/sandbox/sandbox-adapter.ts:172`, `src/utils/sandbox/sandbox-adapter.ts:181` 把 Claude Code 设置映射成 sandbox runtime 配置，并能施加 managed-domain-only 策略。
- `src/utils/sandbox/sandbox-adapter.ts:230`, `src/utils/sandbox/sandbox-adapter.ts:247` 会显式拒绝写 `settings.json` 和 `.claude/skills`，防止通过沙箱内写配置实现权限逃逸。
- `src/utils/sandbox/sandbox-adapter.ts:302`, `src/utils/sandbox/sandbox-adapter.ts:330`, `src/utils/sandbox/sandbox-adapter.ts:350` 还会从 permission rules 和 sandbox.filesystem 配置中综合提取网络与文件系统限制。
- `src/utils/sandbox/sandbox-adapter.ts:702`, `src/utils/sandbox/sandbox-adapter.ts:738`, `src/utils/sandbox/sandbox-adapter.ts:775` 说明命令包装、初始化和设置热更新都能进入沙箱管理器。

综合来看，这套安全系统的真实结构是：

- 规则层决定 allow / deny / ask。
- 分类器层在 auto mode 下进一步缩窄风险面。
- 路径层拦截危险目录与内部元数据位置。
- shell 语义层解析命令结构。
- OS 沙箱层再做文件系统与网络的最终限制。

这是一套标准的 defense-in-depth，而不是单层提示框。

## 10. 文件工具的能力边界很宽

文件读写工具远不只是普通文本读写。

- `src/tools/FileReadTool/FileReadTool.ts:61` 引入 PDF 读取，`src/tools/FileReadTool/FileReadTool.ts:59` 引入 notebook 读取，`src/tools/FileReadTool/FileReadTool.ts:50` 引入图像缩放。
- `src/tools/FileReadTool/FileReadTool.ts:181` 对超大文本做 token 上限提示。
- `src/tools/FileReadTool/FileReadTool.ts:470`, `src/tools/FileReadTool/FileReadTool.ts:484`, `src/tools/FileReadTool/FileReadTool.ts:489` 对图片/PDF 的原生处理与 device file 阻断做了区分。
- `src/tools/FileReadTool/FileReadTool.ts:904`, `src/tools/FileReadTool/FileReadTool.ts:991`, `src/tools/FileReadTool/FileReadTool.ts:1008`, `src/tools/FileReadTool/FileReadTool.ts:1089`, `src/tools/FileReadTool/FileReadTool.ts:1142` 表明 PDF 页图抽取、整 PDF 传递、图像 token 预算压缩都已经纳入正式流程。
- `src/tools/FileEditTool/FileEditTool.ts:345`, `src/tools/FileEditTool/FileEditTool.ts:493` 则说明写文件不仅有设置文件额外校验，还会主动通知 LSP server 做 didChange / didSave。

从这里能看到 Claude Code 的一个重要设计哲学：文件工具不仅是“提供给模型的能力”，也是“和 IDE/LSP/权限/上下文预算联动的系统组件”。

## 11. Prompt、系统提示与缓存工程

这一部分是 Claude Code 很强的工程特色。很多项目把 prompt 当静态字符串，这里不是。

- `src/constants/prompts.ts:114`, `src/constants/prompts.ts:115`, `src/constants/prompts.ts:573` 定义并插入了 `SYSTEM_PROMPT_DYNAMIC_BOUNDARY`，明显是在把系统提示拆成可缓存前缀与动态部分。
- `src/utils/api.ts:119` 的 `toolToAPISchema(...)` 不只是把工具 schema 转成 API 结构；`src/utils/api.ts:223` 还会按需加入 `defer_loading`；`src/utils/api.ts:338`, `src/utils/api.ts:364`, `src/utils/api.ts:374` 会跳过 boundary 并拆分 system prompt block。
- `src/services/api/claude.ts:1174`, `src/services/api/claude.ts:1231`, `src/services/api/claude.ts:1237` 表明在启用 tool search 时会把部分工具转成 deferred tool。
- `src/services/api/claude.ts:1376` 调用 `buildSystemPromptBlocks(...)`。
- `src/services/api/claude.ts:3053`, `src/services/api/claude.ts:3112`, `src/services/api/claude.ts:3141`, `src/services/api/claude.ts:3164`, `src/services/api/claude.ts:3213` 说明 API 层会注入 `cache_edits` 与 `cache_reference`，并且非常小心地处理去重和插入位置。
- `src/utils/forkedAgent.ts:51`, `src/utils/forkedAgent.ts:57`, `src/utils/forkedAgent.ts:131`, `src/utils/forkedAgent.ts:489` 说明 forked agent 也围绕 cache-safe 参数构建。
- `src/services/compact/microCompact.ts:335`, `src/services/compact/microCompact.ts:369` 说明 micro compact 会尽量通过 cache-edit 语义删掉历史块，而不是粗暴重写整个上下文。

这背后的含义非常重要：Claude Code 把 prompt caching 视为一级架构约束，而不是性能优化的附加项。工具排序、system prompt 边界、forked agent、micro compact 都在围绕“如何让缓存命中率、上下文稳定性和长会话可持续性更好”服务。

## 12. 会话存储、转录、压缩与记忆

如果只看聊天界面，很容易低估这部分的重要性；但从源码体量看，这其实是系统的另一颗心脏。

- `src/utils/sessionStorage.ts:558`, `src/utils/sessionStorage.ts:622`, `src/utils/sessionStorage.ts:841` 表明会话存储本身就有队列、定时 flush 和显式 flush 机制。
- `src/utils/sessionStorage.ts:1408` 是 `recordTranscript(...)` 的核心入口。
- `src/utils/sessionStorage.ts:1583` 说明 flush session storage 是独立可调用的操作。
- `src/utils/sessionStorage.ts:2098`, `src/utils/sessionStorage.ts:2171`, `src/utils/sessionStorage.ts:2188` 显示其专门处理 orphaned sibling/tool_result 恢复。
- `src/utils/sessionStorage.ts:3229` 还考虑到了 rewind/ctrl-z 造成的 append-only 链分叉。

上下文压缩和记忆则进一步扩展了这条链：

- `src/context.ts` 负责把 git 状态、`CLAUDE.md`、当前日期等注入系统上下文。
- `src/services/compact/compact.ts`、`src/services/compact/autoCompact.ts`、`src/services/compact/microCompact.ts` 共同构成长会话压缩体系。
- `src/services/SessionMemory/sessionMemory.ts` 通过 forked agent 提取 session memory，说明“记忆”本身也是 agent 化、后台化的。

这一层带来的产品含义是：Claude Code 并不是“每轮都重新组织上下文”的 stateless chat，而是显式维护一条可恢复、可裁剪、可摘要、可分叉、可回放的会话历史链。很多体验问题和一致性问题，实际上都在这层被解决或暴露。

## 13. 多代理、后台任务与团队式运行

多代理在这份代码里不是概念演示，而是有完整任务系统承载的正式能力。

- `src/Task.ts:7-13` 定义了 `local_bash`、`local_agent`、`remote_agent`、`in_process_teammate`、`local_workflow`、`monitor_mcp`、`dream` 等任务类型。
- `src/tools/AgentTool/AgentTool.tsx:87`, `src/tools/AgentTool/AgentTool.tsx:96`, `src/tools/AgentTool/AgentTool.tsx:99` 显示 AgentTool 的输入 schema 已经包含后台运行、权限模式、隔离模式等概念。
- `src/tools/AgentTool/AgentTool.tsx:273`, `src/tools/AgentTool/AgentTool.tsx:278`, `src/tools/AgentTool/AgentTool.tsx:361` 对 teammate 嵌套和后台代理有明确约束，说明团队模型不是无边界递归。
- `src/tools/AgentTool/AgentTool.tsx:567`, `src/tools/AgentTool/AgentTool.tsx:569`, `src/tools/AgentTool/AgentTool.tsx:577`, `src/tools/AgentTool/AgentTool.tsx:590`, `src/tools/AgentTool/AgentTool.tsx:592` 表明 worker 会以自己的权限上下文重建工具池，并可选择 worktree 隔离。
- `src/tools/AgentTool/runAgent.ts:315`, `src/tools/AgentTool/runAgent.ts:412`, `src/tools/AgentTool/runAgent.ts:721`, `src/tools/AgentTool/runAgent.ts:844` 体现了 worktree、permission mode、cache-safe 参数与 shell task 清理等细节。
- `src/tasks/LocalAgentTask/LocalAgentTask.tsx:488`, `src/tasks/LocalAgentTask/LocalAgentTask.tsx:553` 与 `src/tasks/RemoteAgentTask/RemoteAgentTask.tsx:415`, `src/tasks/RemoteAgentTask/RemoteAgentTask.tsx:422` 表明本地与远程代理都被任务化、可追踪、可通知。

这说明 Claude Code 内部已经把“代理”产品化为正式运行实体，而不是单纯一次性工具调用。任务 ID、后台化、通知、输出文件、worktree 生命周期，这些都是长期运行代理平台的典型特征。

## 14. MCP、插件与技能：扩展性是一级架构目标

MCP：

- `src/services/mcp/client.ts:9`, `src/services/mcp/client.ts:16`, `src/services/mcp/client.ts:88` 显示至少支持 SSE、streamable HTTP、WebSocket 等 transport。
- `src/services/mcp/client.ts:620`, `src/services/mcp/client.ts:673`, `src/services/mcp/client.ts:709`, `src/services/mcp/client.ts:783`, `src/services/mcp/client.ts:814`, `src/services/mcp/client.ts:879` 表明认证、OAuth provider、proxy、TLS、HTTP 与 WS 路径都被完整考虑。
- `src/services/mcp/client.ts:2315`, `src/services/mcp/client.ts:3201` 说明还有 needs-auth cache 与 token 失效后的重新授权逻辑。
- `src/entrypoints/mcp.ts:35`, `src/entrypoints/mcp.ts:59`, `src/entrypoints/mcp.ts:99`, `src/entrypoints/mcp.ts:150`, `src/entrypoints/mcp.ts:192` 则表明 Claude Code 甚至可以反向把自身工具暴露成一个 MCP server。

插件：

- `src/utils/plugins/pluginLoader.ts:5`, `src/utils/plugins/pluginLoader.ts:17`, `src/utils/plugins/pluginLoader.ts:28` 在文件头就写清楚了 marketplace、git repository、manifest validation 等设计目标。
- `src/utils/plugins/pluginLoader.ts:121`, `src/utils/plugins/pluginLoader.ts:979`, `src/utils/plugins/pluginLoader.ts:1101` 显示 zip cache、plugin manifest 装载与校验已经是成熟能力。
- `src/utils/plugins/pluginLoader.ts:1882`, `src/utils/plugins/pluginLoader.ts:1938`, `src/utils/plugins/pluginLoader.ts:1961` 体现出 marketplace 插件发现、企业策略筛选、并行加载。
- `src/utils/plugins/pluginLoader.ts:3096`, `src/utils/plugins/pluginLoader.ts:3137`, `src/utils/plugins/pluginLoader.ts:3161` 把完整加载与 cache-only 加载分成两条路径，以优化启动性能。

技能：

- `src/skills/loadSkillsDir.ts:133`, `src/skills/loadSkillsDir.ts:156`, `src/skills/loadSkillsDir.ts:181` 说明技能 frontmatter 可以配置 hooks、path 作用域、模型与 effort 等元数据。
- `src/skills/loadSkillsDir.ts:447`, `src/skills/loadSkillsDir.ts:578`, `src/skills/loadSkillsDir.ts:771`, `src/skills/loadSkillsDir.ts:986` 说明技能支持解析、条件激活、动态激活。

综合判断：扩展性不是“之后再接”的插件层，而是产品中心能力。MCP、插件、技能、命令都是一等公民，而且都已经与权限、缓存、启动时加载成本发生了深度耦合。

## 15. 远程会话、Bridge 与控制协议

这部分进一步证明 Claude Code 不只是本地 CLI。

- `src/remote/RemoteSessionManager.ts:95`, `src/remote/RemoteSessionManager.ts:194`, `src/remote/RemoteSessionManager.ts:278`, `src/remote/RemoteSessionManager.ts:295`, `src/remote/RemoteSessionManager.ts:310` 说明远程会话管理器负责连接、消息转发、权限请求与中断。
- `src/bridge/bridgeMain.ts:1980` 表明 bridge 不是辅助脚本，而是单独的大型运行模式。
- `src/cli/structuredIO.ts` 和 `src/entrypoints/sdk/controlSchemas.ts` 则定义了结构化控制通道和 schema。
- `src/entrypoints/agentSdkTypes.ts:120`, `src/entrypoints/agentSdkTypes.ts:132`, `src/entrypoints/agentSdkTypes.ts:144`, `src/entrypoints/agentSdkTypes.ts:164`, `src/entrypoints/agentSdkTypes.ts:182`, `src/entrypoints/agentSdkTypes.ts:207`, `src/entrypoints/agentSdkTypes.ts:223`, `src/entrypoints/agentSdkTypes.ts:237`, `src/entrypoints/agentSdkTypes.ts:251`, `src/entrypoints/agentSdkTypes.ts:272`, `src/entrypoints/agentSdkTypes.ts:442` 大量 `not implemented` 非常值得注意。

我的解读是：当前源码树更像 Claude Code CLI/TUI 运行时的内部源码快照，而不是一个完整对外 SDK 工作区。原因有三点：

- 公共 SDK 形状在，但很多运行函数是占位实现。
- 当前树缺少常规构建元数据。
- 真正完整的实现重心明显在 CLI/TUI/bridge/runtime 一侧，而不是 npm-style SDK package 一侧。

## 16. 这份源码最强的地方

- 它把长期会话、工具执行、存储一致性、权限流和缓存命中率放在同一架构面上统一处理。
- 它对 prompt caching 的工程投入非常深，远超一般 agent 应用。
- 它把安全做成了多层体系，而不是单点确认框。
- 它对扩展性投入很大，MCP、插件、技能都不是装饰层。
- 它已经具备多代理和远程执行平台的雏形，甚至在很多地方已经不是“雏形”，而是成熟产品能力。

## 17. 主要风险与技术债

- 超大热点文件过多，`main.tsx`、`REPL.tsx`、`messages.ts`、`sessionStorage.ts`、`api/claude.ts`、`cli/print.ts`、`pluginLoader.ts` 都已经达到高维护压力区间。
- `src/bootstrap/state.ts` 代表的全局可变状态会增加隐式耦合、并发推理难度和回归分析成本。
- `utils/` 承载了过多核心逻辑，说明抽象边界有持续漂移的风险。
- feature flag 面过大，当前至少可见 89 个 flag；高频 flag 还包括 `KAIROS`、`TRANSCRIPT_CLASSIFIER`、`TEAMMEM`、`VOICE_MODE`、`BASH_CLASSIFIER`、`PROACTIVE`、`COORDINATOR_MODE`、`BRIDGE_MODE` 等。这意味着代码面上同时存在大量产品分支和实验分支。
- 终端渲染层高度定制，意味着体验更强，但也提高了跨平台兼容与渲染回归的复杂度。
- 当前快照不含完整 build/test/package 元数据，因此对“如何发布、如何测试、哪些是源码、哪些是编译后产物”的外部可验证性有限。

## 18. 最终结论

如果把 Claude Code 简化成“调用 Claude 的命令行工具”，那会严重低估这份源码的真实复杂度。更准确的描述是：

它是一套围绕大模型构建的终端 Agent 运行时平台，核心价值在于把模型能力嵌入一个可调度、可授权、可恢复、可扩展、可远程化、可多代理化的执行系统中。

从源码证据看，Claude Code 的真正壁垒不只是模型接口接得好，而是它已经把以下问题系统化了：

- 如何让工具成为稳定执行语义的一部分。
- 如何让长会话在成本、缓存、存储和一致性上可持续。
- 如何让自动化能力在权限、路径、shell、沙箱多层约束下仍然可用。
- 如何把本地、远程、插件、MCP、技能、多代理统一到一个运行时里。

这也是为什么它看起来像一个“终端里的 agent OS”，而不只是一个“聊天程序”。

## 19. 附录：关键源码锚点

- 启动与模式：`src/entrypoints/cli.tsx:126,160`；`src/main.tsx:585,957,2597,3329,3467,4327,4331`；`src/entrypoints/init.ts:247,307,311`
- 查询循环：`src/query.ts:164,563,713,719,1382`；`src/QueryEngine.ts:184,451,460,693,728,834,1078`
- 消息修复：`src/utils/messages.ts:1305,4980,5123,5305`
- 会话存储：`src/utils/sessionStorage.ts:558,622,841,1408,1583,2098,2171,3229`
- 工具框架：`src/Tool.ts:123,158,285,416,519,623`；`src/tools.ts:345,364`；`src/services/tools/toolOrchestration.ts:19,36,66,118,152`
- 权限与文件系统：`src/utils/permissions/permissionSetup.ts:94,240`；`src/utils/permissions/permissions.ts:111,483,594,854,1067,1262,1425`；`src/utils/permissions/filesystem.ts:95,224,1081,1219,1252,1303,1622,1727,1771`
- Shell 与沙箱：`src/tools/BashTool/bashSecurity.ts:28,289,497,851,2247,2286`；`src/tools/BashTool/readOnlyValidation.ts:1876,1951,1978`；`src/tools/PowerShellTool/readOnlyValidation.ts:118,1064,1168`；`src/entrypoints/sandboxTypes.ts:12,47,91,117`；`src/utils/sandbox/sandbox-adapter.ts:149,172,230,247,302,330,702,738,775`
- 文件工具：`src/tools/FileReadTool/FileReadTool.ts:61,181,470,484,904,991,1089`；`src/tools/FileEditTool/FileEditTool.ts:345,493`
- Prompt/cache：`src/constants/prompts.ts:114,573`；`src/utils/api.ts:119,223,338,364`；`src/services/api/claude.ts:1174,1231,1376,3053,3164,3213`；`src/utils/forkedAgent.ts:51,57,131,489`；`src/services/compact/microCompact.ts:335,369`
- 多代理与任务：`src/Task.ts:7-13`；`src/tools/AgentTool/AgentTool.tsx:87,96,99,273,567,569,577,590,592`；`src/tools/AgentTool/runAgent.ts:315,412,721,844`；`src/tasks/LocalAgentTask/LocalAgentTask.tsx:488,553`；`src/tasks/RemoteAgentTask/RemoteAgentTask.tsx:415,422`
- MCP/插件/技能：`src/services/mcp/client.ts:620,673,709,783,814,879,2315,3201`；`src/entrypoints/mcp.ts:35,59,99,150,192`；`src/utils/plugins/pluginLoader.ts:5,121,979,1882,1938,1961,3096,3137,3161`；`src/skills/loadSkillsDir.ts:133,156,181,447,771,986`
- 远程与 SDK：`src/remote/RemoteSessionManager.ts:95,194,278,295,310`；`src/bridge/bridgeMain.ts:1980`；`src/entrypoints/agentSdkTypes.ts:120,132,144,164,182,207,223,237,251,272,442`
