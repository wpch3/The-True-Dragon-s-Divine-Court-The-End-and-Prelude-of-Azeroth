#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""Build Gemini handoff PDF into novel/ and repo root."""
from reportlab.lib.pagesizes import A4
from reportlab.lib.styles import ParagraphStyle
from reportlab.lib.units import cm, mm
from reportlab.platypus import SimpleDocTemplate, Paragraph, Spacer, PageBreak
from reportlab.pdfbase import pdfmetrics
from reportlab.pdfbase.ttfonts import TTFont
from reportlab.lib.enums import TA_LEFT, TA_CENTER, TA_JUSTIFY
import os
import re
import glob
import shutil

ROOT = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
FONT = os.path.join(ROOT, "fonts", "NotoSansSC.ttf")
if not os.path.exists(FONT):
    FONT = os.path.join(ROOT, "fonts", "NotoSansSC-Regular.ttf")
pdfmetrics.registerFont(TTFont("NotoSC", FONT))

OUT = os.path.join(ROOT, "novel", "真龙神庭_交接_Gemini.pdf")
OUT2 = os.path.join(ROOT, "真龙神庭_交接_Gemini.pdf")


def style_map():
    return {
        "title": ParagraphStyle(
            "t",
            fontName="NotoSC",
            fontSize=16,
            leading=24,
            alignment=TA_CENTER,
            spaceAfter=12,
        ),
        "h1": ParagraphStyle(
            "h1", fontName="NotoSC", fontSize=13, leading=20, spaceBefore=12, spaceAfter=8
        ),
        "h2": ParagraphStyle(
            "h2", fontName="NotoSC", fontSize=11, leading=16, spaceBefore=8, spaceAfter=6
        ),
        "body": ParagraphStyle(
            "b",
            fontName="NotoSC",
            fontSize=9.5,
            leading=15,
            alignment=TA_JUSTIFY,
            firstLineIndent=18,
            spaceAfter=4,
        ),
        "meta": ParagraphStyle(
            "m", fontName="NotoSC", fontSize=9, leading=14, spaceAfter=3
        ),
        "center": ParagraphStyle(
            "c",
            fontName="NotoSC",
            fontSize=10,
            leading=15,
            alignment=TA_CENTER,
            spaceAfter=6,
        ),
    }


def esc(s: str) -> str:
    return s.replace("&", "&amp;").replace("<", "&lt;").replace(">", "&gt;")


def md_to_flow(text: str, styles):
    flows = []
    for raw in text.split("\n"):
        line = raw.rstrip()
        if not line.strip():
            flows.append(Spacer(1, 4))
            continue
        if line.startswith("# "):
            flows.append(Paragraph(esc(line[2:]), styles["h1"]))
            continue
        if line.startswith("## "):
            flows.append(Paragraph(esc(line[3:]), styles["h2"]))
            continue
        if line.startswith("### "):
            flows.append(Paragraph(esc(line[4:]), styles["h2"]))
            continue
        if line.startswith("---"):
            flows.append(Spacer(1, 6))
            continue
        if line.startswith("|") or line.startswith("- ") or line.startswith(">"):
            flows.append(
                Paragraph(esc(line.lstrip("> ").lstrip("- ")), styles["meta"])
            )
            continue
        flows.append(Paragraph(esc(line), styles["body"]))
    return flows


def footer(canvas, doc):
    canvas.saveState()
    canvas.setFont("NotoSC", 8)
    canvas.drawCentredString(A4[0] / 2, 12 * mm, f"— {canvas.getPageNumber()} — 交接包")
    canvas.drawString(15 * mm, A4[1] - 12 * mm, "真龙神庭 · Gemini Handoff")
    canvas.restoreState()


def main():
    styles = style_map()
    story = []
    story.append(Spacer(1, 2 * cm))
    story.append(Paragraph("真龙神庭：艾泽拉斯的终焉与序曲", styles["title"]))
    story.append(Paragraph("Gemini 交接包 / Handoff", styles["title"]))
    story.append(
        Paragraph("正典进度：第1–38章 · 分支 arena/01a0b501-…", styles["center"])
    )
    story.append(
        Paragraph(
            "The True Dragon's Divine Court: The End and Prelude of Azeroth",
            styles["center"],
        )
    )
    story.append(PageBreak())

    story.append(Paragraph("一、交接总览", styles["h1"]))
    story.extend(
        md_to_flow(
            open(os.path.join(ROOT, "novel/HANDOFF_GEMINI.md"), encoding="utf-8").read(),
            styles,
        )
    )
    story.append(PageBreak())

    story.append(Paragraph("二、用户拍板与文风铁律", styles["h1"]))
    for rel in [
        "memory/01_CORE/USER_DECREES.md",
        "memory/13_STYLE_RULES/PROSE_CN.md",
        "memory/13_STYLE_RULES/PROTAGONIST_VOICE.md",
    ]:
        path = os.path.join(ROOT, rel)
        story.append(Paragraph(rel, styles["h2"]))
        story.extend(md_to_flow(open(path, encoding="utf-8").read(), styles))
    story.append(PageBreak())

    story.append(Paragraph("三、近期正文（第34–38章全文）", styles["h1"]))
    for p in sorted(
        glob.glob(os.path.join(ROOT, "novel/chapters/_canon_current/3[4-8]_*.md"))
    ):
        text = open(p, encoding="utf-8").read()
        story.append(PageBreak())
        for block in text.split("\n\n"):
            block = block.strip()
            if not block:
                continue
            if block.startswith("# "):
                story.append(Paragraph(esc(block[2:]), styles["h1"]))
            else:
                joined = "".join(
                    ln.strip() for ln in block.split("\n") if ln.strip()
                )
                # keep Chinese without extra spaces
                story.append(Paragraph(esc(joined), styles["body"]))

    story.append(PageBreak())
    story.append(Paragraph("四、第30–33章标题（v2正典，全文见仓库）", styles["h1"]))
    for p in sorted(
        glob.glob(os.path.join(ROOT, "novel/chapters/_canon_current/3[0-3]_*.md"))
    ):
        title = open(p, encoding="utf-8").read().split("\n", 1)[0].replace("# ", "")
        story.append(Paragraph(esc(title), styles["meta"]))

    story.append(PageBreak())
    story.append(Paragraph("五、当前卷钩子", styles["h1"]))
    story.extend(
        md_to_flow(
            open(
                os.path.join(ROOT, "memory/11_PLOT_ARCS/CURRENT_VOLUME.md"),
                encoding="utf-8",
            ).read(),
            styles,
        )
    )

    doc = SimpleDocTemplate(
        OUT,
        pagesize=A4,
        leftMargin=1.8 * cm,
        rightMargin=1.8 * cm,
        topMargin=1.6 * cm,
        bottomMargin=1.6 * cm,
        title="真龙神庭 Gemini交接",
        author="Arena",
    )
    doc.build(story, onFirstPage=footer, onLaterPages=footer)
    shutil.copy(OUT, OUT2)
    print("PDF written:", OUT, os.path.getsize(OUT))


if __name__ == "__main__":
    main()
