#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""Build novel PDF from markdown chapters + settings."""
import os
import re
import glob
from reportlab.lib.pagesizes import A4
from reportlab.lib.styles import getSampleStyleSheet, ParagraphStyle
from reportlab.lib.units import cm, mm
from reportlab.lib.enums import TA_CENTER, TA_JUSTIFY, TA_LEFT
from reportlab.platypus import (
    SimpleDocTemplate,
    Paragraph,
    Spacer,
    PageBreak,
    KeepTogether,
    ListFlowable,
    ListItem,
)
from reportlab.pdfbase import pdfmetrics
from reportlab.pdfbase.ttfonts import TTFont

ROOT = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
FONT = os.path.join(ROOT, "fonts", "NotoSansSC.ttf")
OUT = os.path.join(
    ROOT, "novel", "真龙神庭_艾泽拉斯的终焉与序曲_v1.pdf"
)

pdfmetrics.registerFont(TTFont("NotoSC", FONT))


def esc(text: str) -> str:
    text = (
        text.replace("&", "&amp;")
        .replace("<", "&lt;")
        .replace(">", "&gt;")
    )
    return text


def md_inline(text: str) -> str:
    text = esc(text)
    text = re.sub(r"\*\*(.+?)\*\*", r"<b>\1</b>", text)
    text = re.sub(r"`(.+?)`", r"<font face='NotoSC' size='9'>\1</font>", text)
    return text


def build_styles():
    styles = getSampleStyleSheet()
    styles.add(
        ParagraphStyle(
            name="CoverTitle",
            fontName="NotoSC",
            fontSize=22,
            leading=32,
            alignment=TA_CENTER,
            spaceAfter=12,
        )
    )
    styles.add(
        ParagraphStyle(
            name="CoverSub",
            fontName="NotoSC",
            fontSize=11,
            leading=18,
            alignment=TA_CENTER,
            spaceAfter=8,
        )
    )
    styles.add(
        ParagraphStyle(
            name="H1",
            fontName="NotoSC",
            fontSize=16,
            leading=24,
            alignment=TA_CENTER,
            spaceBefore=6,
            spaceAfter=16,
        )
    )
    styles.add(
        ParagraphStyle(
            name="H2",
            fontName="NotoSC",
            fontSize=13,
            leading=20,
            spaceBefore=14,
            spaceAfter=8,
        )
    )
    styles.add(
        ParagraphStyle(
            name="H3",
            fontName="NotoSC",
            fontSize=11,
            leading=16,
            spaceBefore=10,
            spaceAfter=6,
        )
    )
    styles.add(
        ParagraphStyle(
            name="Body",
            fontName="NotoSC",
            fontSize=10.5,
            leading=18,
            alignment=TA_JUSTIFY,
            firstLineIndent=22,
            spaceAfter=6,
        )
    )
    styles.add(
        ParagraphStyle(
            name="BodyNoIndent",
            fontName="NotoSC",
            fontSize=10.5,
            leading=18,
            alignment=TA_LEFT,
            spaceAfter=6,
        )
    )
    styles.add(
        ParagraphStyle(
            name="Meta",
            fontName="NotoSC",
            fontSize=9,
            leading=14,
            textColor="#333333",
            spaceAfter=4,
        )
    )
    styles.add(
        ParagraphStyle(
            name="TOC",
            fontName="NotoSC",
            fontSize=10,
            leading=16,
            spaceAfter=3,
        )
    )
    styles.add(
        ParagraphStyle(
            name="Quote",
            fontName="NotoSC",
            fontSize=10,
            leading=16,
            leftIndent=16,
            textColor="#222222",
            spaceAfter=6,
        )
    )
    return styles


def add_page_number(canvas, doc):
    canvas.saveState()
    canvas.setFont("NotoSC", 8)
    page = canvas.getPageNumber()
    canvas.drawCentredString(A4[0] / 2, 12 * mm, f"— {page} —")
    canvas.drawString(18 * mm, A4[1] - 12 * mm, "真龙神庭：艾泽拉斯的终焉与序曲")
    canvas.restoreState()


def parse_md_to_flowables(text: str, styles, is_chapter=False):
    flows = []
    lines = text.split("\n")
    buf = []

    def flush_para():
        nonlocal buf
        if not buf:
            return
        para = "".join(buf).strip()
        buf = []
        if not para:
            return
        # dialogue / short lines without indent sometimes
        style = styles["Body"]
        if para.startswith(">") or para.startswith("【") or para.startswith("---"):
            style = styles["BodyNoIndent"]
        if para.startswith(">"):
            para = para.lstrip("> ").strip()
            flows.append(Paragraph(md_inline(para), styles["Quote"]))
            return
        flows.append(Paragraph(md_inline(para), style))

    for raw in lines:
        line = raw.rstrip()
        if not line.strip():
            flush_para()
            continue
        if line.startswith("# "):
            flush_para()
            flows.append(Paragraph(md_inline(line[2:].strip()), styles["H1"]))
            continue
        if line.startswith("## "):
            flush_para()
            flows.append(Paragraph(md_inline(line[3:].strip()), styles["H2"]))
            continue
        if line.startswith("### "):
            flush_para()
            flows.append(Paragraph(md_inline(line[4:].strip()), styles["H3"]))
            continue
        if line.strip() == "---":
            flush_para()
            flows.append(Spacer(1, 8))
            continue
        if line.startswith("|") and "---" not in line:
            flush_para()
            # simple table row as text
            cells = [c.strip() for c in line.strip("|").split("|")]
            flows.append(
                Paragraph(md_inline(" · ".join(cells)), styles["BodyNoIndent"])
            )
            continue
        if re.match(r"^\|?\s*-{3,}", line):
            continue
        if line.lstrip().startswith("- "):
            flush_para()
            flows.append(
                Paragraph("• " + md_inline(line.lstrip()[2:]), styles["BodyNoIndent"])
            )
            continue
        # join soft-wrapped PDF-ish lines: if previous didn't end with punctuation, keep joining
        buf.append(line if not buf else line)

    flush_para()
    return flows


def load_chapters():
    files = sorted(glob.glob(os.path.join(ROOT, "novel", "chapters", "*.md")))
    chapters = []
    for path in files:
        text = open(path, encoding="utf-8").read()
        chapters.append((os.path.basename(path), text))
    return chapters


def main():
    styles = build_styles()
    doc = SimpleDocTemplate(
        OUT,
        pagesize=A4,
        leftMargin=2 * cm,
        rightMargin=2 * cm,
        topMargin=1.8 * cm,
        bottomMargin=1.8 * cm,
        title="真龙神庭：艾泽拉斯的终焉与序曲",
        author="Arena Novel Project",
    )
    story = []

    # Cover
    story.append(Spacer(1, 4 * cm))
    story.append(Paragraph("真龙神庭", styles["CoverTitle"]))
    story.append(Paragraph("艾泽拉斯的终焉与序曲", styles["CoverTitle"]))
    story.append(Spacer(1, 0.6 * cm))
    story.append(
        Paragraph(
            "The True Dragon's Divine Court:<br/>The End and Prelude of Azeroth",
            styles["CoverSub"],
        )
    )
    story.append(Spacer(1, 1.2 * cm))
    story.append(Paragraph("长篇史诗 · 第1–30章 + 设定/蓝图/审计", styles["CoverSub"]))
    story.append(Paragraph("版本 v1.0 · 续写与节奏矫正版", styles["CoverSub"]))
    story.append(PageBreak())

    # TOC
    story.append(Paragraph("目录", styles["H1"]))
    story.append(Paragraph("卷一 / 卷二 正文（第1–30章）", styles["H2"]))
    chapters = load_chapters()
    for fn, text in chapters:
        title = text.split("\n", 1)[0].replace("# ", "").strip()
        story.append(Paragraph(md_inline(title), styles["TOC"]))
    story.append(Paragraph("附录", styles["H2"]))
    story.append(Paragraph("核心设定圣经", styles["TOC"]))
    story.append(Paragraph("全章审计报告", styles["TOC"]))
    story.append(Paragraph("500章+长期蓝图", styles["TOC"]))
    story.append(Paragraph("Gemini终局回答订正", styles["TOC"]))
    story.append(PageBreak())

    # Chapters
    for fn, text in chapters:
        # Fix soft line breaks from PDF extraction: merge lines that are mid-sentence
        # For chapter 30 (our writing) paragraphs are already good.
        # For extracted ones, lines are often broken every ~40 chars without punctuation end
        fixed_lines = []
        raw_lines = text.split("\n")
        acc = ""
        for i, ln in enumerate(raw_lines):
            if ln.startswith("#"):
                if acc:
                    fixed_lines.append(acc)
                    acc = ""
                fixed_lines.append(ln)
                continue
            if not ln.strip():
                if acc:
                    fixed_lines.append(acc)
                    acc = ""
                fixed_lines.append("")
                continue
            if ln.strip() == "---" or ln.startswith("【") or ln.startswith(">"):
                if acc:
                    fixed_lines.append(acc)
                    acc = ""
                fixed_lines.append(ln)
                continue
            # merge continuation
            if not acc:
                acc = ln.strip()
            else:
                # if acc ends with sentence end, start new
                if acc[-1] in "。！？…—」』》\"'：:；;":
                    fixed_lines.append(acc)
                    acc = ln.strip()
                else:
                    acc += ln.strip()
        if acc:
            fixed_lines.append(acc)
        fixed = "\n".join(fixed_lines)
        story.extend(parse_md_to_flowables(fixed, styles, is_chapter=True))
        story.append(PageBreak())

    # Appendices
    appendices = [
        (
            "附录A · 核心设定圣经",
            os.path.join(ROOT, "novel", "settings", "00_CORE_BIBLE.md"),
        ),
        (
            "附录B · 全章审计报告",
            os.path.join(ROOT, "novel", "audit", "CHAPTER_AUDIT_v1.md"),
        ),
        (
            "附录C · 500章+长期蓝图",
            os.path.join(ROOT, "novel", "blueprint", "LONG_ARC_500.md"),
        ),
        (
            "附录D · Gemini终局回答订正",
            os.path.join(ROOT, "novel", "audit", "GEMINI_FINAL_CORRECTIONS.md"),
        ),
    ]
    for title, path in appendices:
        if not os.path.exists(path):
            continue
        story.append(Paragraph(title, styles["H1"]))
        body = open(path, encoding="utf-8").read()
        story.extend(parse_md_to_flowables(body, styles))
        story.append(PageBreak())

    doc.build(story, onFirstPage=add_page_number, onLaterPages=add_page_number)
    print("PDF written:", OUT, "size", os.path.getsize(OUT))


if __name__ == "__main__":
    main()
