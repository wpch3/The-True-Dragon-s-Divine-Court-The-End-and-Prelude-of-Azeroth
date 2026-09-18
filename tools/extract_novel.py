#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""Extract and normalize novel from Gemini PDF export."""
from pypdf import PdfReader
import re
import os
import json
import unicodedata

ROOT = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
PDF = os.path.join(ROOT, "魔兽世界小说大纲设定.pdf")

# CJK Radicals Supplement chars that do NOT NFKC to standard CJK
# Map simplified radical forms -> simplified Chinese
SUPPLEMENT = {
    "\u2e81": "厂",
    "\u2e84": "尸",
    "\u2e88": "刀",
    "\u2e8c": "小",
    "\u2e8f": "川",
    "\u2e94": "工",
    "\u2e95": "己",
    "\u2ea0": "民",  # CJK RADICAL CIVILIAN
    "\u2ec5": "见",  # CJK RADICAL C-SIMPLIFIED SEE
    "\u2ec6": "角",
    "\u2ecd": "贝",
    "\u2ed2": "车",
    "\u2ed3": "长",  # CJK RADICAL C-SIMPLIFIED LONG
    "\u2ed4": "门",
    "\u2ed8": "青",  # CJK RADICAL BLUE
    "\u2ed9": "页",
    "\u2eda": "风",
    "\u2edb": "风",  # CJK RADICAL C-SIMPLIFIED WIND
    "\u2edc": "飞",
    "\u2ee2": "马",
    "\u2ee3": "骨",
    "\u2ee8": "麦",
    "\u2ee9": "黄",
    "\u2ef0": "龙",  # CJK RADICAL C-SIMPLIFIED DRAGON
    "\u2ef1": "龟",
    "\u2ef2": "龟",
    "\u2ef3": "龙",
}

# Traditional -> simplified preference after NFKC
TRAD_TO_SIMP = str.maketrans(
    {
        "見": "见",
        "貝": "贝",
        "車": "车",
        "長": "长",
        "門": "门",
        "韋": "韦",
        "頁": "页",
        "風": "风",
        "飛": "飞",
        "馬": "马",
        "魚": "鱼",
        "鳥": "鸟",
        "鹵": "卤",
        "麥": "麦",
        "黃": "黄",
        "黽": "黾",
        "齊": "齐",
        "齒": "齿",
        "龍": "龙",
        "龜": "龟",
        "靑": "青",
        "戶": "户",
        "衆": "众",
        "與": "与",
        "爲": "为",
        "於": "于",
        "後": "后",
        "從": "从",
        "無": "无",
        "當": "当",
        "對": "对",
        "開": "开",
        "關": "关",
        "這": "这",
        "還": "还",
        "來": "来",
        "時": "时",
        "會": "会",
        "個": "个",
        "們": "们",
        "說": "说",
        "過": "过",
        "發": "发",
        "經": "经",
        "現": "现",
        "麼": "么",
        "種": "种",
        "動": "动",
        "國": "国",
        "為": "为",
        "體": "体",
        "點": "点",
        "戰": "战",
        "東": "东",
        "兩": "两",
        "並": "并",
        "萬": "万",
        "義": "义",
        "氣": "气",
        "術": "术",
        "術": "术",
    }
)


def normalize_char(ch: str) -> str:
    if ch in SUPPLEMENT:
        return SUPPLEMENT[ch]
    o = ord(ch)
    # Kangxi radicals & compatibility ideographs
    if 0x2F00 <= o <= 0x2FDF or 0xF900 <= o <= 0xFAFF or 0x2E80 <= o <= 0x2EFF:
        nfkc = unicodedata.normalize("NFKC", ch)
        if nfkc and nfkc != ch:
            ch = nfkc
        elif ch in SUPPLEMENT:
            ch = SUPPLEMENT[ch]
    return ch.translate(TRAD_TO_SIMP) if len(ch) == 1 else ch


def normalize(s: str) -> str:
    out = []
    for ch in s:
        if ch in SUPPLEMENT:
            out.append(SUPPLEMENT[ch])
            continue
        o = ord(ch)
        if 0x2F00 <= o <= 0x2FDF or 0xF900 <= o <= 0xFAFF:
            nfkc = unicodedata.normalize("NFKC", ch)
            ch = nfkc if nfkc else ch
        elif 0x2E80 <= o <= 0x2EFF:
            nfkc = unicodedata.normalize("NFKC", ch)
            if nfkc and nfkc != ch and ord(nfkc[0]) > 0x2EFF:
                ch = nfkc
            elif ch in SUPPLEMENT:
                ch = SUPPLEMENT[ch]
            # else leave and try later map
        out.append(ch)
    text = "".join(out)
    text = text.translate(TRAD_TO_SIMP)
    # leftover supplement
    for k, v in SUPPLEMENT.items():
        text = text.replace(k, v)
    return text


def cn_num_to_int(s: str) -> int:
    s = s.strip()
    if s.isdigit():
        return int(s)
    digit = {
        "零": 0,
        "〇": 0,
        "一": 1,
        "二": 2,
        "两": 2,
        "三": 3,
        "四": 4,
        "五": 5,
        "六": 6,
        "七": 7,
        "八": 8,
        "九": 9,
    }
    if s == "十":
        return 10
    if s.startswith("十"):
        return 10 + digit.get(s[1], 0)
    if "十" in s:
        parts = s.split("十")
        tens = digit.get(parts[0], 1)
        ones = digit.get(parts[1], 0) if parts[1] else 0
        return tens * 10 + ones
    if "百" in s:
        parts = s.split("百")
        hundreds = digit.get(parts[0], 1)
        rest = parts[1] if len(parts) > 1 else ""
        return hundreds * 100 + (cn_num_to_int(rest) if rest else 0)
    if len(s) == 1 and s in digit:
        return digit[s]
    return -1


def is_real_title(t: str) -> bool:
    t = t.strip()
    if not re.match(r"^第[一二三四五六七八九十百零〇两0-9]{1,5}章[：:]", t):
        return False
    bad = [
        "吗",
        "不需要",
        "重写为",
        "结束于",
        "里，",
        "中，",
        "之前",
        "之后的",
        "下半",
        "刚刚",
        "直接开启",
        "开启部落",
        "我们",
        "你希望",
        "开始吧",
        "写了",
        "描写",
        "请求",
        "那句",
        "看看",
        "顺着",
        "完美填",
        "继续",
        "lite",
        "没写好",
    ]
    if any(b in t for b in bad):
        return False
    if len(t) > 45:
        return False
    after = re.split(r"[：:]", t, 1)[-1].strip()
    if len(after) < 4:
        return False
    return True


def clean_body(body: str) -> str:
    body = re.sub(r"2026/9/18[^\n]*\n?", "", body)
    body = re.sub(r"https://gemini\.google\.com/[^\n]*\n?", "", body)
    body = re.sub(r"\n?\d{1,3}/\d{1,3}\s*\n", "\n", body)
    body = re.sub(r"\n{3,}", "\n\n", body)
    return body.strip()


# Known correct titles (from conversation) for filename polish
CANON_TITLES = {
    1: "第一章：王权之影与时间线上的迷子",
    2: "第二章：达拉然的井底之蛙，与深夜盛放的黑龙玫瑰",
    3: "第三章：阴影法庭的初建，与血色玫瑰的效忠",
    4: "第四章：永歌森林的挽歌，与铸光圣精灵的降生",
    5: "第五章：银月城的低语，与太阳井的易主",
    6: "第六章：神明居所的浮生一日",
    7: "第七章：王位上的清风，与暗流涌动的洛丹伦",
    8: "第八章：荒野的清道夫，与桌面上不见血的屠杀",
    9: "第九章：海风中的金发千金，与无尽之海的波澜",
    10: "第十章：深渊的哀鸣，与无尽之海的真龙王座",
    11: "第十一章：一万年的回声，与深渊海妖的恸哭",
    12: "第十二章：紫罗兰的傲慢，与凡星之上的裁决",
    13: "第十三章：坠落的紫罗兰，与星轨编织者",
    14: "第十四章：劈开万年的迷雾，与煞魔的绝对湮灭",
    15: "第十五章：巴尼尔的冬雪，与“无敌”的新生",
    16: "第十六章：暴风城的暗流，与死亡之翼的盛宴",
    17: "第十七章：大地的悲鸣，与灭世者的赎罪",
    18: "第十八章：神庭的午后，与巨龙女仆的修罗场",
    19: "第十九章：灰谷的绝境，与深渊领主的覆灭",
    20: "第二十章：月神殿的黄昏，与暗夜星辰的臣服",
    21: "第二十一章：虚伪的神祇，与翡翠梦魇的降维清洗",
    22: "第二十二章：世界之树下的晚宴，与真龙王座的修罗场",
    23: "第二十三章：黄沙下的杀戮盛宴，与全职业的降维顶点",
    24: "第二十四章：被踩碎的凝视，与降维神工的奇迹",
    25: "第二十五章：金币的黄昏，与星际财团的绝对收购",
    26: "第二十六章：洛丹伦的炉火，与矮人王的热啤酒",
    27: "第二十七章：云端的盛宴，与神庭女眷的修罗场",
    28: "第二十八章：生命的啼鸣，与红龙女王的震撼",
    29: "第二十九章：红龙女王的PTSD，与维度的彻底倾覆",
}


def main():
    reader = PdfReader(PDF)
    full = "\n".join((p.extract_text() or "") for p in reader.pages)
    full_n = normalize(full)

    weird = {ch for ch in full_n if 0x2E80 <= ord(ch) <= 0x2FDF}
    print(f"Remaining radical chars: {len(weird)} {list(weird)[:10]}")

    for d in ["chapters", "settings", "blueprint", "audit"]:
        os.makedirs(os.path.join(ROOT, "novel", d), exist_ok=True)

    # wipe old chapter files
    chdir = os.path.join(ROOT, "novel", "chapters")
    for fn in os.listdir(chdir):
        os.remove(os.path.join(chdir, fn))

    with open(os.path.join(ROOT, "novel", "SOURCE_FULL.txt"), "w", encoding="utf-8") as f:
        f.write(full_n)

    candidates = []
    for m in re.finditer(
        r"(第[一二三四五六七八九十百零〇两0-9]{1,5}章[：:]\s*[^\n]{2,50})", full_n
    ):
        title = m.group(1).strip()
        if is_real_title(title):
            candidates.append((m.start(), title))

    deduped = []
    for pos, title in candidates:
        mnum = re.match(r"第([一二三四五六七八九十百零〇两0-9]{1,5})章", title)
        num = cn_num_to_int(mnum.group(1)) if mnum else -1
        if deduped:
            prev_m = re.match(
                r"第([一二三四五六七八九十百零〇两0-9]{1,5})章", deduped[-1][1]
            )
            prev_num = cn_num_to_int(prev_m.group(1)) if prev_m else -2
            if num == prev_num and num > 0:
                deduped[-1] = (pos, title)
                continue
        if deduped and deduped[-1][1] == title:
            continue
        deduped.append((pos, title))

    chapters = []
    for i, (pos, title) in enumerate(deduped):
        end = deduped[i + 1][0] if i + 1 < len(deduped) else len(full_n)
        body = full_n[pos:end]
        up = re.search(r"\nUser prompt:", body)
        if up:
            body = body[: up.start()]
        body = clean_body(body)
        mnum = re.match(r"第([一二三四五六七八九十百零〇两0-9]{1,5})章", title)
        num = cn_num_to_int(mnum.group(1)) if mnum else i + 1
        # polish title from canon
        if num in CANON_TITLES:
            title = CANON_TITLES[num]
            # replace first line of body
            lines = body.split("\n")
            if lines and lines[0].startswith("第"):
                lines[0] = title
                body = "\n".join(lines)
        chapters.append({"num": num, "title": title, "text": body, "chars": len(body)})

    by_num = {}
    for c in chapters:
        n = c["num"]
        if n not in by_num or c["chars"] >= by_num[n]["chars"]:
            by_num[n] = c
    final = [by_num[k] for k in sorted(by_num.keys())]

    index = []
    for c in final:
        safe = re.sub(r'[\\/:*?"<>|\s]+', "_", c["title"])[:80]
        fname = f"{c['num']:02d}_{safe}.md"
        path = os.path.join(chdir, fname)
        lines = c["text"].split("\n")
        out_lines = []
        started = False
        for ln in lines:
            if not started and ln.strip().startswith("第") and "章" in ln:
                started = True
                out_lines.append(f"# {c['title']}")
                out_lines.append("")
                continue
            out_lines.append(ln)
        with open(path, "w", encoding="utf-8") as f:
            f.write("\n".join(out_lines).strip() + "\n")
        index.append(
            {
                "num": c["num"],
                "title": c["title"],
                "file": f"chapters/{fname}",
                "chars": len(c["text"]),
            }
        )
        print(f"Ch{c['num']:02d}: {c['title']} ({c['chars']} chars) -> {fname}")

    with open(
        os.path.join(ROOT, "novel", "chapters_index.json"), "w", encoding="utf-8"
    ) as f:
        json.dump(index, f, ensure_ascii=False, indent=2)

    print(f"\nDONE: {len(final)} chapters")
    # sanity titles
    for c in final[:5]:
        print(" ", c["title"])


if __name__ == "__main__":
    main()
