#!/usr/bin/env python3

from __future__ import annotations

from collections import Counter, defaultdict
from dataclasses import asdict, dataclass
import json
import math
from pathlib import Path
import re

from PIL import Image, ImageDraw

import generate_architecture_assets as base


ROOT = Path(__file__).resolve().parents[1]
DOCS_DIR = ROOT / "docs"
OUT_DIR = DOCS_DIR / "assets"
SRC_DIR = ROOT / "src"

IMAGE_SUFFIXES = {".ts", ".tsx", ".js"}
ACCENT_KEYS = ["blue", "green", "orange", "purple", "teal", "rose"]
ACCENT_FILLS = {
    "blue": "blue_fill",
    "green": "green_fill",
    "orange": "orange_fill",
    "purple": "purple_fill",
    "teal": "teal_fill",
    "rose": "rose_fill",
}


@dataclass
class FileStat:
    path: str
    loc: int
    imports: int


@dataclass
class DirStat:
    name: str
    files: int
    loc: int
    imports: int
    max_file_path: str
    max_file_loc: int
    share: float
    risk_score: float = 0.0


@dataclass
class CodebaseMetrics:
    total_files: int
    total_loc: int
    feature_flags: int
    dynamic_imports: int
    top_dirs: list[DirStat]
    top_files: list[FileStat]
    command_surfaces: int
    tool_directories: int
    hook_files: int
    mcp_files: int
    plugin_files: int
    bundled_skill_registrations: int


@dataclass(frozen=True)
class SequenceStep:
    title: str
    subtitle: str
    bullets: tuple[str, ...]
    files: tuple[str, ...]
    accent_key: str


SEQUENCE_STEPS = (
    SequenceStep(
        title="1. Input Surfaces Feed The Runtime",
        subtitle="A turn can originate from the CLI, SDK/JSON transport, editor-facing integration, or a remote bridge session.",
        bullets=(
            "The bootstrap decides whether this is a fast path or a full conversational turn.",
            "Interactive sessions route into the REPL; structured/headless sessions route into print/transport paths.",
            "Startup restores session state, tools, settings, and runtime services before any model call.",
        ),
        files=(
            "src/entrypoints/cli.tsx",
            "src/main.tsx",
            "src/screens/REPL.tsx",
            "src/cli/print.ts",
        ),
        accent_key="blue",
    ),
    SequenceStep(
        title="2. User Input Is Normalized",
        subtitle="Raw terminal text becomes structured commands, attachments, messages, and hook events before QueryEngine sees it.",
        bullets=(
            "Slash commands can short-circuit before any model call.",
            "History expansion, IDE selections, and attachments become structured input.",
            "Hooks can enrich, warn, block, or rewrite the turn.",
        ),
        files=(
            "src/utils/processUserInput/processUserInput.ts",
            "src/history.ts",
            "src/utils/messages.ts",
            "src/utils/hooks.ts",
        ),
        accent_key="orange",
    ),
    SequenceStep(
        title="3. QueryEngine Assembles Context",
        subtitle="The long-lived conversation runtime builds the system prompt, memory, tool list, and turn-specific budgets.",
        bullets=(
            "Claude.md memory, attachments, and prior transcript state are incorporated here.",
            "Agent mode, custom prompts, append prompts, and settings shape the final system prompt.",
            "This is the main stateful boundary between the UI and the model/tool loop.",
        ),
        files=(
            "src/QueryEngine.ts",
            "src/query.ts",
            "src/utils/systemPrompt.ts",
            "src/utils/attachments.ts",
        ),
        accent_key="purple",
    ),
    SequenceStep(
        title="4. The Model Streams Output And Tool Requests",
        subtitle="The API layer streams assistant content, thinking blocks, and tool_use blocks back into the runtime loop.",
        bullets=(
            "The model service resolves headers, betas, and output limits.",
            "Streaming can pivot from plain text into tool_use blocks mid-turn.",
            "Context pressure and error recovery can redirect into compaction or retry behavior.",
        ),
        files=(
            "src/query.ts",
            "src/services/api/claude.ts",
            "src/services/api/errors.ts",
            "src/services/compact/autoCompact.ts",
        ),
        accent_key="teal",
    ),
    SequenceStep(
        title="5. Tool Execution Runs Under Permission Control",
        subtitle="Tool requests are validated, permission-checked, hook-aware, and orchestrated through a common runtime path.",
        bullets=(
            "Every tool call passes through validation, permission, and hook phases.",
            "Concurrency-safe tool calls can run together while unsafe calls remain serialized.",
            "Bash and PowerShell add extra safety/read-only validation on top of the shared path.",
        ),
        files=(
            "src/services/tools/toolExecution.ts",
            "src/services/tools/toolOrchestration.ts",
            "src/tools/BashTool/bashSecurity.ts",
            "src/utils/permissions/filesystem.ts",
        ),
        accent_key="rose",
    ),
    SequenceStep(
        title="6. Results Persist Into The Next Turn",
        subtitle="Tool results, transcript updates, task state, compaction boundaries, and session metadata all become resumable state.",
        bullets=(
            "JSONL transcripts and sidecar metadata preserve the working thread.",
            "Task registries and agent state update in the same boundary.",
            "Compaction and session-memory flows prevent long-running sessions from collapsing under context pressure.",
        ),
        files=(
            "src/utils/sessionStorage.ts",
            "src/services/compact/compact.ts",
            "src/services/compact/sessionMemoryCompact.ts",
            "src/tasks/LocalAgentTask/LocalAgentTask.tsx",
        ),
        accent_key="green",
    ),
)


def rel_path(path: Path) -> str:
    return path.relative_to(ROOT).as_posix()


def count_lines(path: Path) -> int:
    with path.open("r", encoding="utf-8", errors="ignore") as handle:
        return sum(1 for _ in handle)


def count_imports(text: str) -> int:
    static_imports = len(re.findall(r"(?m)^\s*import\b", text))
    requires = len(re.findall(r"require\(", text))
    return static_imports + requires


def compute_metrics() -> CodebaseMetrics:
    files = [path for path in SRC_DIR.rglob("*") if path.is_file() and path.suffix in IMAGE_SUFFIXES]
    feature_pattern = re.compile(r'feature\((?:await\s+)?["\'` ]*([A-Z0-9_]+)["\'` ]*')
    feature_flags: set[str] = set()
    top_level: dict[str, dict[str, object]] = {}
    file_stats: list[FileStat] = []
    dynamic_imports = 0

    total_loc = 0
    for path in files:
        text = path.read_text(encoding="utf-8", errors="ignore")
        loc = len(text.splitlines())
        imports = count_imports(text)
        total_loc += loc
        feature_flags.update(feature_pattern.findall(text))
        dynamic_imports += text.count("import(")
        file_stats.append(FileStat(path=rel_path(path), loc=loc, imports=imports))

        relative = path.relative_to(SRC_DIR)
        top_name = relative.parts[0] if len(relative.parts) > 1 else "root-files"
        bucket = top_level.setdefault(
            top_name,
            {"files": 0, "loc": 0, "imports": 0, "max_file_path": "", "max_file_loc": 0},
        )
        bucket["files"] = int(bucket["files"]) + 1
        bucket["loc"] = int(bucket["loc"]) + loc
        bucket["imports"] = int(bucket["imports"]) + imports
        if loc > int(bucket["max_file_loc"]):
            bucket["max_file_loc"] = loc
            bucket["max_file_path"] = rel_path(path)

    dir_stats: list[DirStat] = []
    for name, raw in top_level.items():
        dir_stats.append(
            DirStat(
                name=name,
                files=int(raw["files"]),
                loc=int(raw["loc"]),
                imports=int(raw["imports"]),
                max_file_path=str(raw["max_file_path"]),
                max_file_loc=int(raw["max_file_loc"]),
                share=(int(raw["loc"]) / total_loc) if total_loc else 0.0,
            )
        )

    max_loc = max(stat.loc for stat in dir_stats)
    max_files = max(stat.files for stat in dir_stats)
    max_imports = max(stat.imports for stat in dir_stats)
    max_file_loc = max(stat.max_file_loc for stat in dir_stats)
    for stat in dir_stats:
        stat.risk_score = round(
            45 * stat.loc / max_loc
            + 20 * stat.files / max_files
            + 20 * stat.imports / max_imports
            + 15 * stat.max_file_loc / max_file_loc,
            1,
        )

    dir_stats.sort(key=lambda item: item.loc, reverse=True)
    file_stats.sort(key=lambda item: item.loc, reverse=True)

    bundled_skill_registrations = len(
        re.findall(
            r"export function register[A-Za-z0-9]+Skill",
            "\n".join(
                path.read_text(encoding="utf-8", errors="ignore")
                for path in (SRC_DIR / "skills" / "bundled").glob("*.ts")
            ),
        )
    )

    return CodebaseMetrics(
        total_files=len(files),
        total_loc=total_loc,
        feature_flags=len(feature_flags),
        dynamic_imports=dynamic_imports,
        top_dirs=dir_stats,
        top_files=file_stats,
        command_surfaces=len([path for path in (SRC_DIR / "commands").iterdir() if path.is_dir()]),
        tool_directories=len([path for path in (SRC_DIR / "tools").iterdir() if path.is_dir()]),
        hook_files=len(list((SRC_DIR / "hooks").rglob("*.ts"))) + len(list((SRC_DIR / "hooks").rglob("*.tsx"))),
        mcp_files=len(list((SRC_DIR / "services" / "mcp").rglob("*.ts")))
        + len(list((SRC_DIR / "services" / "mcp").rglob("*.tsx"))),
        plugin_files=len(list((SRC_DIR / "utils" / "plugins").rglob("*.ts")))
        + len(list((SRC_DIR / "utils" / "plugins").rglob("*.tsx")))
        + len(list((SRC_DIR / "plugins").rglob("*.ts"))),
        bundled_skill_registrations=bundled_skill_registrations,
    )


def ensure_dirs() -> None:
    DOCS_DIR.mkdir(parents=True, exist_ok=True)
    OUT_DIR.mkdir(parents=True, exist_ok=True)


def draw_title(draw: ImageDraw.ImageDraw, title: str, subtitle: str) -> None:
    base.draw_text(draw, (56, 30), title, base.font(46, "headline"), base.PALETTE["ink"])
    base.draw_text(draw, (58, 84), subtitle, base.font(20), base.PALETTE["muted"])


def pct_text(value: float) -> str:
    return f"{value * 100:.1f}%"


def metric_label(stat: DirStat) -> str:
    return f"{stat.loc:,} LOC · {stat.files} files · {pct_text(stat.share)}"


def display_name(name: str) -> str:
    return name.replace("-", " ")


def accent_fill(accent_key: str) -> tuple[int, int, int, int]:
    return base.PALETTE[ACCENT_FILLS.get(accent_key, "slate_fill")]


def rect_center(rect: tuple[int, int, int, int]) -> tuple[int, int]:
    return ((rect[0] + rect[2]) // 2, (rect[1] + rect[3]) // 2)


def edge_point_toward(
    source: tuple[int, int, int, int],
    target: tuple[int, int, int, int],
) -> tuple[int, int]:
    cx, cy = rect_center(source)
    tx, ty = rect_center(target)
    dx = tx - cx
    dy = ty - cy
    half_w = max(1, (source[2] - source[0]) / 2)
    half_h = max(1, (source[3] - source[1]) / 2)
    scale = max(abs(dx) / half_w if dx else 0, abs(dy) / half_h if dy else 0, 1)
    return round(cx + dx / scale), round(cy + dy / scale)


def draw_link(
    draw: ImageDraw.ImageDraw,
    source: tuple[int, int, int, int],
    target: tuple[int, int, int, int],
    accent: tuple[int, int, int, int],
    width: int = 5,
) -> None:
    start = edge_point_toward(source, target)
    end = edge_point_toward(target, source)
    draw.line((start, end), fill=base.with_alpha(accent, 118), width=width)
    draw.ellipse((start[0] - 6, start[1] - 6, start[0] + 6, start[1] + 6), fill=accent)
    draw.ellipse((end[0] - 6, end[1] - 6, end[0] + 6, end[1] + 6), fill=accent)


def draw_stat_chip(
    image: Image.Image,
    rect: tuple[int, int, int, int],
    label: str,
    value: str,
    accent_key: str,
) -> None:
    accent = base.PALETTE[accent_key]
    base.rounded_box(
        image,
        rect,
        fill=base.PALETTE["paper"],
        outline=base.PALETTE["line"],
        width=1,
        radius=22,
        shadow=True,
        shadow_alpha=8,
    )
    draw = ImageDraw.Draw(image)
    base.draw_text(draw, (rect[0] + 20, rect[1] + 18), label, base.font(14, "headline"), base.PALETTE["muted"])
    base.draw_text(draw, (rect[0] + 20, rect[1] + 46), value, base.font(28, "headline"), base.PALETTE["ink"])
    draw.rounded_rectangle((rect[2] - 40, rect[1] + 16, rect[2] - 20, rect[1] + 36), radius=10, fill=base.with_alpha(accent, 86))


def draw_metric_bar(
    image: Image.Image,
    rect: tuple[int, int, int, int],
    label: str,
    value_text: str,
    ratio: float,
    accent_key: str,
) -> None:
    accent = base.PALETTE[accent_key]
    draw = ImageDraw.Draw(image)
    base.draw_text(draw, (rect[0], rect[1]), label, base.font(13, "headline"), base.PALETTE["muted"])
    value_font = base.font(18, "headline")
    value_text = base.ellipsize_text(draw, value_text, value_font, rect[2] - rect[0])
    base.draw_text(draw, (rect[0], rect[1] + 20), value_text, value_font, base.PALETTE["ink"])
    track = (rect[0], rect[3] - 16, rect[2], rect[3] - 4)
    base.rounded_box(image, track, fill=base.PALETTE["slate_fill"], radius=6)
    fill_w = max(12, round((track[2] - track[0]) * max(0.05, min(ratio, 1.0))))
    draw.rounded_rectangle((track[0], track[1], track[0] + fill_w, track[3]), radius=6, fill=accent)


def draw_kicker(draw: ImageDraw.ImageDraw, xy: tuple[int, int], text: str, accent_key: str) -> None:
    accent = base.PALETTE[accent_key]
    fill = accent_fill(accent_key)
    padding_x = 18
    padding_y = 10
    use_font = base.font(16, "headline")
    width, height = base.text_size(draw, text, use_font)
    rect = (xy[0], xy[1], xy[0] + width + padding_x * 2, xy[1] + height + padding_y * 2)
    draw.rounded_rectangle(rect, radius=(rect[3] - rect[1]) // 2, fill=fill, outline=base.with_alpha(accent, 54), width=1)
    base.draw_text(draw, (xy[0] + padding_x, xy[1] + padding_y - 1), text, use_font, accent)


def slice_treemap(
    items: list[DirStat],
    rect: tuple[int, int, int, int],
    horizontal: bool | None = None,
) -> list[tuple[DirStat, tuple[int, int, int, int]]]:
    if not items:
        return []
    if len(items) == 1:
        return [(items[0], rect)]
    x1, y1, x2, y2 = rect
    width = x2 - x1
    height = y2 - y1
    if horizontal is None:
        horizontal = width >= height
    total = sum(item.loc for item in items)
    half = total / 2
    running = 0
    split_index = 1
    for index, item in enumerate(items[:-1], start=1):
        running += item.loc
        split_index = index
        if running >= half:
            break

    left_items = items[:split_index]
    right_items = items[split_index:]
    left_total = sum(item.loc for item in left_items)
    ratio = left_total / total if total else 0.5
    if horizontal:
        split_x = max(x1 + 140, min(x2 - 140, x1 + round(width * ratio)))
        left_rect = (x1, y1, split_x, y2)
        right_rect = (split_x, y1, x2, y2)
    else:
        split_y = max(y1 + 120, min(y2 - 120, y1 + round(height * ratio)))
        left_rect = (x1, y1, x2, split_y)
        right_rect = (x1, split_y, x2, y2)
    return slice_treemap(left_items, left_rect, not horizontal) + slice_treemap(right_items, right_rect, not horizontal)


def render_hotspot_treemap(metrics: CodebaseMetrics) -> Path:
    size = (2000, 1320)
    image = Image.new("RGBA", size, base.PALETTE["canvas_alt"])
    draw = ImageDraw.Draw(image)
    draw_title(
        draw,
        "Codebase Hotspots Treemap",
        "Directory footprint and oversized-file concentration derived from the analyzed src/ tree.",
    )
    base.draw_badge(
        image,
        (1534, 34, 1682, 72),
        f"{metrics.total_files:,} files",
        base.with_alpha(base.PALETTE["blue"], 22),
        base.PALETTE["blue"],
    )
    base.draw_badge(
        image,
        (1696, 34, 1846, 72),
        f"{metrics.total_loc:,} LOC",
        base.with_alpha(base.PALETTE["green"], 22),
        base.PALETTE["green"],
    )
    base.draw_badge(
        image,
        (1860, 34, 1946, 72),
        "src/",
        base.with_alpha(base.PALETTE["purple"], 18),
        base.PALETTE["purple"],
    )

    treemap_rect = (56, 132, 1348, 1224)
    sidebar_rect = (1378, 132, 1944, 1224)
    base.rounded_box(image, treemap_rect, fill=base.PALETTE["paper"], outline=base.PALETTE["line"], width=1, radius=30, shadow=True, shadow_alpha=12)
    base.rounded_box(image, sidebar_rect, fill=base.PALETTE["paper"], outline=base.PALETTE["line"], width=1, radius=30, shadow=True, shadow_alpha=12)
    draw_kicker(draw, (84, 154), "Footprint map", "blue")
    base.draw_text(draw, (84, 208), "Top-level directories sized by LOC", base.font(28, "headline"), base.PALETTE["ink"])
    base.draw_text(draw, (84, 246), "Only the largest buckets are labeled inside the map. Detailed readouts move to the right rail so the chart stays readable.", base.font(18), base.PALETTE["muted"])
    draw_kicker(draw, (1404, 154), "Readout rail", "purple")
    base.draw_text(draw, (1404, 208), "Top directories and largest files", base.font(28, "headline"), base.PALETTE["ink"])

    accent_cycle = [base.PALETTE[key] for key in ACCENT_KEYS]
    major_dirs = metrics.top_dirs[:8]
    other_loc = sum(stat.loc for stat in metrics.top_dirs[8:])
    other_files = sum(stat.files for stat in metrics.top_dirs[8:])
    other_imports = sum(stat.imports for stat in metrics.top_dirs[8:])
    if other_loc:
        major_dirs = major_dirs + [
            DirStat(
                name="other",
                files=other_files,
                loc=other_loc,
                imports=other_imports,
                max_file_path=metrics.top_dirs[10].max_file_path,
                max_file_loc=metrics.top_dirs[10].max_file_loc,
                share=other_loc / metrics.total_loc,
                risk_score=metrics.top_dirs[10].risk_score,
            )
        ]

    cells = slice_treemap(major_dirs, (84, 304, 1322, 1142))
    for index, (stat, rect) in enumerate(cells):
        accent_key = ACCENT_KEYS[index % len(ACCENT_KEYS)]
        accent = accent_cycle[index % len(accent_cycle)]
        fill = accent_fill(accent_key)
        base.rounded_box(image, rect, fill=fill, outline=base.with_alpha(accent, 72), width=2, radius=26)
        x1, y1, x2, y2 = rect
        draw.rounded_rectangle((x1 + 16, y1 + 16, x1 + 24, y2 - 16), radius=4, fill=accent)

        available_w = x2 - x1 - 52
        available_h = y2 - y1
        title_font, title_lines = base.fit_wrapped_font(
            draw,
            display_name(stat.name),
            "headline",
            34 if available_w > 260 else 28,
            18,
            available_w,
            74,
            4,
            max_lines=2,
        )
        base.draw_text_lines(draw, (x1 + 36, y1 + 22), title_lines, title_font, base.PALETTE["ink"], 4)
        title_height = base.text_block_height(draw, title_lines, title_font, 4)

        if available_w > 170 and available_h > 134:
            summary = f"{stat.loc:,} LOC"
            if available_w > 240:
                summary += f" · {stat.files} files"
            base.draw_text(draw, (x1 + 36, y1 + 34 + title_height), summary, base.font(17, "headline"), base.PALETTE["muted"])
            if available_h > 200:
                detail = base.ellipsize_text(draw, f"Largest file: {Path(stat.max_file_path).name}", base.font(15), available_w)
                base.draw_text(draw, (x1 + 36, y1 + 62 + title_height), detail, base.font(15), base.PALETTE["muted"])

        share_text = pct_text(stat.share)
        share_font = base.font(18, "headline")
        share_w, share_h = base.text_size(draw, share_text, share_font)
        chip = (x1 + 20, y2 - share_h - 22, x1 + share_w + 38, y2 - 14)
        base.rounded_box(image, chip, fill=accent_fill(accent_key), radius=18)
        base.draw_text(draw, (chip[0] + 12, chip[1] + 6), share_text, share_font, accent)

    summary_cards = metrics.top_dirs[:4]
    card_y = 282
    for index, stat in enumerate(summary_cards):
        accent_key = ACCENT_KEYS[index % len(ACCENT_KEYS)]
        accent = base.PALETTE[accent_key]
        rect = (1402, card_y, 1920, card_y + 126)
        base.rounded_box(image, rect, fill=accent_fill(accent_key), outline=base.PALETTE["line"], width=1, radius=24)
        draw.rounded_rectangle((rect[0] + 18, rect[1] + 18, rect[0] + 26, rect[3] - 18), radius=4, fill=accent)
        base.draw_text(draw, (rect[0] + 42, rect[1] + 16), display_name(stat.name), base.font(24, "headline"), base.PALETTE["ink"])
        base.draw_text(draw, (rect[0] + 42, rect[1] + 50), f"{stat.loc:,} LOC · {stat.files} files · {stat.imports:,} imports", base.font(16), base.PALETTE["muted"])
        largest = base.ellipsize_text(draw, f"Largest file: {Path(stat.max_file_path).name}", base.font(15), 438)
        base.draw_text(draw, (rect[0] + 42, rect[1] + 78), largest, base.font(15), base.PALETTE["muted"])
        risk_rect = (rect[2] - 116, rect[1] + 18, rect[2] - 18, rect[1] + 56)
        base.rounded_box(image, risk_rect, fill=base.PALETTE["paper"], outline=base.with_alpha(accent, 52), width=1, radius=18)
        base.draw_text(draw, (risk_rect[0] + 14, risk_rect[1] + 8), f"Risk {stat.risk_score:.1f}", base.font(16, "headline"), accent)
        card_y += 142

    base.draw_text(draw, (1404, 846), "Largest files", base.font(24, "headline"), base.PALETTE["ink"])
    current_y = 886
    for rank, file_stat in enumerate(metrics.top_files[:5], start=1):
        item_rect = (1402, current_y, 1920, current_y + 56)
        base.rounded_box(image, item_rect, fill=base.PALETTE["slate_fill"], outline=base.PALETTE["line"], width=1, radius=20)
        badge = (1418, current_y + 10, 1454, current_y + 46)
        base.rounded_box(image, badge, fill=base.PALETTE["ink"], radius=16)
        base.draw_text(draw, (1429, current_y + 13), str(rank), base.font(16, "headline"), base.rgba("#ffffff"))
        path_text = base.ellipsize_text(draw, file_stat.path, base.font(14, "mono"), 392, mode="middle")
        base.draw_text(draw, (1472, current_y + 10), path_text, base.font(14, "mono"), base.PALETTE["ink"])
        base.draw_text(draw, (1472, current_y + 31), f"{file_stat.loc:,} LOC · {file_stat.imports} imports", base.font(14), base.PALETTE["muted"])
        current_y += 64

    footer_rect = (56, 1244, 1944, 1300)
    base.rounded_box(image, footer_rect, fill=base.PALETTE["paper"], outline=base.PALETTE["line"], width=1, radius=20)
    footer = "Reading: utils/, components/, services/, and tools/ dominate the footprint. The right rail highlights where size concentration turns into likely maintenance drag."
    footer_font, footer_lines = base.fit_wrapped_font(draw, footer, "body", 18, 16, 1840, 40, 4, max_lines=2)
    base.draw_text_lines(draw, (80, 1261), footer_lines, footer_font, base.PALETTE["muted"], 4)
    out_path = OUT_DIR / "codebase-hotspots-treemap.png"
    image.save(out_path)
    return out_path


def heat_color(value: float, accent: tuple[int, int, int, int]) -> tuple[int, int, int, int]:
    alpha = 12 + int(140 * value)
    return base.with_alpha(accent, alpha)


def render_risk_heatmap(metrics: CodebaseMetrics) -> Path:
    size = (1920, 1280)
    image = Image.new("RGBA", size, base.PALETTE["canvas_alt"])
    draw = ImageDraw.Draw(image)
    draw_title(
        draw,
        "Codebase Risk Heatmap",
        "Composite risk score by major directory. Higher values combine LOC, file count, import fan-out, and largest-file concentration.",
    )
    top_dirs = metrics.top_dirs[:10]
    headers = ["Directory", "LOC", "Files", "Imports", "Largest File", "Risk"]
    widths = [290, 190, 168, 188, 208, 124]
    table_x = 60
    table_y = 168
    row_h = 94
    table_w = sum(widths)

    base.rounded_box(image, (table_x - 4, table_y - 8, table_x + table_w + 4, 1156), fill=base.PALETTE["paper"], outline=base.PALETTE["line"], width=1, radius=28, shadow=True, shadow_alpha=12)
    draw_kicker(draw, (84, 184), "Composite score", "rose")
    base.draw_text(draw, (84, 236), "Directory-level concentration and risk", base.font(28, "headline"), base.PALETTE["ink"])
    base.draw_text(draw, (84, 272), "Each row combines code volume, breadth, import fan-out, and largest-file concentration. Bars show the relative position within the top directories.", base.font(18), base.PALETTE["muted"])
    header_y = 328
    base.rounded_box(image, (table_x + 20, header_y, table_x + table_w - 20, header_y + 60), fill=base.PALETTE["ink"], radius=20)
    current_x = table_x
    for header, width in zip(headers, widths):
        base.draw_text(draw, (current_x + 22, header_y + 16), header, base.font(18, "headline"), base.rgba("#ffffff"))
        current_x += width

    max_loc = max(stat.loc for stat in top_dirs)
    max_files = max(stat.files for stat in top_dirs)
    max_imports = max(stat.imports for stat in top_dirs)
    max_largest = max(stat.max_file_loc for stat in top_dirs)
    max_risk = max(stat.risk_score for stat in top_dirs)

    current_y = header_y + 76
    for index, stat in enumerate(top_dirs):
        bg = base.PALETTE["paper"] if index % 2 == 0 else base.PALETTE["slate_fill"]
        base.rounded_box(image, (table_x + 20, current_y, table_x + table_w - 20, current_y + row_h), fill=bg, outline=base.PALETTE["line"], width=1, radius=20)
        cell_x = table_x
        name_x = cell_x + 22
        base.draw_text(draw, (name_x, current_y + 18), display_name(stat.name), base.font(20, "headline"), base.PALETTE["ink"])
        base.draw_text(draw, (name_x, current_y + 50), f"{pct_text(stat.share)} of total LOC", base.font(15), base.PALETTE["muted"])
        cell_x += widths[0]
        draw_metric_bar(image, (cell_x + 18, current_y + 14, cell_x + widths[1] - 18, current_y + row_h - 16), "LOC", f"{stat.loc:,}", stat.loc / max_loc, "green")
        cell_x += widths[1]
        draw_metric_bar(image, (cell_x + 18, current_y + 14, cell_x + widths[2] - 18, current_y + row_h - 16), "Files", str(stat.files), stat.files / max_files, "orange")
        cell_x += widths[2]
        draw_metric_bar(image, (cell_x + 18, current_y + 14, cell_x + widths[3] - 18, current_y + row_h - 16), "Imports", f"{stat.imports:,}", stat.imports / max_imports, "purple")
        cell_x += widths[3]
        draw_metric_bar(image, (cell_x + 18, current_y + 14, cell_x + widths[4] - 18, current_y + row_h - 16), "Largest", f"{stat.max_file_loc:,}", stat.max_file_loc / max_largest, "teal")
        cell_x += widths[4]
        risk_ratio = stat.risk_score / max_risk
        accent = base.PALETTE["rose"]
        risk_rect = (cell_x + 20, current_y + 18, cell_x + widths[5] - 18, current_y + row_h - 18)
        base.rounded_box(image, risk_rect, fill=base.with_alpha(accent, 16 + int(42 * risk_ratio)), outline=base.with_alpha(accent, 84), width=1, radius=18)
        base.draw_text(draw, (risk_rect[0] + 20, risk_rect[1] + 16), f"{stat.risk_score:.1f}", base.font(24, "headline"), base.PALETTE["ink"])
        current_y += row_h + 10

    notes_rect = (1356, 168, 1862, 1156)
    base.rounded_box(image, notes_rect, fill=base.PALETTE["paper"], outline=base.PALETTE["line"], width=1, radius=26, shadow=True, shadow_alpha=10)
    draw_kicker(draw, (1380, 188), "Engineering readout", "rose")
    base.draw_text(draw, (1380, 240), "Where review attention should go first", base.font(28, "headline"), base.PALETTE["ink"])
    focus_blocks = [
        ("Gravity well", f"{display_name(top_dirs[0].name)} dominates both size and spread. It is the likeliest source of cross-cutting maintenance drag.", "rose"),
        ("Broad UI surface", f"{display_name(top_dirs[1].name)} is large because it spans many files. That usually means breadth and coupling, not just one oversized hotspot.", "purple"),
        ("Runtime policy layers", "services/ and tools/ are where permissions, orchestration, shell safety, MCP boundaries, and runtime contracts accumulate.", "teal"),
        ("Central trunks", "commands/ and root runtime files are smaller by LOC, but they often sit on critical invocation and control-flow boundaries.", "orange"),
    ]
    note_y = 302
    for title, body, accent_key in focus_blocks:
        accent = base.PALETTE[accent_key]
        rect = (1380, note_y, 1838, note_y + 132)
        base.rounded_box(image, rect, fill=base.PALETTE["slate_fill"], outline=base.PALETTE["line"], width=1, radius=22)
        base.draw_text(draw, (1400, note_y + 16), title, base.font(19, "headline"), accent)
        font_obj, lines = base.fit_wrapped_font(draw, body, "body", 16, 14, 418, 72, 4, max_lines=4)
        base.draw_text_lines(draw, (1400, note_y + 48), lines, font_obj, base.PALETTE["ink"], 4)
        note_y += 146

    base.draw_text(draw, (1380, 908), "Risk band", base.font(20, "headline"), base.PALETTE["ink"])
    legend = [("Low", 0.2), ("Guarded", 0.4), ("Moderate", 0.6), ("High", 0.8), ("Critical", 1.0)]
    for idx, (label, ratio) in enumerate(legend):
        accent = base.PALETTE["rose"]
        box = (1380 + idx * 92, 948, 1450 + idx * 92, 990)
        base.rounded_box(image, box, fill=base.with_alpha(accent, 14 + int(48 * ratio)), radius=14)
        base.draw_text(draw, (1392 + idx * 92, 960), label, base.font(14, "headline"), base.PALETTE["ink"])

    base.draw_text(draw, (64, 1224), "Method: composite score = normalized LOC + file count + import references + largest-file size. Treat it as a prioritization lens, not a substitute for runtime tracing.", base.font(18), base.PALETTE["muted"])
    out_path = OUT_DIR / "codebase-risk-heatmap.png"
    image.save(out_path)
    return out_path


TOOL_MATRIX_ROWS = [
    ("File Read / Write / Edit", ["yes", "yes", "yes", "yes", "partial", "no", "yes"]),
    ("Bash Tool", ["yes", "yes", "yes", "yes", "yes", "partial", "yes"]),
    ("PowerShell Tool", ["yes", "yes", "yes", "yes", "yes", "partial", "yes"]),
    ("Web Fetch / Search", ["yes", "yes", "yes", "yes", "partial", "yes", "no"]),
    ("MCP Tools", ["yes", "yes", "yes", "yes", "partial", "yes", "partial"]),
    ("Agent / Team Tools", ["yes", "yes", "yes", "yes", "yes", "partial", "yes"]),
    ("Skill Tool", ["yes", "yes", "yes", "yes", "yes", "partial", "yes"]),
]

TOOL_MATRIX_NOTES = {
    "File Read / Write / Edit": "Repo-local navigation, grep/glob, and mutation surfaces.",
    "Bash Tool": "Shell execution plus dedicated bashSecurity and read-only checks.",
    "PowerShell Tool": "Windows shell path with comparable gating and preview-style positioning.",
    "Web Fetch / Search": "Network-facing research surface with lighter side-effect risk.",
    "MCP Tools": "External server protocol; trust boundary extends beyond the repo.",
    "Agent / Team Tools": "Delegated/background execution that can reshape next-turn state.",
    "Skill Tool": "Capability packs that influence prompt/runtime behavior and execution.",
}


def matrix_cell_color(value: str) -> tuple[int, int, int, int]:
    if value == "yes":
        return base.PALETTE["green_fill"]
    if value == "partial":
        return base.PALETTE["orange_fill"]
    return base.PALETTE["slate_fill"]


def matrix_cell_label(value: str) -> str:
    return {"yes": "Yes", "partial": "Partial", "no": "No"}[value]


def render_tool_permission_matrix() -> Path:
    size = (1920, 1360)
    image = Image.new("RGBA", size, base.PALETTE["canvas_alt"])
    draw = ImageDraw.Draw(image)
    draw_title(
        draw,
        "Tool Permission Matrix",
        "Shared tool orchestration path plus notable extra controls by tool family.",
    )
    columns = [
        "Validation",
        "Gate",
        "Hooks",
        "Policy",
        "Concurrency",
        "External I/O",
        "Side Effects",
    ]
    left = 60
    top = 168
    row_h = 84
    first_col = 420
    col_w = 176
    total_w = first_col + col_w * len(columns)

    base.rounded_box(image, (56, 158, 1864, 1298), fill=base.PALETTE["paper"], outline=base.PALETTE["line"], width=1, radius=28, shadow=True, shadow_alpha=12)
    draw_kicker(draw, (84, 182), "Shared orchestration path", "blue")
    base.draw_text(draw, (84, 234), "Which tool families pass through which controls", base.font(28, "headline"), base.PALETTE["ink"])
    base.draw_text(draw, (84, 270), "All rows share the same execution spine. The matrix highlights where extra safety, policy, or external trust boundaries show up.", base.font(18), base.PALETTE["muted"])

    header_y = 322
    base.rounded_box(image, (left, header_y, left + total_w, header_y + 62), fill=base.PALETTE["ink"], radius=20)
    base.draw_text(draw, (left + 20, header_y + 16), "Tool Family", base.font(19, "headline"), base.rgba("#ffffff"))
    for idx, column in enumerate(columns):
        x = left + first_col + idx * col_w
        base.draw_text(draw, (x + 16, header_y + 16), column, base.font(16, "headline"), base.rgba("#ffffff"))

    current_y = header_y + 76
    for row_name, values in TOOL_MATRIX_ROWS:
        base.rounded_box(image, (left, current_y, left + total_w, current_y + row_h), fill=base.PALETTE["paper"] if (current_y // 10) % 2 else base.PALETTE["slate_fill"], outline=base.PALETTE["line"], width=1, radius=22)
        base.draw_text(draw, (left + 18, current_y + 16), row_name, base.font(20, "headline"), base.PALETTE["ink"])
        sub = TOOL_MATRIX_NOTES[row_name]
        sub_font, sub_lines = base.fit_wrapped_font(draw, sub, "body", 14, 13, first_col - 34, 42, 3, max_lines=2)
        base.draw_text_lines(draw, (left + 18, current_y + 46), sub_lines, sub_font, base.PALETTE["muted"], 3)
        for idx, value in enumerate(values):
            x = left + first_col + idx * col_w
            cell = (x + 12, current_y + 16, x + col_w - 12, current_y + row_h - 16)
            base.rounded_box(image, cell, fill=matrix_cell_color(value), outline=base.PALETTE["line"], width=1, radius=18)
            label = matrix_cell_label(value)
            label_w, _ = base.text_size(draw, label, base.font(18, "headline"))
            base.draw_text(draw, (cell[0] + (cell[2] - cell[0] - label_w) / 2, cell[1] + 16), label, base.font(18, "headline"), base.PALETTE["ink"])
        current_y += row_h + 10

    notes_rect = (60, 1058, 1860, 1298)
    base.rounded_box(image, notes_rect, fill=base.PALETTE["paper"], outline=base.PALETTE["line"], width=1, radius=26, shadow=True, shadow_alpha=10)
    base.draw_text(draw, (84, 1070), "Interpretation Notes", base.font(24, "headline"), base.PALETTE["ink"])
    notes = (
        "Bash and PowerShell are the strictest families. They inherit the shared gate and then add dedicated shell-specific safety layers.",
        "MCP is where trust leaves the repo boundary, so external I/O and compatibility concerns rise even though the orchestration path stays familiar.",
        "Agent and Skill surfaces matter because they can spawn more execution, persist state, or reshape the next-turn context instead of only returning text.",
        "Hook awareness shows up across the board because pre/post execution hooks and permission-denied hooks live in the common orchestration spine.",
    )
    base.draw_bullet_list(draw, 84, 1112, 1728, notes, base.PALETTE["blue"], "body", 16, 14)
    base.draw_text(draw, (60, 1312), "Key sources: src/services/tools/toolExecution.ts, src/services/tools/toolOrchestration.ts, src/utils/permissions/filesystem.ts, src/tools/BashTool/*, src/tools/PowerShellTool/*.", base.font(18), base.PALETTE["muted"])
    out_path = OUT_DIR / "tool-permission-matrix.png"
    image.save(out_path)
    return out_path


def render_session_lifecycle() -> Path:
    size = (1920, 1240)
    image = Image.new("RGBA", size, base.PALETTE["canvas_alt"])
    draw = ImageDraw.Draw(image)
    draw_title(
        draw,
        "Session Lifecycle",
        "How transcript persistence, compaction, resume, and task/agent state form the long-lived Claude Code session model.",
    )

    steps = [
        ("Entry", "A new or resumed prompt enters the long-lived runtime."),
        ("Persist Transcript", "Messages, tool results, and sidecar metadata land in transcript storage."),
        ("Update Tasks", "Local agents, remote agents, and notifications advance beside the transcript."),
        ("Check Pressure", "Token budgets and history boundaries decide whether compaction is needed."),
        ("Compact / Restore", "Older context is summarized, relinked, or resumed from stored memory."),
        ("Resume Next Turn", "The following prompt restarts from persisted state instead of from zero."),
    ]
    step_rects: list[tuple[int, int, int, int]] = []
    y = 226
    step_w = 262
    gap = 28
    start_x = 70
    timeline_y = 410
    draw_kicker(draw, (70, 154), "Long-lived runtime model", "blue")
    base.draw_text(draw, (70, 206), "A session is a persisted state machine, not a stateless chat loop", base.font(30, "headline"), base.PALETTE["ink"])
    draw.line((90, timeline_y, 1830, timeline_y), fill=base.PALETTE["line_dark"], width=8)

    for idx, (title, subtitle) in enumerate(steps):
        x = start_x + idx * (step_w + gap)
        rect = (x, y, x + step_w, y + 150)
        step_rects.append(rect)
        accent_key = ACCENT_KEYS[idx % len(ACCENT_KEYS)]
        accent = base.PALETTE[accent_key]
        base.rounded_box(image, rect, fill=accent_fill(accent_key), outline=base.with_alpha(accent, 72), width=2, radius=28, shadow=True, shadow_alpha=10)
        badge = (x + 18, y + 18, x + 60, y + 60)
        base.rounded_box(image, badge, fill=accent, radius=18)
        base.draw_text(draw, (x + 32, y + 24), str(idx + 1), base.font(20, "headline"), base.rgba("#ffffff"))
        title_font, title_lines = base.fit_wrapped_font(draw, title, "headline", 25, 18, step_w - 36, 54, 3, max_lines=2)
        base.draw_text_lines(draw, (x + 18, y + 76), title_lines, title_font, accent, 3)
        title_h = base.text_block_height(draw, title_lines, title_font, 3)
        font_obj, lines = base.fit_wrapped_font(draw, subtitle, "body", 16, 14, step_w - 36, 54, 4, max_lines=3)
        base.draw_text_lines(draw, (x + 18, y + 88 + title_h), lines, font_obj, base.PALETTE["muted"], 4)
        if idx < len(steps) - 1:
            x1 = rect[2]
            x2 = rect[2] + gap
            draw.line((x1 + 6, timeline_y, x2 - 8, timeline_y), fill=base.PALETTE["line_dark"], width=6)
            draw.polygon([(x2 - 8, timeline_y), (x2 - 20, timeline_y - 9), (x2 - 20, timeline_y + 9)], fill=base.PALETTE["line_dark"])

    store_rects = [
        ((90, 566, 566, 794), "Transcript Store", "JSONL messages, sidecar metadata, resume titles, and compact boundaries live here.", "purple"),
        ((724, 566, 1198, 794), "Session Memory + Claude.md", "Session memory, recovered context, and session-start rebuild logic preserve continuity beyond the visible turn.", "teal"),
        ((1354, 566, 1830, 794), "Task / Agent Registries", "Local agents, remote agents, notifications, and task state evolve beside the transcript instead of outside it.", "rose"),
    ]
    for rect, title, subtitle, accent_key in store_rects:
        accent = base.PALETTE[accent_key]
        base.rounded_box(image, rect, fill=base.PALETTE["paper"], outline=base.with_alpha(accent, 72), width=2, radius=26)
        base.draw_text(draw, (rect[0] + 20, rect[1] + 18), title, base.font(22, "headline"), accent)
        font_obj, lines = base.fit_wrapped_font(draw, subtitle, "body", 17, 14, rect[2] - rect[0] - 40, 92, 5, max_lines=5)
        base.draw_text_lines(draw, (rect[0] + 20, rect[1] + 62), lines, font_obj, base.PALETTE["ink"], 5)

    connectors = [
        (step_rects[1][0] + 120, step_rects[1][3], 328, 566),
        (step_rects[4][0] + 126, step_rects[4][3], 960, 566),
        (step_rects[2][0] + 122, step_rects[2][3], 1592, 566),
    ]
    for x1, y1, x2, y2 in connectors:
        draw.line((x1, y1, x2, y2), fill=base.PALETTE["line_dark"], width=4)
        draw.polygon([(x2, y2), (x2 - 10, y2 - 8), (x2 + 10, y2 - 8)], fill=base.PALETTE["line_dark"])

    loop_rect = (422, 864, 1498, 1138)
    base.rounded_box(image, loop_rect, fill=base.PALETTE["paper"], outline=base.with_alpha(base.PALETTE["blue"], 80), width=2, radius=28, shadow=True, shadow_alpha=10)
    base.draw_text(draw, (452, 892), "Why This Matters", base.font(26, "headline"), base.PALETTE["blue"])
    bullets = (
        "The transcript is a runtime substrate, not just a log. That is why resume, background work, and inspection remain possible.",
        "Compaction is part of the normal lifecycle. It is what keeps a long session alive when raw history no longer fits.",
        "Task and agent registries share the same continuity boundary, which is why post-turn work can keep progressing after the visible response ends.",
    )
    base.draw_bullet_list(draw, 452, 940, 1000, bullets, base.PALETTE["blue"], "body", 18, 15)
    out_path = OUT_DIR / "session-lifecycle.png"
    image.save(out_path)
    return out_path


def render_extension_ecosystem(metrics: CodebaseMetrics) -> Path:
    size = (1920, 1260)
    image = Image.new("RGBA", size, base.PALETTE["canvas_alt"])
    draw = ImageDraw.Draw(image)
    draw_title(
        draw,
        "Extension Ecosystem",
        "How MCP, plugins, skills, hooks, and remote execution wrap around the core Claude Code runtime.",
    )

    draw_kicker(draw, (66, 152), "Hub and spoke view", "teal")
    base.draw_text(draw, (66, 204), "How the extension surface wraps around the runtime", base.font(30, "headline"), base.PALETTE["ink"])
    base.draw_text(draw, (66, 242), "This codebase behaves like a runtime platform. MCP, hooks, skills, plugins, and remote execution expand the trust boundary around QueryEngine and the tool loop.", base.font(18), base.PALETTE["muted"])

    center = (706, 312, 1214, 804)
    nodes = [
        ((132, 318, 500, 498), "MCP Layer", f"{metrics.mcp_files} files across clients, resources, auth, and transport plumbing.", "teal"),
        ((1420, 318, 1788, 498), "Hook Runtime", f"{metrics.hook_files} hook files plus the shared pre/post tool interception path.", "orange"),
        ((162, 548, 530, 728), "Skill Surfaces", f"{metrics.bundled_skill_registrations} bundled registrations plus repo, plugin, and MCP skill loading.", "purple"),
        ((1390, 548, 1758, 728), "Plugin Layer", f"{metrics.plugin_files} plugin-facing files for loading, caching, and marketplace-style plumbing.", "rose"),
        ((302, 828, 670, 1008), "Remote + Team Execution", "Remote agents, teammates, worktrees, and session bridges extend runtime reach beyond a single local turn.", "green"),
        ((1250, 828, 1618, 1008), "IDE / Browser / Web", "Editor integration, browser-facing skills, and web tools broaden both entry and action surfaces.", "blue"),
    ]

    for rect, _, _, accent_key in nodes:
        draw_link(draw, center, rect, base.PALETTE[accent_key], width=4)

    base.rounded_box(image, center, fill=base.PALETTE["paper"], outline=base.with_alpha(base.PALETTE["blue"], 80), width=2, radius=40, shadow=True, shadow_alpha=14)
    base.draw_text(draw, (776, 346), "Claude Code Runtime", base.font(34, "headline"), base.PALETTE["ink"])
    base.draw_text(draw, (776, 392), "QueryEngine, session state, and permissioned tool orchestration", base.font(19), base.PALETTE["muted"])
    chip_specs = [
        ("Tool dirs", str(metrics.tool_directories), "green"),
        ("Commands", str(metrics.command_surfaces), "orange"),
        ("Flags", str(metrics.feature_flags), "purple"),
        ("Dyn. imports", str(metrics.dynamic_imports), "teal"),
    ]
    chip_rects = [
        (770, 452, 956, 542),
        (968, 452, 1154, 542),
        (770, 558, 956, 648),
        (968, 558, 1154, 648),
    ]
    for rect, (label, value, accent_key) in zip(chip_rects, chip_specs):
        draw_stat_chip(image, rect, label, value, accent_key)
    core_lines = (
        "The runtime sits at the center because extensions do not bypass it.",
        "They widen the trust boundary, capability surface, and operational complexity around the same core session engine.",
    )
    base.draw_bullet_list(draw, 772, 686, 390, core_lines, base.PALETTE["blue"], "body", 17, 15)

    for rect, title, subtitle, accent_key in nodes:
        accent = base.PALETTE[accent_key]
        base.rounded_box(image, rect, fill=accent_fill(accent_key), outline=base.with_alpha(accent, 82), width=2, radius=28, shadow=True, shadow_alpha=8)
        base.draw_text(draw, (rect[0] + 22, rect[1] + 22), title, base.font(22, "headline"), accent)
        font_obj, lines = base.fit_wrapped_font(draw, subtitle, "body", 17, 14, rect[2] - rect[0] - 40, 88, 4, max_lines=4)
        base.draw_text_lines(draw, (rect[0] + 22, rect[1] + 62), lines, font_obj, base.PALETTE["ink"], 4)

    footer_rect = (56, 1094, 1864, 1198)
    base.rounded_box(image, footer_rect, fill=base.PALETTE["paper"], outline=base.PALETTE["line"], width=1, radius=24)
    footer = "Reading: this is not only a CLI. It is a runtime platform with a wide extension surface, where MCP and skills are especially prominent and built-in plugin support looks comparatively early-stage."
    footer_font, footer_lines = base.fit_wrapped_font(draw, footer, "body", 18, 16, 1760, 60, 4, max_lines=3)
    base.draw_text_lines(draw, (86, 1120), footer_lines, footer_font, base.PALETTE["muted"], 4)
    out_path = OUT_DIR / "extension-ecosystem.png"
    image.save(out_path)
    return out_path


def render_query_sequence(metrics: CodebaseMetrics) -> tuple[Path, Path]:
    size = (1600, 1020)
    frames: list[Image.Image] = []

    pipeline = [step.title.split(". ", 1)[1] for step in SEQUENCE_STEPS]

    for index, step in enumerate(SEQUENCE_STEPS):
        accent = base.PALETTE[step.accent_key]
        image = Image.new("RGBA", size, base.PALETTE["canvas_alt"])
        draw = ImageDraw.Draw(image)
        draw_title(
            draw,
            "QueryEngine / Tool Execution Sequence",
            "Focused runtime sequence: how a real turn moves through normalization, QueryEngine, model streaming, tool execution, and persistence.",
        )
        base.draw_badge(
            image,
            (1368, 34, 1546, 72),
            f"Step {index + 1} / {len(SEQUENCE_STEPS)}",
            base.with_alpha(accent, 22),
            accent,
        )

        line_y = 150
        draw.line((72, line_y, 1528, line_y), fill=base.PALETTE["line_dark"], width=4)
        step_w = 214
        gap = 26
        for step_idx, label in enumerate(pipeline):
            x = 72 + step_idx * (step_w + gap)
            rect = (x, 114, x + step_w, 186)
            state = "future"
            if step_idx < index:
                state = "past"
            elif step_idx == index:
                state = "current"
            fill = base.PALETTE["paper"]
            outline = base.PALETTE["line"]
            bubble_fill = base.rgba("#d1d5db")
            label_ink = base.PALETTE["ink"]
            if state == "past":
                fill = base.with_alpha(base.PALETTE["green"], 18)
                outline = base.PALETTE["green"]
                bubble_fill = base.PALETTE["green"]
            elif state == "current":
                fill = base.with_alpha(accent, 20)
                outline = accent
                bubble_fill = accent
            base.rounded_box(image, rect, fill=fill, outline=outline, width=2, radius=18)
            bubble = (x + 12, 132, x + 46, 166)
            base.rounded_box(image, bubble, fill=bubble_fill, radius=17)
            base.draw_text(draw, (x + 23, 138), str(step_idx + 1), base.font(17, "headline"), base.rgba("#ffffff"))
            font_obj, lines = base.fit_wrapped_font(draw, label, "headline", 16, 13, 144, 42, 2, max_lines=2)
            base.draw_text_lines(draw, (x + 58, 128), lines, font_obj, label_ink, 2)

        main_rect = (70, 234, 1014, 706)
        files_rect = (1042, 234, 1530, 460)
        insights_rect = (1042, 484, 1530, 706)
        summary_rect = (70, 740, 1530, 946)
        for rect, title in (
            (main_rect, "Current Internal Boundary"),
            (files_rect, "Key Files"),
            (insights_rect, "Why This Boundary Exists"),
            (summary_rect, "Pipeline Summary"),
        ):
            base.rounded_box(image, rect, fill=base.PALETTE["paper"], outline=base.PALETTE["line"], width=1, radius=28, shadow=True, shadow_alpha=10)
            base.draw_text(draw, (rect[0] + 22, rect[1] + 18), title, base.font(24, "headline"), accent if title != "Pipeline Summary" else base.PALETTE["ink"])

        base.draw_badge(image, (96, 286, 182, 322), step.title.split(".", 1)[0].upper(), accent, base.rgba("#ffffff"))
        title_font, title_lines = base.fit_wrapped_font(draw, step.title, "headline", 34, 24, 874, 76, 4, max_lines=2)
        base.draw_text_lines(draw, (96, 346), title_lines, title_font, base.PALETTE["ink"], 4)
        title_height = base.text_block_height(draw, title_lines, title_font, 4)
        sub_font, sub_lines = base.fit_wrapped_font(draw, step.subtitle, "body", 20, 16, 874, 84, 5, max_lines=4)
        sub_y = 358 + title_height
        base.draw_text_lines(draw, (96, sub_y), sub_lines, sub_font, base.PALETTE["muted"], 5)
        sub_height = base.text_block_height(draw, sub_lines, sub_font, 5)
        base.draw_bullet_list(draw, 96, sub_y + sub_height + 22, 856, step.bullets, accent, "body", 18, 15)

        base.draw_file_pills(image, (1064, 292, 1508, 430), accent, step.files)

        insights = {
            0: (
                "Startup breadth matters because this repo has many non-query command surfaces.",
                "The bootstrap is optimized to avoid paying full runtime cost for every invocation.",
                "Session restore starts here, which is why main.tsx is unusually central.",
            ),
            1: (
                "Normalization is where the runtime decides whether the user asked for a model turn at all.",
                "Message shaping is a major hidden source of product behavior complexity.",
                "Hooks are influential this early, not bolted on after the fact.",
            ),
            2: (
                "QueryEngine is the stateful heart of the product.",
                "This is where memory, tools, prompts, and prior transcript state collapse into one turn package.",
                "Context quality is largely determined here rather than in the model service itself.",
            ),
            3: (
                "Streaming output is not just text; it includes control flow and tool intent.",
                "The model layer is tightly coupled to compaction and recovery behavior.",
                "A large percentage of user-visible runtime feel is determined during streaming.",
            ),
            4: (
                "The tool runtime is security-sensitive and therefore intentionally layered.",
                "Permissions, hooks, and orchestration are central runtime concerns, not isolated add-ons.",
                "Shell families receive the strictest specialized safety treatment.",
            ),
            5: (
                "Persistence is what allows long sessions, resume, background work, and post-turn state continuity.",
                "Compaction is part of the lifecycle, not a niche maintenance command.",
                "The next turn depends on what is written here.",
            ),
        }[index]
        base.draw_bullet_list(draw, 1064, 542, 430, insights, accent, "body", 17, 15)

        summary = "User request -> normalization -> QueryEngine context build -> streamed response/tool_use -> permissioned tool execution -> persisted transcript/task/session state."
        font_obj, lines = base.fit_wrapped_font(draw, summary, "body", 21, 17, 1420, 80, 5, max_lines=3)
        base.draw_text_lines(draw, (96, 804), lines, font_obj, base.PALETTE["ink"], 5)

        frames.append(image)

    still_path = OUT_DIR / "queryengine-tool-sequence.png"
    frames[2].save(still_path)
    gif_path = OUT_DIR / "queryengine-tool-sequence.gif"
    palette_frames = base.quantize_for_gif(frames)
    palette_frames[0].save(
        gif_path,
        save_all=True,
        append_images=palette_frames[1:],
        duration=[1400, 1400, 1500, 1500, 1500, 1800],
        loop=0,
        optimize=False,
        disposal=2,
    )
    return still_path, gif_path


def write_metrics_json(metrics: CodebaseMetrics) -> Path:
    out_path = OUT_DIR / "codebase-metrics.json"
    payload = {
        "summary": {
            "total_files": metrics.total_files,
            "total_loc": metrics.total_loc,
            "feature_flags": metrics.feature_flags,
            "dynamic_imports": metrics.dynamic_imports,
            "command_surfaces": metrics.command_surfaces,
            "tool_directories": metrics.tool_directories,
            "hook_files": metrics.hook_files,
            "mcp_files": metrics.mcp_files,
            "plugin_files": metrics.plugin_files,
            "bundled_skill_registrations": metrics.bundled_skill_registrations,
        },
        "top_dirs": [asdict(item) for item in metrics.top_dirs[:15]],
        "top_files": [asdict(item) for item in metrics.top_files[:25]],
    }
    out_path.write_text(json.dumps(payload, indent=2), encoding="utf-8")
    return out_path


def main() -> None:
    ensure_dirs()
    metrics = compute_metrics()
    outputs = [
        write_metrics_json(metrics),
        render_hotspot_treemap(metrics),
        render_risk_heatmap(metrics),
        render_tool_permission_matrix(),
        render_session_lifecycle(),
        render_extension_ecosystem(metrics),
    ]
    still_path, gif_path = render_query_sequence(metrics)
    outputs.extend([still_path, gif_path])

    print("Generated analysis assets:")
    for output in outputs:
        print(" -", output)


if __name__ == "__main__":
    main()
