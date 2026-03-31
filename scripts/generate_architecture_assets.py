#!/usr/bin/env python3

from __future__ import annotations

from dataclasses import dataclass
from functools import lru_cache
from pathlib import Path
from typing import Iterable

from PIL import Image, ImageColor, ImageDraw, ImageFilter, ImageFont


ROOT = Path(__file__).resolve().parents[1]
OUT_DIR = ROOT / "docs" / "assets"


def rgba(hex_value: str, alpha: int = 255) -> tuple[int, int, int, int]:
    red, green, blue = ImageColor.getrgb(hex_value)
    return red, green, blue, alpha


def with_alpha(color: tuple[int, int, int, int], alpha: int) -> tuple[int, int, int, int]:
    return color[0], color[1], color[2], alpha


PALETTE = {
    "ink": rgba("#172033"),
    "muted": rgba("#62748d"),
    "muted_soft": rgba("#94a3b8"),
    "canvas": rgba("#f6f8fc"),
    "canvas_alt": rgba("#fcfdff"),
    "paper": rgba("#ffffff"),
    "line": rgba("#d8e2ef"),
    "line_dark": rgba("#b9c7da"),
    "shadow": rgba("#12233d", 22),
    "shadow_soft": rgba("#12233d", 10),
    "blue": rgba("#2563eb"),
    "blue_fill": rgba("#eef4ff"),
    "green": rgba("#10b981"),
    "green_fill": rgba("#eefaf5"),
    "orange": rgba("#f59e0b"),
    "orange_fill": rgba("#fff7ea"),
    "purple": rgba("#8b5cf6"),
    "purple_fill": rgba("#f4efff"),
    "teal": rgba("#0ea5a3"),
    "teal_fill": rgba("#edfcfb"),
    "rose": rgba("#ef476f"),
    "rose_fill": rgba("#fff1f5"),
    "slate_fill": rgba("#f2f6fb"),
}


FONT_CANDIDATES = {
    "headline": [
        "/System/Library/Fonts/Avenir Next.ttc",
        "/System/Library/Fonts/Helvetica.ttc",
        "/System/Library/Fonts/Supplemental/Arial.ttf",
    ],
    "body": [
        "/System/Library/Fonts/SFNS.ttf",
        "/System/Library/Fonts/Helvetica.ttc",
        "/System/Library/Fonts/Supplemental/Arial.ttf",
    ],
    "mono": [
        "/System/Library/Fonts/Menlo.ttc",
        "/System/Library/Fonts/SFNSMono.ttf",
        "/System/Library/Fonts/Helvetica.ttc",
    ],
}


@dataclass(frozen=True)
class DiagramCard:
    title: str
    subtitle: str


@dataclass(frozen=True)
class DiagramSection:
    label: str
    summary: str
    accent_key: str
    fill_key: str
    connector: str
    cards: tuple[DiagramCard, ...]


@dataclass(frozen=True)
class WorkflowStep:
    chip: str
    title: str
    subtitle: str
    bullets: tuple[str, ...]
    user_view: str
    runtime_focus: tuple[str, ...]
    key_files: tuple[str, ...]
    accent_key: str


ARCHITECTURE_SECTIONS = (
    DiagramSection(
        label="User Entry Points",
        summary="How requests enter the product",
        accent_key="blue",
        fill_key="blue_fill",
        connector="CLI flags, REPL, SDK streams, WebSocket entry",
        cards=(
            DiagramCard("CLI Terminal", "Primary interactive interface for coding sessions and command-driven workflows."),
            DiagramCard("Structured SDK", "Headless JSON I/O path used by automation, wrappers, and integrations."),
            DiagramCard("IDE Integration", "Editor-facing hooks, selections, and LSP/assistant coordination surfaces."),
            DiagramCard("Remote Viewer", "Bridge and session-viewer path for remote or mirrored conversations."),
            DiagramCard("Voice Mode", "Feature-gated voice-oriented entry path observed in the runtime surface."),
        ),
    ),
    DiagramSection(
        label="Core Runtime",
        summary="The conversation state machine",
        accent_key="green",
        fill_key="green_fill",
        connector="Messages, policy, streaming state, and turn orchestration",
        cards=(
            DiagramCard("Bootstrap", "Fast-path dispatch in entrypoints plus startup preparation in main.tsx."),
            DiagramCard("Input Processor", "Slash commands, hooks, attachments, history expansion, and turn routing."),
            DiagramCard("QueryEngine", "Long-lived session state, turn lifecycle, and model/tool coordination."),
            DiagramCard("System Prompt", "Agent mode, memory, settings, custom prompts, and context assembly."),
            DiagramCard("Permissions", "Modes, policies, hooks, classifiers, and runtime authorization logic."),
        ),
    ),
    DiagramSection(
        label="Tool Runtime",
        summary="Everything the model can call",
        accent_key="orange",
        fill_key="orange_fill",
        connector="Validated tool calls, permission checks, and structured tool results",
        cards=(
            DiagramCard("File Tools", "Read, write, edit, grep, glob, and project navigation surfaces."),
            DiagramCard("Shell Tools", "Bash and PowerShell execution with safety gates and read-only validation."),
            DiagramCard("MCP Tools", "External servers, resources, prompts, and protocol-based integrations."),
            DiagramCard("Web Tools", "Search, fetch, browse, and network-assisted research surfaces."),
            DiagramCard("AgentTool", "Subagents, teammates, background tasks, and delegated execution."),
        ),
    ),
    DiagramSection(
        label="Session & Memory",
        summary="Persistent state and recovery",
        accent_key="purple",
        fill_key="purple_fill",
        connector="JSONL transcripts, file I/O, cache state, compaction, and sidecar metadata",
        cards=(
            DiagramCard("Transcripts", "JSONL-backed session persistence with message history and sidecar metadata."),
            DiagramCard("Compaction", "Long-session recovery, context budgets, and summarization boundaries."),
            DiagramCard("Claude.md", "Project memory, nested memory discovery, and local knowledge injection."),
            DiagramCard("Settings Merge", "User, project, managed, policy, and flag-driven configuration state."),
            DiagramCard("Analytics", "Cost, telemetry, diagnostics, and operational insight collection."),
        ),
    ),
    DiagramSection(
        label="Agents & Remote",
        summary="Distributed and background work",
        accent_key="teal",
        fill_key="teal_fill",
        connector="Task registries, remote control, worktrees, and multi-agent orchestration",
        cards=(
            DiagramCard("Local Agents", "Foreground and background tasks running inside the local runtime."),
            DiagramCard("Teammates", "In-process multi-agent orchestration and collaborative worker flows."),
            DiagramCard("Remote Agents", "CCR-style remote/background sessions and delegated remote execution."),
            DiagramCard("Worktrees", "Isolated workspaces for delegated edits and safer parallel changes."),
            DiagramCard("Session Bridge", "Remote coordination and session streaming over bridge/WebSocket paths."),
        ),
    ),
    DiagramSection(
        label="Extensions & Enterprise",
        summary="Pluggability and product gating",
        accent_key="rose",
        fill_key="rose_fill",
        connector="Plugin loading, skills, hooks, sync, and feature-gated product surfaces",
        cards=(
            DiagramCard("Plugins", "Versioned loader, marketplaces, installation state, and runtime caches."),
            DiagramCard("Skills", "Bundled, disk, plugin, and MCP-provided reusable capability packs."),
            DiagramCard("Hooks", "Lifecycle shell, HTTP, and function hooks that can enrich or block actions."),
            DiagramCard("Sync", "Settings sync and shared memory/state coordination across environments."),
            DiagramCard("Feature Flags", "Build variants, gated surfaces, and tier-specific capability switches."),
        ),
    ),
)


WORKFLOW_STEPS = (
    WorkflowStep(
        chip="Entry",
        title="1. A Request Enters Claude Code",
        subtitle="The runtime first decides what kind of invocation this is: a fast path, an interactive REPL turn, or a structured/headless session.",
        bullets=(
            "The request can originate from the CLI, a structured JSON I/O client, editor integration, or a remote session viewer.",
            "Fast paths such as version/help/daemon-like modes bypass most of the heavy runtime and exit early.",
            "Full interactive startup flows through the CLI entrypoint into main.tsx, where the long-lived session is prepared.",
            "Interactive users land in the Ink REPL while headless users fall through to structured printing/stream output paths.",
        ),
        user_view="You see a fresh session open, a previous transcript resume, or a non-interactive stream begin immediately depending on flags and mode.",
        runtime_focus=(
            "Choose the correct bootstrap path for this invocation.",
            "Restore or create the right session container for the turn.",
            "Decide whether the request should enter the full conversation runtime at all.",
        ),
        key_files=(
            "src/entrypoints/cli.tsx",
            "src/main.tsx",
            "src/screens/REPL.tsx",
            "src/cli/print.ts",
        ),
        accent_key="blue",
    ),
    WorkflowStep(
        chip="Settings",
        title="2. Settings, Auth, And Policy Are Resolved",
        subtitle="Before the model sees anything, Claude Code decides which features, tools, and permissions are active for this session.",
        bullets=(
            "Configuration is merged from user, project, local, managed, policy, and command-line sources.",
            "Remote-managed settings and organization-level rules can enable, disable, or constrain major features.",
            "Authentication state, plugin availability, MCP configs, and model defaults are loaded here.",
            "This stage determines the effective permission mode and which capabilities the UI is even allowed to expose.",
        ),
        user_view="Feature visibility often changes here: permissions behavior, remote/background surfaces, and some tools depend on this stage.",
        runtime_focus=(
            "Merge configuration layers into one effective session state.",
            "Resolve auth, model defaults, and capability switches.",
            "Establish the policy envelope that later tool calls must respect.",
        ),
        key_files=(
            "src/utils/settings/settings.ts",
            "src/services/remoteManagedSettings/index.ts",
            "src/services/settingsSync/index.ts",
            "src/utils/permissions/permissionSetup.ts",
        ),
        accent_key="green",
    ),
    WorkflowStep(
        chip="Normalize",
        title="3. Input Is Normalized Into Structured Messages",
        subtitle="Raw terminal text is not sent directly to the model. Claude Code converts it into structured messages, commands, attachments, and hook events.",
        bullets=(
            "Slash commands are resolved before any model call is attempted.",
            "Images, references, pasted content, selections, and history expansion become structured inputs.",
            "Hooks can enrich, block, warn on, or rewrite the request before it reaches the conversation engine.",
            "The result is a model-ready message bundle plus a decision on whether the turn requires model inference at all.",
        ),
        user_view="This is where slash commands can short-circuit immediately and where pre-flight warnings or hook-driven blockers surface.",
        runtime_focus=(
            "Resolve command-like input before spending model tokens.",
            "Convert attachments and references into durable structured state.",
            "Produce a clean message bundle for the QueryEngine turn.",
        ),
        key_files=(
            "src/utils/processUserInput/processUserInput.ts",
            "src/history.ts",
            "src/utils/messages.ts",
            "src/utils/hooks.ts",
        ),
        accent_key="orange",
    ),
    WorkflowStep(
        chip="Context",
        title="4. QueryEngine Builds The Turn Context",
        subtitle="The conversation engine assembles the system prompt, memory, tool pool, context windows, and state needed for this specific turn.",
        bullets=(
            "QueryEngine owns the long-lived session model and the transition rules between turns.",
            "System prompt composition depends on agent mode, coordinator mode, custom prompts, append prompts, and settings.",
            "Claude.md memory, attachments, session history, and cached file context are folded into the turn here.",
            "Budgets, callbacks, model configuration, and tool availability are prepared before the API call begins.",
        ),
        user_view="Most of this stage is invisible, but it strongly determines response quality, available tools, and how much prior context survives.",
        runtime_focus=(
            "Assemble the final prompt and context package for the turn.",
            "Prepare model budgets, tool inventory, and memory sources.",
            "Establish the callbacks that will handle streaming and tool execution.",
        ),
        key_files=(
            "src/QueryEngine.ts",
            "src/query.ts",
            "src/utils/systemPrompt.ts",
            "src/utils/attachments.ts",
        ),
        accent_key="purple",
    ),
    WorkflowStep(
        chip="Model",
        title="5. The Model Streams A Response",
        subtitle="Claude Code sends the normalized request to the model layer and begins streaming assistant output, including tool-use directives.",
        bullets=(
            "API request shaping, headers, betas, and output constraints are resolved in the model service layer.",
            "Assistant output can stream as plain text, structured content, thinking blocks, or tool_use blocks.",
            "Error recovery, rate-limit handling, and oversized-turn behavior can redirect the flow here.",
            "If the turn is too large, compaction-related behavior can trigger before the conversation continues.",
        ),
        user_view="You see the assistant start typing, tool loaders appear, or the runtime pivot into compaction/recovery if the turn is too large.",
        runtime_focus=(
            "Issue the model request with the correct headers and limits.",
            "Handle streaming blocks and recognize tool-use transitions.",
            "Recover cleanly from API errors, oversized turns, or compact boundaries.",
        ),
        key_files=(
            "src/query.ts",
            "src/services/api/claude.ts",
            "src/services/api/errors.ts",
            "src/services/compact/autoCompact.ts",
        ),
        accent_key="teal",
    ),
    WorkflowStep(
        chip="Tools",
        title="6. Tools Execute Under Permission Control",
        subtitle="Tool calls are validated, permission-checked, scheduled, executed, and returned to the model as structured tool results.",
        bullets=(
            "Each tool call passes through permission logic, policy checks, and hook-aware validation.",
            "Concurrency-safe calls can run together while unsafe or stateful calls stay serialized.",
            "Shell execution is guarded by dedicated security/read-only validation layers.",
            "Built-ins, MCP tools, web tools, and agent spawning all share a common orchestration path.",
        ),
        user_view="This is where permission prompts appear, commands run, files change, MCP data streams back, or background agents get launched.",
        runtime_focus=(
            "Validate every tool call against permission and policy state.",
            "Schedule safe concurrency while preserving deterministic behavior.",
            "Turn tool results back into model-visible structured conversation state.",
        ),
        key_files=(
            "src/services/tools/toolExecution.ts",
            "src/services/tools/toolOrchestration.ts",
            "src/tools/BashTool/bashSecurity.ts",
            "src/services/mcp/client.ts",
        ),
        accent_key="rose",
    ),
    WorkflowStep(
        chip="Persist",
        title="7. Session State Is Persisted For The Next Turn",
        subtitle="At the end of the turn, Claude Code records the conversation, updates agent/task state, and decides whether to continue, compact, or stop.",
        bullets=(
            "Messages are stored in JSONL transcripts plus sidecar session metadata.",
            "Local agents, remote agents, background tasks, and teammate flows update task registries and notifications.",
            "If the session grows too large, compaction summarizes earlier context and preserves critical artifacts.",
            "The next prompt resumes from persisted state rather than rebuilding the entire working thread from scratch.",
        ),
        user_view="You can resume later, inspect background work, receive notifications, and continue a long-lived session without losing the thread.",
        runtime_focus=(
            "Persist the transcript, metadata, and task updates for the turn.",
            "Compact or summarize history when context budgets are under pressure.",
            "Prepare the exact state the next prompt should resume from.",
        ),
        key_files=(
            "src/utils/sessionStorage.ts",
            "src/services/compact/compact.ts",
            "src/tasks/LocalAgentTask/LocalAgentTask.tsx",
            "src/tasks/RemoteAgentTask/RemoteAgentTask.tsx",
        ),
        accent_key="blue",
    ),
)


@lru_cache(maxsize=None)
def font(size: int, family: str = "body") -> ImageFont.FreeTypeFont | ImageFont.ImageFont:
    for path in FONT_CANDIDATES[family]:
        if not Path(path).exists():
            continue
        try:
            return ImageFont.truetype(path, size=size)
        except OSError:
            continue
    return ImageFont.load_default()


def text_bbox(draw: ImageDraw.ImageDraw, text: str, use_font: ImageFont.ImageFont) -> tuple[int, int, int, int]:
    return draw.textbbox((0, 0), text or " ", font=use_font)


def text_size(draw: ImageDraw.ImageDraw, text: str, use_font: ImageFont.ImageFont) -> tuple[int, int]:
    left, top, right, bottom = text_bbox(draw, text, use_font)
    return right - left, bottom - top


def line_height(draw: ImageDraw.ImageDraw, use_font: ImageFont.ImageFont) -> int:
    return text_size(draw, "Ag", use_font)[1]


def draw_text(
    draw: ImageDraw.ImageDraw,
    xy: tuple[float, float],
    text: str,
    use_font: ImageFont.ImageFont,
    fill: tuple[int, int, int, int],
) -> None:
    left, top, _, _ = text_bbox(draw, text, use_font)
    draw.text((xy[0] - left, xy[1] - top), text, font=use_font, fill=fill)


def break_long_token(draw: ImageDraw.ImageDraw, token: str, use_font: ImageFont.ImageFont, max_width: int) -> list[str]:
    if text_size(draw, token, use_font)[0] <= max_width:
        return [token]
    pieces: list[str] = []
    current = ""
    for char in token:
        candidate = current + char
        if current and text_size(draw, candidate, use_font)[0] > max_width:
            pieces.append(current)
            current = char
        else:
            current = candidate
    if current:
        pieces.append(current)
    return pieces or [token]


def wrap_text(draw: ImageDraw.ImageDraw, text: str, use_font: ImageFont.ImageFont, max_width: int) -> list[str]:
    if not text:
        return [""]
    parts: list[str] = []
    for word in text.split():
        if text_size(draw, word, use_font)[0] <= max_width:
            parts.append(word)
        else:
            parts.extend(break_long_token(draw, word, use_font, max_width))
    lines: list[str] = []
    current = parts[0]
    for part in parts[1:]:
        candidate = f"{current} {part}"
        if text_size(draw, candidate, use_font)[0] <= max_width:
            current = candidate
        else:
            lines.append(current)
            current = part
    lines.append(current)
    return lines


def text_block_height(
    draw: ImageDraw.ImageDraw,
    lines: list[str],
    use_font: ImageFont.ImageFont,
    line_gap: int,
) -> int:
    if not lines:
        return 0
    return len(lines) * line_height(draw, use_font) + max(0, len(lines) - 1) * line_gap


def ellipsize_text(
    draw: ImageDraw.ImageDraw,
    text: str,
    use_font: ImageFont.ImageFont,
    max_width: int,
    mode: str = "end",
) -> str:
    if text_size(draw, text, use_font)[0] <= max_width:
        return text
    ellipsis = "..."
    if mode == "middle":
        left = text
        right = ""
        while left and text_size(draw, left + ellipsis + right, use_font)[0] > max_width:
            if len(left) > len(right):
                right = left[-1] + right
                left = left[:-1]
            else:
                right = right[1:] if right else ""
        while left and right and text_size(draw, left + ellipsis + right, use_font)[0] > max_width:
            if len(left) >= len(right):
                left = left[:-1]
            else:
                right = right[1:]
        return (left + ellipsis + right).strip(".") or ellipsis
    trimmed = text
    while trimmed and text_size(draw, trimmed + ellipsis, use_font)[0] > max_width:
        trimmed = trimmed[:-1]
    return (trimmed + ellipsis) if trimmed else ellipsis


def fit_wrapped_font(
    draw: ImageDraw.ImageDraw,
    text: str,
    family: str,
    max_size: int,
    min_size: int,
    max_width: int,
    max_height: int,
    line_gap: int,
    max_lines: int | None = None,
) -> tuple[ImageFont.ImageFont, list[str]]:
    for size in range(max_size, min_size - 1, -1):
        use_font = font(size, family)
        lines = wrap_text(draw, text, use_font, max_width)
        if max_lines is not None and len(lines) > max_lines:
            continue
        if text_block_height(draw, lines, use_font, line_gap) <= max_height:
            return use_font, lines
    use_font = font(min_size, family)
    lines = wrap_text(draw, text, use_font, max_width)
    if max_lines is not None and len(lines) > max_lines:
        lines = lines[:max_lines]
        lines[-1] = ellipsize_text(draw, lines[-1], use_font, max_width)
    return use_font, lines


def draw_text_lines(
    draw: ImageDraw.ImageDraw,
    xy: tuple[int, int],
    lines: list[str],
    use_font: ImageFont.ImageFont,
    fill: tuple[int, int, int, int],
    line_gap: int,
) -> int:
    current_y = xy[1]
    for line in lines:
        draw_text(draw, (xy[0], current_y), line, use_font, fill)
        current_y += line_height(draw, use_font) + line_gap
    return current_y - xy[1]


def add_glow(base: Image.Image, box: tuple[int, int, int, int], color: tuple[int, int, int, int], blur: int) -> None:
    layer = Image.new("RGBA", base.size, (0, 0, 0, 0))
    overlay = ImageDraw.Draw(layer)
    overlay.ellipse(box, fill=color)
    base.alpha_composite(layer.filter(ImageFilter.GaussianBlur(blur)))


def rounded_box(
    base: Image.Image,
    rect: tuple[int, int, int, int],
    fill: tuple[int, int, int, int],
    outline: tuple[int, int, int, int] | None = None,
    width: int = 1,
    radius: int = 24,
    shadow: bool = False,
    shadow_alpha: int = 18,
) -> None:
    if shadow:
        layer = Image.new("RGBA", base.size, (0, 0, 0, 0))
        shadow_draw = ImageDraw.Draw(layer)
        x1, y1, x2, y2 = rect
        shadow_draw.rounded_rectangle(
            (x1, y1 + 8, x2, y2 + 8),
            radius=radius,
            fill=(PALETTE["shadow"][0], PALETTE["shadow"][1], PALETTE["shadow"][2], shadow_alpha),
        )
        base.alpha_composite(layer.filter(ImageFilter.GaussianBlur(16)))
    draw = ImageDraw.Draw(base)
    draw.rounded_rectangle(rect, radius=radius, fill=fill, outline=outline, width=width)


def draw_badge(
    base: Image.Image,
    rect: tuple[int, int, int, int],
    text: str,
    fill: tuple[int, int, int, int],
    ink: tuple[int, int, int, int],
) -> None:
    rounded_box(base, rect, fill=fill, outline=None, radius=(rect[3] - rect[1]) // 2)
    draw = ImageDraw.Draw(base)
    use_font, lines = fit_wrapped_font(
        draw,
        text,
        "body",
        17,
        13,
        rect[2] - rect[0] - 24,
        rect[3] - rect[1] - 10,
        3,
        max_lines=1,
    )
    line_w, line_h = text_size(draw, lines[0], use_font)
    draw_text(
        draw,
        (rect[0] + (rect[2] - rect[0] - line_w) / 2, rect[1] + (rect[3] - rect[1] - line_h) / 2),
        lines[0],
        use_font,
        ink,
    )


def draw_connector(draw: ImageDraw.ImageDraw, width: int, y: int, label: str) -> None:
    x = 90
    while x < width - 90:
        draw.line((x, y, min(x + 12, width - 90), y), fill=PALETTE["line_dark"], width=2)
        x += 24
    label_font = font(18, "body")
    label_w, label_h = text_size(draw, label, label_font)
    label_x = (width - label_w) // 2
    draw.rounded_rectangle(
        (label_x - 12, y - 18, label_x + label_w + 12, y + label_h + 6),
        radius=16,
        fill=PALETTE["canvas"],
        outline=PALETTE["line"],
        width=1,
    )
    draw_text(draw, (label_x, y - 10), label, label_font, PALETTE["muted"])


def draw_architecture_card(
    base: Image.Image,
    rect: tuple[int, int, int, int],
    accent: tuple[int, int, int, int],
    card: DiagramCard,
    flat: bool,
) -> None:
    rounded_box(
        base,
        rect,
        fill=PALETTE["paper"],
        outline=PALETTE["line"],
        width=1,
        radius=22,
        shadow=not flat,
        shadow_alpha=16,
    )
    draw = ImageDraw.Draw(base)
    x1, y1, x2, y2 = rect
    draw.rounded_rectangle((x1 + 16, y1 + 16, x1 + 22, y2 - 16), radius=3, fill=accent)
    title_font, title_lines = fit_wrapped_font(draw, card.title, "headline", 27, 20, x2 - x1 - 56, 56, 4, max_lines=2)
    draw_text_lines(draw, (x1 + 38, y1 + 18), title_lines, title_font, PALETTE["ink"], 4)
    title_height = text_block_height(draw, title_lines, title_font, 4)
    body_y = y1 + 22 + title_height + 14
    body_font, body_lines = fit_wrapped_font(
        draw,
        card.subtitle,
        "body",
        17,
        14,
        x2 - x1 - 56,
        max(40, y2 - body_y - 18),
        4,
        max_lines=4,
    )
    draw_text_lines(draw, (x1 + 38, body_y), body_lines, body_font, PALETTE["muted"], 4)


def draw_architecture_section(
    base: Image.Image,
    top: int,
    section: DiagramSection,
    sidebar_width: int,
    flat: bool,
    draw_connector_after: bool,
) -> int:
    draw = ImageDraw.Draw(base)
    accent = PALETTE[section.accent_key]
    fill = PALETTE[section.fill_key]
    width = base.size[0]
    height = 184 if not flat else 176
    outer = (60, top, width - 60, top + height)
    rounded_box(base, outer, fill=fill, outline=with_alpha(accent, 90), width=2, radius=28, shadow=not flat, shadow_alpha=12)

    sidebar = (outer[0] + 18, outer[1] + 18, outer[0] + sidebar_width, outer[3] - 18)
    rounded_box(base, sidebar, fill=with_alpha(accent, 30), outline=with_alpha(accent, 72), width=1, radius=22)
    chip_w = min(sidebar_width - 46, text_size(draw, section.label, font(32, "headline"))[0] + 34)
    chip = (sidebar[0] + 18, sidebar[1] + 22, sidebar[0] + 18 + chip_w, sidebar[1] + 58)
    rounded_box(base, chip, fill=accent, radius=18)
    draw_text(draw, (chip[0] + 16, chip[1] + 7), section.label, font(23, "headline"), rgba("#ffffff"))
    summary_font, summary_lines = fit_wrapped_font(
        draw,
        section.summary,
        "body",
        19,
        16,
        sidebar[2] - sidebar[0] - 36,
        52,
        4,
        max_lines=2,
    )
    draw_text_lines(draw, (sidebar[0] + 18, sidebar[1] + 78), summary_lines, summary_font, PALETTE["ink"], 4)

    card_gap = 16
    card_start = sidebar[2] + 18
    card_end = outer[2] - 18
    card_height = outer[3] - outer[1] - 36
    card_width = int((card_end - card_start - card_gap * (len(section.cards) - 1)) / len(section.cards))
    for index, card in enumerate(section.cards):
        x = card_start + index * (card_width + card_gap)
        draw_architecture_card(base, (x, outer[1] + 18, x + card_width, outer[1] + 18 + card_height), accent, card, flat)

    next_top = outer[3] + 32
    if draw_connector_after:
        draw_connector(draw, width, next_top - 8, section.connector)
        next_top += 26
    return next_top


def render_architecture(flat: bool) -> Image.Image:
    size = (1920, 1600 if not flat else 1560)
    base = Image.new("RGBA", size, PALETTE["canvas_alt"] if flat else PALETTE["canvas"])
    draw = ImageDraw.Draw(base)

    title = "Claude Code System Architecture" if not flat else "Claude Code · System Architecture"
    subtitle = (
        "Source-derived architecture map from the analyzed repository snapshot. This is a synthesized technical view, not vendor artwork."
        if not flat
        else "English-only slide version based on repository analysis. Layout optimized for clean export in PNG and GIF workflows."
    )
    draw_text(draw, (60, 34), title, font(50 if flat else 54, "headline"), PALETTE["ink"])
    draw_text(draw, (62, 94), subtitle, font(21, "body"), PALETTE["muted"])

    badge_y = 34
    draw_badge(base, (1420, badge_y, 1590, badge_y + 40), "1,902 files", with_alpha(PALETTE["blue"], 22), PALETTE["blue"])
    draw_badge(base, (1604, badge_y, 1768, badge_y + 40), "89 flags", with_alpha(PALETTE["green"], 22), PALETTE["green"])
    draw_badge(base, (1782, badge_y, 1860, badge_y + 40), "src/", with_alpha(PALETTE["purple"], 20), PALETTE["purple"])

    label_probe = ImageDraw.Draw(Image.new("RGBA", (10, 10)))
    sidebar_width = max(text_size(label_probe, section.label, font(32, "headline"))[0] for section in ARCHITECTURE_SECTIONS) + 90
    sidebar_width = max(314, min(sidebar_width, 400))

    top = 138
    for index, section in enumerate(ARCHITECTURE_SECTIONS):
        top = draw_architecture_section(
            base,
            top,
            section,
            sidebar_width,
            flat=flat,
            draw_connector_after=index < len(ARCHITECTURE_SECTIONS) - 1,
        )

    footer = (
        "Core read: requests enter via CLI/SDK/editor surfaces, move through QueryEngine and permission-gated tools, and persist as resumable session state."
    )
    draw_text(draw, (60, base.size[1] - 46), footer, font(18, "body"), PALETTE["muted"])
    return base


def draw_bullet_list(
    draw: ImageDraw.ImageDraw,
    x: int,
    y: int,
    width: int,
    bullets: Iterable[str],
    accent: tuple[int, int, int, int],
    text_family: str,
    max_font: int,
    min_font: int,
) -> int:
    current_y = y
    for bullet in bullets:
        use_font, lines = fit_wrapped_font(draw, bullet, text_family, max_font, min_font, width - 28, 200, 5, max_lines=4)
        draw.rounded_rectangle((x, current_y + 7, x + 8, current_y + 15), radius=4, fill=accent)
        height = draw_text_lines(draw, (x + 20, current_y), lines, use_font, PALETTE["ink"], 5)
        current_y += max(28, height) + 16
    return current_y


def draw_panel(
    base: Image.Image,
    rect: tuple[int, int, int, int],
    accent: tuple[int, int, int, int],
    title: str,
    shadow: bool,
) -> None:
    rounded_box(base, rect, fill=PALETTE["paper"], outline=PALETTE["line"], width=1, radius=24, shadow=shadow, shadow_alpha=14)
    draw = ImageDraw.Draw(base)
    draw.rounded_rectangle((rect[0] + 16, rect[1] + 16, rect[0] + 22, rect[3] - 16), radius=3, fill=accent)
    draw_text(draw, (rect[0] + 38, rect[1] + 18), title, font(24, "headline"), accent)


def draw_progress_row(base: Image.Image, step_index: int, flat: bool) -> None:
    draw = ImageDraw.Draw(base)
    width = base.size[0]
    start_x = 52
    top_y = 118
    total_width = width - start_x * 2
    gap = 12
    item_width = int((total_width - gap * (len(WORKFLOW_STEPS) - 1)) / len(WORKFLOW_STEPS))

    line_y = top_y + 32
    draw.line((start_x, line_y, width - start_x, line_y), fill=PALETTE["line_dark"], width=4)

    progress_end = start_x + step_index * (item_width + gap) + item_width // 2
    accent = PALETTE[WORKFLOW_STEPS[step_index].accent_key]
    draw.line((start_x, line_y, progress_end, line_y), fill=accent, width=4)

    for index, step in enumerate(WORKFLOW_STEPS):
        chip_x = start_x + index * (item_width + gap)
        rect = (chip_x, top_y, chip_x + item_width, top_y + 74)
        state = "future"
        if index < step_index:
            state = "done"
        elif index == step_index:
            state = "current"
        chip_accent = PALETTE[step.accent_key]
        fill = PALETTE["paper"]
        outline = PALETTE["line"]
        if state == "done":
            fill = with_alpha(PALETTE["green"], 22)
            outline = PALETTE["green"]
        elif state == "current":
            fill = with_alpha(chip_accent, 24)
            outline = chip_accent
        rounded_box(base, rect, fill=fill, outline=outline, width=2, radius=18, shadow=not flat, shadow_alpha=10)

        bubble = (rect[0] + 12, rect[1] + 18, rect[0] + 46, rect[1] + 52)
        bubble_fill = rgba("#e5e7eb")
        if state == "done":
            bubble_fill = PALETTE["green"]
        elif state == "current":
            bubble_fill = chip_accent
        rounded_box(base, bubble, fill=bubble_fill, radius=17)
        bubble_text = str(index + 1)
        bubble_font = font(17, "headline")
        bubble_w, bubble_h = text_size(draw, bubble_text, bubble_font)
        draw_text(
            draw,
            (bubble[0] + (bubble[2] - bubble[0] - bubble_w) / 2, bubble[1] + (bubble[3] - bubble[1] - bubble_h) / 2),
            bubble_text,
            bubble_font,
            rgba("#ffffff"),
        )
        label_font, label_lines = fit_wrapped_font(draw, step.chip, "headline", 17, 13, item_width - 64, 36, 2, max_lines=2)
        draw_text_lines(draw, (rect[0] + 58, rect[1] + 19), label_lines, label_font, PALETTE["ink"], 2)


def draw_file_pills(
    base: Image.Image,
    rect: tuple[int, int, int, int],
    accent: tuple[int, int, int, int],
    files: Iterable[str],
) -> None:
    draw = ImageDraw.Draw(base)
    x1, y1, x2, y2 = rect
    current_y = y1
    pill_height = 42
    gap = 12
    available_width = x2 - x1
    for file in files:
        if current_y + pill_height > y2:
            break
        pill = (x1, current_y, x2, current_y + pill_height)
        rounded_box(base, pill, fill=with_alpha(accent, 16), outline=with_alpha(accent, 56), width=1, radius=14)
        mono_font = font(15, "mono")
        text = ellipsize_text(draw, file, mono_font, available_width - 22, mode="middle")
        draw_text(draw, (pill[0] + 12, pill[1] + 10), text, mono_font, PALETTE["ink"])
        current_y += pill_height + gap


def render_workflow_frame(step_index: int, flat: bool) -> Image.Image:
    size = (1600, 1080)
    step = WORKFLOW_STEPS[step_index]
    accent = PALETTE[step.accent_key]
    base = Image.new("RGBA", size, PALETTE["canvas_alt"] if flat else PALETTE["canvas"])
    draw = ImageDraw.Draw(base)

    title = "Claude Code · How It Works" if flat else "How Claude Code Processes A Prompt"
    subtitle = (
        "English-only slide walkthrough optimized for clean export and readable animation."
        if flat
        else "Step-by-step runtime walkthrough synthesized from the analyzed source tree."
    )
    draw_text(draw, (52, 28), title, font(44, "headline"), PALETTE["ink"])
    draw_text(draw, (54, 80), subtitle, font(19, "body"), PALETTE["muted"])
    draw_badge(base, (1364, 34, 1548, 74), f"Step {step_index + 1} / {len(WORKFLOW_STEPS)}", with_alpha(accent, 22), accent)

    draw_progress_row(base, step_index, flat)

    stage_rect = (52, 214, 1018, 716)
    user_rect = (1042, 214, 1548, 438)
    files_rect = (1042, 456, 1548, 716)
    focus_rect = (52, 744, 1548, 1010)

    draw_panel(base, stage_rect, accent, "Current Stage", shadow=not flat)
    draw_panel(base, user_rect, accent, "What The User Sees", shadow=not flat)
    draw_panel(base, files_rect, accent, "Key Source Files", shadow=not flat)
    draw_panel(base, focus_rect, accent, "What The Runtime Is Doing", shadow=not flat)

    stage_draw = ImageDraw.Draw(base)
    stage_badge = (stage_rect[0] + 38, stage_rect[1] + 58, stage_rect[0] + 118, stage_rect[1] + 96)
    draw_badge(base, stage_badge, step.chip.upper(), accent, rgba("#ffffff"))
    title_font, title_lines = fit_wrapped_font(
        stage_draw,
        step.title,
        "headline",
        38,
        28,
        stage_rect[2] - stage_rect[0] - 76,
        84,
        4,
        max_lines=2,
    )
    draw_text_lines(stage_draw, (stage_rect[0] + 38, stage_rect[1] + 112), title_lines, title_font, PALETTE["ink"], 4)
    title_height = text_block_height(stage_draw, title_lines, title_font, 4)
    subtitle_font, subtitle_lines = fit_wrapped_font(
        stage_draw,
        step.subtitle,
        "body",
        22,
        18,
        stage_rect[2] - stage_rect[0] - 76,
        86,
        5,
        max_lines=3,
    )
    subtitle_y = stage_rect[1] + 126 + title_height
    draw_text_lines(stage_draw, (stage_rect[0] + 38, subtitle_y), subtitle_lines, subtitle_font, PALETTE["muted"], 5)
    subtitle_height = text_block_height(stage_draw, subtitle_lines, subtitle_font, 5)
    draw_bullet_list(
        stage_draw,
        stage_rect[0] + 38,
        subtitle_y + subtitle_height + 22,
        stage_rect[2] - stage_rect[0] - 76,
        step.bullets,
        accent,
        "body",
        18,
        15,
    )

    user_draw = ImageDraw.Draw(base)
    user_font, user_lines = fit_wrapped_font(
        user_draw,
        step.user_view,
        "body",
        21,
        17,
        user_rect[2] - user_rect[0] - 40,
        user_rect[3] - user_rect[1] - 80,
        6,
        max_lines=7,
    )
    draw_text_lines(user_draw, (user_rect[0] + 24, user_rect[1] + 62), user_lines, user_font, PALETTE["ink"], 6)

    draw_file_pills(base, (files_rect[0] + 24, files_rect[1] + 62, files_rect[2] - 24, files_rect[3] - 24), accent, step.key_files)

    focus_draw = ImageDraw.Draw(base)
    col_gap = 24
    col_width = int((focus_rect[2] - focus_rect[0] - 48 - col_gap * 2) / 3)
    for index, point in enumerate(step.runtime_focus):
        card_x = focus_rect[0] + 24 + index * (col_width + col_gap)
        card_rect = (card_x, focus_rect[1] + 60, card_x + col_width, focus_rect[1] + 176)
        rounded_box(base, card_rect, fill=PALETTE["slate_fill"], outline=PALETTE["line"], width=1, radius=18)
        number = str(index + 1)
        number_badge = (card_rect[0] + 16, card_rect[1] + 16, card_rect[0] + 48, card_rect[1] + 48)
        rounded_box(base, number_badge, fill=accent, radius=16)
        draw_text(focus_draw, (number_badge[0] + 10, number_badge[1] + 6), number, font(17, "headline"), rgba("#ffffff"))
        point_font, point_lines = fit_wrapped_font(
            focus_draw,
            point,
            "body",
            18,
            15,
            col_width - 38,
            86,
            5,
            max_lines=4,
        )
        draw_text_lines(focus_draw, (card_rect[0] + 16, card_rect[1] + 62), point_lines, point_font, PALETTE["ink"], 5)

    summary = "Prompt -> normalization -> QueryEngine -> model stream -> permission-gated tools -> persisted session state."
    summary_rect = (focus_rect[0] + 24, focus_rect[1] + 194, focus_rect[2] - 24, focus_rect[3] - 22)
    rounded_box(base, summary_rect, fill=with_alpha(accent, 14), outline=with_alpha(accent, 48), width=1, radius=18)
    summary_font, summary_lines = fit_wrapped_font(
        focus_draw,
        summary,
        "body",
        18,
        15,
        summary_rect[2] - summary_rect[0] - 28,
        40,
        4,
        max_lines=2,
    )
    draw_text_lines(focus_draw, (summary_rect[0] + 16, summary_rect[1] + 14), summary_lines, summary_font, PALETTE["muted"], 4)

    return base


def quantize_for_gif(frames: list[Image.Image]) -> list[Image.Image]:
    rgb_frames = [frame.convert("RGB") for frame in frames]
    width, height = rgb_frames[0].size
    atlas = Image.new("RGB", (width, height * len(rgb_frames)))
    for index, frame in enumerate(rgb_frames):
        atlas.paste(frame, (0, index * height))
    palette_source = atlas.quantize(colors=255, method=Image.MEDIANCUT, dither=Image.Dither.NONE)
    return [
        frame.quantize(colors=255, method=Image.MEDIANCUT, dither=Image.Dither.NONE, palette=palette_source)
        for frame in rgb_frames
    ]


def save_pngs_and_gif(prefix: str, gif_name: str, flat: bool) -> None:
    frames: list[Image.Image] = []
    for index in range(len(WORKFLOW_STEPS)):
        frame = render_workflow_frame(index, flat=flat)
        frame.save(OUT_DIR / f"{prefix}-step-{index + 1:02d}.png")
        frames.append(frame)
    palette_frames = quantize_for_gif(frames)
    palette_frames[0].save(
        OUT_DIR / gif_name,
        save_all=True,
        append_images=palette_frames[1:],
        duration=[1350, 1350, 1350, 1350, 1350, 1450, 1900],
        loop=0,
        optimize=False,
        disposal=2,
    )


def edge_activity(image: Image.Image, margin: int = 4) -> dict[str, int]:
    rgb = image.convert("RGB")
    width, height = rgb.size
    base_color = rgb.getpixel((0, 0))

    def count_points(points: Iterable[tuple[int, int]]) -> int:
        count = 0
        for x, y in points:
            pixel = rgb.getpixel((x, y))
            if sum(abs(pixel[i] - base_color[i]) for i in range(3)) > 24:
                count += 1
        return count

    top = [(x, y) for y in range(margin) for x in range(width)]
    bottom = [(x, y) for y in range(height - margin, height) for x in range(width)]
    left = [(x, y) for x in range(margin) for y in range(height)]
    right = [(x, y) for x in range(width - margin, width) for y in range(height)]
    return {
        "top": count_points(top),
        "bottom": count_points(bottom),
        "left": count_points(left),
        "right": count_points(right),
    }


def main() -> None:
    OUT_DIR.mkdir(parents=True, exist_ok=True)

    architecture = render_architecture(flat=False)
    architecture.save(OUT_DIR / "claude-code-system-architecture.png")

    save_pngs_and_gif("claude-code-how-it-works", "claude-code-how-it-works.gif", flat=False)

    print("Generated assets:")
    print(" -", OUT_DIR / "claude-code-system-architecture.png")
    for index in range(len(WORKFLOW_STEPS)):
        print(" -", OUT_DIR / f"claude-code-how-it-works-step-{index + 1:02d}.png")
    print(" -", OUT_DIR / "claude-code-how-it-works.gif")

    print("Edge checks:")
    for name in (
        "claude-code-system-architecture.png",
        "claude-code-how-it-works-step-01.png",
    ):
        image = Image.open(OUT_DIR / name)
        print(f" - {name}: {edge_activity(image)}")


if __name__ == "__main__":
    main()
