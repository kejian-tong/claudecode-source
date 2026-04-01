#!/usr/bin/env python3

from __future__ import annotations

import argparse
import re
from pathlib import Path
from typing import List, Tuple
from xml.sax.saxutils import escape

from reportlab.lib.colors import HexColor
from reportlab.lib.pagesizes import A4
from reportlab.lib.styles import ParagraphStyle, StyleSheet1, getSampleStyleSheet
from reportlab.lib.units import mm
from reportlab.pdfbase import pdfmetrics
from reportlab.pdfbase.cidfonts import UnicodeCIDFont
from reportlab.platypus import PageBreak, Paragraph, SimpleDocTemplate, Spacer


Block = Tuple[str, str]


def parse_markdown(text: str) -> List[Block]:
    blocks: List[Block] = []
    paragraph_lines: List[str] = []
    in_code = False
    code_lines: List[str] = []

    def flush_paragraph() -> None:
        nonlocal paragraph_lines
        if paragraph_lines:
            joined = " ".join(line.strip() for line in paragraph_lines if line.strip())
            if joined:
                blocks.append(("p", joined))
            paragraph_lines = []

    for raw_line in text.splitlines():
        line = raw_line.rstrip("\n")
        stripped = line.strip()

        if stripped.startswith("```"):
            if in_code:
                blocks.append(("code", "\n".join(code_lines)))
                code_lines = []
                in_code = False
            else:
                flush_paragraph()
                in_code = True
            continue

        if in_code:
            code_lines.append(line)
            continue

        if stripped in {"<!-- PAGEBREAK -->", "<!--PAGEBREAK-->", "\f"}:
            flush_paragraph()
            blocks.append(("pagebreak", ""))
            continue

        if not stripped:
            flush_paragraph()
            continue

        heading = re.match(r"^(#{1,3})\s+(.*)$", stripped)
        if heading:
            flush_paragraph()
            level = len(heading.group(1))
            blocks.append((f"h{level}", heading.group(2).strip()))
            continue

        bullet = re.match(r"^[-*]\s+(.*)$", stripped)
        if bullet:
            flush_paragraph()
            blocks.append(("bullet", bullet.group(1).strip()))
            continue

        numbered = re.match(r"^(\d+)\.\s+(.*)$", stripped)
        if numbered:
            flush_paragraph()
            blocks.append(("number", f"{numbered.group(1)}. {numbered.group(2).strip()}"))
            continue

        paragraph_lines.append(stripped)

    flush_paragraph()
    if in_code and code_lines:
        blocks.append(("code", "\n".join(code_lines)))
    return blocks


def build_styles(base_font: str, code_font: str, cjk_wrap: str) -> StyleSheet1:
    styles = getSampleStyleSheet()
    styles.add(
        ParagraphStyle(
            name="ReportTitle",
            parent=styles["Title"],
            fontName=base_font,
            fontSize=22,
            leading=28,
            textColor=HexColor("#111827"),
            spaceAfter=10,
        )
    )
    styles.add(
        ParagraphStyle(
            name="ReportMeta",
            parent=styles["Normal"],
            fontName=base_font,
            fontSize=10.5,
            leading=14,
            textColor=HexColor("#4B5563"),
            spaceAfter=6,
            wordWrap=cjk_wrap,
        )
    )
    styles.add(
        ParagraphStyle(
            name="Body",
            parent=styles["Normal"],
            fontName=base_font,
            fontSize=11,
            leading=16,
            spaceAfter=6,
            wordWrap=cjk_wrap,
            textColor=HexColor("#111827"),
        )
    )
    styles.add(
        ParagraphStyle(
            name="H1",
            parent=styles["Heading1"],
            fontName=base_font,
            fontSize=16,
            leading=22,
            spaceBefore=12,
            spaceAfter=6,
            textColor=HexColor("#111827"),
            wordWrap=cjk_wrap,
        )
    )
    styles.add(
        ParagraphStyle(
            name="H2",
            parent=styles["Heading2"],
            fontName=base_font,
            fontSize=13.5,
            leading=18,
            spaceBefore=10,
            spaceAfter=5,
            textColor=HexColor("#111827"),
            wordWrap=cjk_wrap,
        )
    )
    styles.add(
        ParagraphStyle(
            name="H3",
            parent=styles["Heading3"],
            fontName=base_font,
            fontSize=12,
            leading=16,
            spaceBefore=8,
            spaceAfter=4,
            textColor=HexColor("#111827"),
            wordWrap=cjk_wrap,
        )
    )
    styles.add(
        ParagraphStyle(
            name="ReportBullet",
            parent=styles["Normal"],
            fontName=base_font,
            fontSize=11,
            leading=16,
            leftIndent=12,
            firstLineIndent=-9,
            spaceAfter=4,
            wordWrap=cjk_wrap,
            textColor=HexColor("#111827"),
        )
    )
    styles.add(
        ParagraphStyle(
            name="BodyCode",
            parent=styles["Code"],
            fontName=code_font,
            fontSize=9,
            leading=12,
            leftIndent=10,
            rightIndent=10,
            spaceBefore=2,
            spaceAfter=6,
            backColor=HexColor("#F3F4F6"),
            borderPadding=6,
            wordWrap="LTR",
        )
    )
    return styles


def render_blocks(blocks: List[Block], styles: StyleSheet1):
    story = []
    for kind, content in blocks:
        escaped = escape(content).replace("\t", "    ")
        if kind == "h1":
            story.append(Paragraph(escaped, styles["H1"]))
        elif kind == "h2":
            story.append(Paragraph(escaped, styles["H2"]))
        elif kind == "h3":
            story.append(Paragraph(escaped, styles["H3"]))
        elif kind == "bullet":
            story.append(Paragraph(f"- {escaped}", styles["ReportBullet"]))
        elif kind == "number":
            story.append(Paragraph(escaped, styles["ReportBullet"]))
        elif kind == "code":
            for code_line in escaped.splitlines() or [""]:
                story.append(Paragraph(code_line or " ", styles["BodyCode"]))
        elif kind == "pagebreak":
            story.append(PageBreak())
        else:
            story.append(Paragraph(escaped, styles["Body"]))
        if kind not in {"pagebreak"}:
            story.append(Spacer(1, 1.5 * mm))
    return story


def add_footer(canvas, doc) -> None:
    canvas.saveState()
    canvas.setFont("Helvetica", 9)
    canvas.setFillColor(HexColor("#6B7280"))
    canvas.drawRightString(A4[0] - 18 * mm, 10 * mm, str(canvas.getPageNumber()))
    canvas.restoreState()


def main() -> None:
    parser = argparse.ArgumentParser(description="Render simple Markdown to PDF.")
    parser.add_argument("input", type=Path)
    parser.add_argument("output", type=Path)
    parser.add_argument("--lang", choices=["zh", "en"], default="en")
    args = parser.parse_args()

    input_text = args.input.read_text(encoding="utf-8")

    if args.lang == "zh":
        pdfmetrics.registerFont(UnicodeCIDFont("STSong-Light"))
        base_font = "STSong-Light"
        code_font = "Courier"
        wrap_mode = "CJK"
    else:
        base_font = "Helvetica"
        code_font = "Courier"
        wrap_mode = "LTR"

    styles = build_styles(base_font, code_font, wrap_mode)
    blocks = parse_markdown(input_text)

    if not blocks:
        raise SystemExit("Input markdown is empty.")

    title_block = blocks[0]
    remaining_blocks = blocks[1:] if title_block[0] == "h1" else blocks

    args.output.parent.mkdir(parents=True, exist_ok=True)
    doc = SimpleDocTemplate(
        str(args.output),
        pagesize=A4,
        leftMargin=18 * mm,
        rightMargin=18 * mm,
        topMargin=18 * mm,
        bottomMargin=16 * mm,
        title=title_block[1] if title_block[0] == "h1" else args.input.stem,
    )

    story = []
    if title_block[0] == "h1":
        story.append(Paragraph(escape(title_block[1]), styles["ReportTitle"]))
        story.append(Spacer(1, 2 * mm))
        story.append(Paragraph(escape(f"Source: {args.input.name}"), styles["ReportMeta"]))
        story.append(Spacer(1, 2 * mm))

    story.extend(render_blocks(remaining_blocks, styles))
    doc.build(story, onFirstPage=add_footer, onLaterPages=add_footer)


if __name__ == "__main__":
    main()
