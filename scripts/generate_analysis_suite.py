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


def slice_treemap(items: list[DirStat], rect: tuple[int, int, int, int]) -> list[tuple[DirStat, tuple[int, int, int, int]]]:
    if not items:
        return []
    if len(items) == 1:
        return [(items[0], rect)]
    x1, y1, x2, y2 = rect
    width = x2 - x1
    height = y2 - y1
    total = sum(item.loc for item in items)
    horizontal = width >= height
    output: list[tuple[DirStat, tuple[int, int, int, int]]] = []
    cursor = x1 if horizontal else y1
    for index, item in enumerate(items):
        if index == len(items) - 1:
            if horizontal:
                child = (cursor, y1, x2, y2)
            else:
                child = (x1, cursor, x2, y2)
        else:
            ratio = item.loc / total
            if horizontal:
                span = max(110, round(width * ratio))
                child = (cursor, y1, min(x2, cursor + span), y2)
                cursor = child[2]
            else:
                span = max(90, round(height * ratio))
                child = (x1, cursor, x2, min(y2, cursor + span))
                cursor = child[3]
        output.append((item, child))
    return output


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

    treemap_rect = (56, 132, 1448, 1224)
    sidebar_rect = (1476, 132, 1944, 1224)
    base.rounded_box(image, treemap_rect, fill=base.PALETTE["paper"], outline=base.PALETTE["line"], width=1, radius=28, shadow=True, shadow_alpha=12)
    base.rounded_box(image, sidebar_rect, fill=base.PALETTE["paper"], outline=base.PALETTE["line"], width=1, radius=28, shadow=True, shadow_alpha=12)
    base.draw_text(draw, (82, 152), "Treemap By Top-Level Directory", base.font(24, "headline"), base.PALETTE["ink"])
    base.draw_text(draw, (1498, 152), "Largest Files", base.font(24, "headline"), base.PALETTE["ink"])

    accent_cycle = [base.PALETTE[key] for key in ACCENT_KEYS]
    major_dirs = metrics.top_dirs[:10]
    other_loc = sum(stat.loc for stat in metrics.top_dirs[10:])
    other_files = sum(stat.files for stat in metrics.top_dirs[10:])
    other_imports = sum(stat.imports for stat in metrics.top_dirs[10:])
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

    cells = slice_treemap(major_dirs, (80, 196, 1422, 1198))
    for index, (stat, rect) in enumerate(cells):
        accent = accent_cycle[index % len(accent_cycle)]
        fill = base.with_alpha(accent, 18)
        base.rounded_box(image, rect, fill=fill, outline=base.with_alpha(accent, 78), width=2, radius=24)
        x1, y1, x2, y2 = rect
        draw.rounded_rectangle((x1 + 14, y1 + 14, x1 + 20, y2 - 14), radius=3, fill=accent)

        title_font, title_lines = base.fit_wrapped_font(draw, stat.name, "headline", 28, 18, x2 - x1 - 54, 60, 4, max_lines=2)
        base.draw_text_lines(draw, (x1 + 32, y1 + 18), title_lines, title_font, base.PALETTE["ink"], 4)
        title_height = base.text_block_height(draw, title_lines, title_font, 4)

        body_lines = [
            metric_label(stat),
            f"Imports: {stat.imports:,}",
            f"Largest file: {Path(stat.max_file_path).name} ({stat.max_file_loc:,})",
        ]
        current_y = y1 + 28 + title_height
        for line in body_lines:
            available_width = x2 - x1 - 54
            line_text = base.ellipsize_text(draw, line, base.font(16), available_width)
            base.draw_text(draw, (x1 + 32, current_y), line_text, base.font(16), base.PALETTE["muted"])
            current_y += 24

        share_text = f"{pct_text(stat.share)} of src/"
        share_font = base.font(18, "headline")
        share_w, share_h = base.text_size(draw, share_text, share_font)
        if share_w + 30 < (x2 - x1):
            chip = (x2 - share_w - 24, y2 - share_h - 20, x2 - 18, y2 - 18)
            base.rounded_box(image, chip, fill=base.with_alpha(accent, 26), radius=16)
            base.draw_text(draw, (chip[0] + 10, chip[1] + 6), share_text, share_font, accent)

    current_y = 196
    for rank, file_stat in enumerate(metrics.top_files[:12], start=1):
        item_rect = (1498, current_y, 1920, current_y + 68)
        base.rounded_box(image, item_rect, fill=base.PALETTE["slate_fill"], outline=base.PALETTE["line"], width=1, radius=20)
        badge = (1514, current_y + 16, 1546, current_y + 48)
        base.rounded_box(image, badge, fill=base.PALETTE["ink"], radius=16)
        base.draw_text(draw, (1524, current_y + 18), str(rank), base.font(16, "headline"), base.rgba("#ffffff"))
        path_text = base.ellipsize_text(draw, file_stat.path, base.font(15, "mono"), 300, mode="middle")
        base.draw_text(draw, (1564, current_y + 15), path_text, base.font(15, "mono"), base.PALETTE["ink"])
        base.draw_text(draw, (1564, current_y + 39), f"{file_stat.loc:,} LOC · {file_stat.imports} imports", base.font(15), base.PALETTE["muted"])
        current_y += 80

    footer = "Interpretation: utils/, components/, services/, and tools/ dominate the footprint; oversized hotspot files cluster in print, messages, session state, hooks, and REPL/runtime code."
    base.draw_text(draw, (56, 1260), footer, base.font(18), base.PALETTE["muted"])
    out_path = OUT_DIR / "codebase-hotspots-treemap.png"
    image.save(out_path)
    return out_path


def heat_color(value: float, accent: tuple[int, int, int, int]) -> tuple[int, int, int, int]:
    alpha = 12 + int(140 * value)
    return base.with_alpha(accent, alpha)


def render_risk_heatmap(metrics: CodebaseMetrics) -> Path:
    size = (1920, 1260)
    image = Image.new("RGBA", size, base.PALETTE["canvas_alt"])
    draw = ImageDraw.Draw(image)
    draw_title(
        draw,
        "Codebase Risk Heatmap",
        "Composite risk score by major directory. Higher values combine LOC, file count, import fan-out, and largest-file concentration.",
    )
    top_dirs = metrics.top_dirs[:10]
    headers = ["Directory", "LOC", "Files", "Imports", "Largest File", "Risk"]
    widths = [320, 180, 150, 170, 230, 180]
    table_x = 64
    table_y = 154
    row_h = 76
    table_w = sum(widths)

    base.rounded_box(image, (table_x, table_y, table_x + table_w, table_y + 64), fill=base.PALETTE["ink"], radius=22)
    current_x = table_x
    for header, width in zip(headers, widths):
        base.draw_text(draw, (current_x + 18, table_y + 18), header, base.font(19, "headline"), base.rgba("#ffffff"))
        current_x += width

    max_loc = max(stat.loc for stat in top_dirs)
    max_files = max(stat.files for stat in top_dirs)
    max_imports = max(stat.imports for stat in top_dirs)
    max_largest = max(stat.max_file_loc for stat in top_dirs)
    max_risk = max(stat.risk_score for stat in top_dirs)

    current_y = table_y + 82
    for index, stat in enumerate(top_dirs):
        bg = base.PALETTE["paper"] if index % 2 == 0 else base.PALETTE["slate_fill"]
        base.rounded_box(image, (table_x, current_y, table_x + table_w, current_y + row_h), fill=bg, outline=base.PALETTE["line"], width=1, radius=18)
        values = [
            stat.name,
            f"{stat.loc:,}",
            str(stat.files),
            f"{stat.imports:,}",
            f"{stat.max_file_loc:,}",
            f"{stat.risk_score:.1f}",
        ]
        ratios = [
            0.0,
            stat.loc / max_loc,
            stat.files / max_files,
            stat.imports / max_imports,
            stat.max_file_loc / max_largest,
            stat.risk_score / max_risk,
        ]
        cell_x = table_x
        for column_index, (value, width, ratio) in enumerate(zip(values, widths, ratios)):
            if column_index > 0:
                accent = base.PALETTE[ACCENT_KEYS[column_index % len(ACCENT_KEYS)]]
                fill_rect = (cell_x + 8, current_y + 10, cell_x + width - 8, current_y + row_h - 10)
                base.rounded_box(image, fill_rect, fill=heat_color(ratio, accent), radius=14)
            text_font = base.font(18 if column_index == 0 else 17, "headline" if column_index in {0, 5} else "body")
            fill = base.PALETTE["ink"] if column_index in {0, 5} else base.PALETTE["ink"]
            text = value if column_index == 0 else base.ellipsize_text(draw, value, text_font, width - 30)
            base.draw_text(draw, (cell_x + 18, current_y + 20), text, text_font, fill)
            if column_index == 0:
                detail = f"{pct_text(stat.share)} of total LOC"
                base.draw_text(draw, (cell_x + 18, current_y + 44), detail, base.font(15), base.PALETTE["muted"])
            cell_x += width
        current_y += row_h + 10

    notes_rect = (1342, 154, 1862, 1090)
    base.rounded_box(image, notes_rect, fill=base.PALETTE["paper"], outline=base.PALETTE["line"], width=1, radius=26, shadow=True, shadow_alpha=10)
    base.draw_text(draw, (1368, 176), "Engineering Readout", base.font(24, "headline"), base.PALETTE["ink"])
    bullets = (
        "utils/ is the clear gravity well: biggest LOC, biggest file concentration, and the widest internal reuse surface.",
        "components/ is broad rather than singularly dangerous: many files, high LOC, and UI/state coupling.",
        "services/ and tools/ are where runtime policy, tool safety, MCP integration, and orchestration complexity accumulate.",
        "commands/ has breadth risk: many surface areas, each smaller than the runtime hotspots but still product-significant.",
        "root-files includes main.tsx/query.ts style runtime trunks; fewer files, but high centrality.",
    )
    base.draw_bullet_list(draw, 1368, 228, 460, bullets, base.PALETTE["rose"], "body", 17, 15)
    legend_y = 920
    for idx, accent_key in enumerate(ACCENT_KEYS[:5]):
        accent = base.PALETTE[accent_key]
        box = (1368 + idx * 92, legend_y, 1432 + idx * 92, legend_y + 40)
        base.rounded_box(image, box, fill=heat_color((idx + 1) / 5, accent), radius=12)
        label = ["Low", "Guarded", "Moderate", "High", "Critical"][idx]
        base.draw_text(draw, (1378 + idx * 92, legend_y + 10), label, base.font(14, "headline"), base.PALETTE["ink"])

    base.draw_text(draw, (64, 1186), "Method: composite score = normalized LOC + file count + import references + largest-file size. Use it to prioritize review/refactor attention, not as a substitute for runtime tracing.", base.font(18), base.PALETTE["muted"])
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


def matrix_cell_color(value: str) -> tuple[int, int, int, int]:
    if value == "yes":
        return base.with_alpha(base.PALETTE["green"], 34)
    if value == "partial":
        return base.with_alpha(base.PALETTE["orange"], 34)
    return base.with_alpha(base.PALETTE["muted_soft"], 42)


def matrix_cell_label(value: str) -> str:
    return {"yes": "Yes", "partial": "Partial", "no": "No"}[value]


def render_tool_permission_matrix() -> Path:
    size = (1920, 1240)
    image = Image.new("RGBA", size, base.PALETTE["canvas_alt"])
    draw = ImageDraw.Draw(image)
    draw_title(
        draw,
        "Tool Permission Matrix",
        "Shared tool orchestration path plus notable extra controls by tool family.",
    )
    columns = [
        "Validation",
        "Permission Gate",
        "Hook Aware",
        "Policy / Classifier",
        "Concurrency Control",
        "External I/O",
        "Persistent Side Effects",
    ]
    left = 60
    top = 164
    row_h = 92
    first_col = 360
    col_w = 200

    base.rounded_box(image, (left, top, left + first_col + col_w * len(columns), top + 70), fill=base.PALETTE["ink"], radius=24)
    base.draw_text(draw, (left + 18, top + 20), "Tool Family", base.font(20, "headline"), base.rgba("#ffffff"))
    for idx, column in enumerate(columns):
        x = left + first_col + idx * col_w
        font_obj, lines = base.fit_wrapped_font(draw, column, "headline", 18, 14, col_w - 24, 44, 2, max_lines=2)
        base.draw_text_lines(draw, (x + 12, top + 14), lines, font_obj, base.rgba("#ffffff"), 2)

    current_y = top + 86
    for row_name, values in TOOL_MATRIX_ROWS:
        base.rounded_box(image, (left, current_y, left + first_col + col_w * len(columns), current_y + row_h), fill=base.PALETTE["paper"], outline=base.PALETTE["line"], width=1, radius=22)
        base.draw_text(draw, (left + 18, current_y + 18), row_name, base.font(20, "headline"), base.PALETTE["ink"])
        sub = "Common path: toolExecution.ts -> permission -> hooks -> orchestration"
        base.draw_text(draw, (left + 18, current_y + 50), sub, base.font(14), base.PALETTE["muted"])
        for idx, value in enumerate(values):
            x = left + first_col + idx * col_w
            cell = (x + 10, current_y + 12, x + col_w - 10, current_y + row_h - 12)
            base.rounded_box(image, cell, fill=matrix_cell_color(value), outline=base.PALETTE["line"], width=1, radius=18)
            label = matrix_cell_label(value)
            base.draw_text(draw, (cell[0] + 20, cell[1] + 20), label, base.font(18, "headline"), base.PALETTE["ink"])
        current_y += row_h + 10

    notes_rect = (60, 908, 1860, 1150)
    base.rounded_box(image, notes_rect, fill=base.PALETTE["paper"], outline=base.PALETTE["line"], width=1, radius=26, shadow=True, shadow_alpha=10)
    base.draw_text(draw, (84, 930), "Interpretation Notes", base.font(24, "headline"), base.PALETTE["ink"])
    notes = (
        "Bash and PowerShell are the most defensive tool families: they inherit the shared permission path and add dedicated read-only / path safety logic.",
        "MCP tools share the common runtime but extend the trust boundary outside the repo, so external I/O and compatibility risk both rise.",
        "Agent and Skill surfaces are permission-aware because they can spawn more execution, persist state, or change the next-turn context.",
        "All rows are hook-aware because pre/post tool hooks and permission-denied hooks live in the shared orchestration path.",
    )
    base.draw_bullet_list(draw, 84, 978, 1728, notes, base.PALETTE["blue"], "body", 18, 15)
    base.draw_text(draw, (60, 1182), "Key sources: src/services/tools/toolExecution.ts, src/services/tools/toolOrchestration.ts, src/utils/permissions/filesystem.ts, src/tools/BashTool/*, src/tools/PowerShellTool/*.", base.font(18), base.PALETTE["muted"])
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
        ("Prompt Arrives", "User input enters a live or resumed session."),
        ("Transcript Append", "Messages and tool outcomes are written to JSONL state."),
        ("Task / Agent Update", "Background tasks, local agents, and remote agents update registries."),
        ("Pressure Check", "Token budgets and history boundaries determine whether compaction is needed."),
        ("Compact Or Resume", "Older context is summarized, relinked, or resumed from stored memory."),
        ("Next Turn", "The next prompt restarts from persisted state rather than from scratch."),
    ]
    arrows = []
    step_rects: list[tuple[int, int, int, int]] = []
    y = 244
    step_w = 244
    gap = 44
    start_x = 82
    for idx, (title, subtitle) in enumerate(steps):
        x = start_x + idx * (step_w + gap)
        rect = (x, y, x + step_w, y + 180)
        step_rects.append(rect)
        accent = base.PALETTE[ACCENT_KEYS[idx % len(ACCENT_KEYS)]]
        base.rounded_box(image, rect, fill=base.with_alpha(accent, 18), outline=base.with_alpha(accent, 80), width=2, radius=28, shadow=True, shadow_alpha=10)
        badge = (x + 18, y + 18, x + 54, y + 54)
        base.rounded_box(image, badge, fill=accent, radius=18)
        base.draw_text(draw, (x + 30, y + 24), str(idx + 1), base.font(18, "headline"), base.rgba("#ffffff"))
        base.draw_text(draw, (x + 18, y + 70), title, base.font(22, "headline"), base.PALETTE["ink"])
        font_obj, lines = base.fit_wrapped_font(draw, subtitle, "body", 17, 14, step_w - 36, 80, 4, max_lines=4)
        base.draw_text_lines(draw, (x + 18, y + 106), lines, font_obj, base.PALETTE["muted"], 4)
        if idx < len(steps) - 1:
            arrows.append((rect[2] + 6, y + 90, rect[2] + gap - 12, y + 90))

    for x1, y1, x2, y2 in arrows:
        draw.line((x1, y1, x2, y2), fill=base.PALETTE["line_dark"], width=5)
        draw.polygon([(x2, y2), (x2 - 12, y2 - 8), (x2 - 12, y2 + 8)], fill=base.PALETTE["line_dark"])

    store_rects = [
        ((122, 512, 526, 730), "Transcript Store", "JSONL messages, lite metadata, resume titles, and compact boundaries live here.", "purple"),
        ((758, 512, 1162, 730), "Session Memory + Claude.md", "Session memory, re-injected context, and session-start hooks rebuild critical context.", "teal"),
        ((1392, 512, 1796, 730), "Task / Agent Registries", "Local agents, remote agents, notifications, and task state evolve alongside the transcript.", "rose"),
    ]
    for rect, title, subtitle, accent_key in store_rects:
        accent = base.PALETTE[accent_key]
        base.rounded_box(image, rect, fill=base.PALETTE["paper"], outline=base.with_alpha(accent, 72), width=2, radius=26)
        base.draw_text(draw, (rect[0] + 20, rect[1] + 18), title, base.font(22, "headline"), accent)
        font_obj, lines = base.fit_wrapped_font(draw, subtitle, "body", 17, 14, rect[2] - rect[0] - 40, 92, 5, max_lines=5)
        base.draw_text_lines(draw, (rect[0] + 20, rect[1] + 62), lines, font_obj, base.PALETTE["ink"], 5)

    connectors = [
        (step_rects[1][0] + 120, step_rects[1][3], 324, 512),
        (step_rects[3][0] + 122, step_rects[3][3], 960, 512),
        (step_rects[2][0] + 122, step_rects[2][3], 1594, 512),
    ]
    for x1, y1, x2, y2 in connectors:
        draw.line((x1, y1, x2, y2), fill=base.PALETTE["line_dark"], width=4)
        draw.polygon([(x2, y2), (x2 - 10, y2 - 8), (x2 + 10, y2 - 8)], fill=base.PALETTE["line_dark"])

    loop_rect = (668, 802, 1252, 1082)
    base.rounded_box(image, loop_rect, fill=base.PALETTE["paper"], outline=base.with_alpha(base.PALETTE["blue"], 80), width=2, radius=28, shadow=True, shadow_alpha=10)
    base.draw_text(draw, (694, 826), "Why This Matters", base.font(24, "headline"), base.PALETTE["blue"])
    bullets = (
        "Claude Code is not stateless chat. The persisted transcript is a first-class runtime substrate.",
        "Compaction is not optional cleanup; it is part of the mechanism that makes long-running sessions survivable.",
        "Task and agent state live beside transcript state, which is why background work can continue after the visible turn ends.",
    )
    base.draw_bullet_list(draw, 694, 876, 520, bullets, base.PALETTE["blue"], "body", 18, 15)
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

    center = (654, 290, 1266, 846)
    base.rounded_box(image, center, fill=base.PALETTE["paper"], outline=base.with_alpha(base.PALETTE["blue"], 80), width=2, radius=38, shadow=True, shadow_alpha=14)
    base.draw_text(draw, (742, 348), "Claude Code Runtime", base.font(34, "headline"), base.PALETTE["ink"])
    core_lines = [
        f"{metrics.tool_directories} tool directories",
        f"{metrics.command_surfaces} command surfaces",
        f"{metrics.feature_flags} feature flags",
        f"{metrics.dynamic_imports} dynamic imports",
        "QueryEngine + session persistence + permissioned tool orchestration",
    ]
    current_y = 420
    for line in core_lines:
        font_obj, lines = base.fit_wrapped_font(draw, line, "body", 20, 16, 458, 44, 4, max_lines=2)
        base.draw_text_lines(draw, (742, current_y), lines, font_obj, base.PALETTE["muted"] if current_y < 500 else base.PALETTE["ink"], 4)
        current_y += 58

    nodes = [
        ((168, 180, 542, 372), "MCP Layer", f"{metrics.mcp_files} service files for clients, auth, channel permissions, registries, and transports.", "teal"),
        ((1378, 180, 1752, 372), "Hook Runtime", f"{metrics.hook_files} hook files plus shared pre/post tool interception in the common tool path.", "orange"),
        ((120, 488, 520, 680), "Skill Surfaces", f"{metrics.bundled_skill_registrations} bundled skill registrations plus repo/user/plugin/MCP skill loading.", "purple"),
        ((1400, 488, 1800, 680), "Plugin Layer", f"{metrics.plugin_files} plugin-related files, loader/marketplace plumbing, and bundled-plugin scaffolding.", "rose"),
        ((310, 886, 744, 1090), "Remote + Team Execution", "Remote agents, teammates, worktrees, and session bridge flows extend runtime reach past a single local turn.", "green"),
        ((1176, 886, 1610, 1090), "IDE / Browser / Web", "Editor integration, browser-facing skills, and web tools widen the entry and action surfaces.", "blue"),
    ]
    center_points = []
    for rect, title, subtitle, accent_key in nodes:
        accent = base.PALETTE[accent_key]
        base.rounded_box(image, rect, fill=base.with_alpha(accent, 16), outline=base.with_alpha(accent, 78), width=2, radius=28)
        base.draw_text(draw, (rect[0] + 20, rect[1] + 18), title, base.font(24, "headline"), accent)
        font_obj, lines = base.fit_wrapped_font(draw, subtitle, "body", 17, 14, rect[2] - rect[0] - 40, 100, 4, max_lines=5)
        base.draw_text_lines(draw, (rect[0] + 20, rect[1] + 60), lines, font_obj, base.PALETTE["ink"], 4)
        center_points.append(((rect[0] + rect[2]) // 2, (rect[1] + rect[3]) // 2, accent))

    core_center = ((center[0] + center[2]) // 2, (center[1] + center[3]) // 2)
    for x, y, accent in center_points:
        draw.line((core_center[0], core_center[1], x, y), fill=base.with_alpha(accent, 120), width=4)

    footer = "Reading: this codebase is not only a CLI. It is a runtime platform with a wide extension surface, where MCP and skills are especially prominent and built-in plugin support appears comparatively early-stage."
    base.draw_text(draw, (56, 1184), footer, base.font(18), base.PALETTE["muted"])
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
