"""把 AI 產出的課程內容做成 Word 教案、PowerPoint 簡報（含講稿）與課程網站 HTML。"""
from __future__ import annotations

import html
import io

from docx import Document
from docx.enum.table import WD_TABLE_ALIGNMENT
from docx.enum.text import WD_ALIGN_PARAGRAPH
from docx.oxml.ns import qn
from docx.shared import Cm, Pt, RGBColor
from pptx import Presentation
from pptx.dml.color import RGBColor as PRGB
from pptx.enum.shapes import MSO_SHAPE
from pptx.enum.text import MSO_ANCHOR, PP_ALIGN
from pptx.util import Emu, Inches
from pptx.util import Pt as PPt

FONT = "Noto Sans TC"
BLACK = RGBColor(0, 0, 0)
SCHOOL = "新北市立永平高級中學"
VIDEO_ID = "Z1K2ERjquD0"  # 2023 去馬來西亞國際交流 永平高中循人中學


def file_stem(lesson: dict) -> str:
    return lesson["title"].replace("/", "／")[:40]


# ---------------------------------------------------------------- Word 教案

def _font(run, size=None, bold=False):
    run.font.name = FONT
    run.font.color.rgb = BLACK
    run.bold = bold
    if size:
        run.font.size = Pt(size)
    rpr = run._element.get_or_add_rPr()
    rfonts = rpr.find(qn("w:rFonts"))
    if rfonts is None:
        rfonts = rpr.makeelement(qn("w:rFonts"), {})
        rpr.append(rfonts)
    rfonts.set(qn("w:eastAsia"), FONT)


def _para(doc_or_cell, text="", size=11, bold=False, align=None, space_after=4):
    p = doc_or_cell.add_paragraph()
    if text:
        _font(p.add_run(text), size, bold)
    p.paragraph_format.space_after = Pt(space_after)
    if align:
        p.alignment = align
    return p


def _cell(cell, text, bold=False, shade=False, size=10.5):
    cell.text = ""
    lines = text if isinstance(text, list) else [text]
    for i, line in enumerate(lines):
        p = cell.paragraphs[0] if i == 0 else cell.add_paragraph()
        p.paragraph_format.space_after = Pt(2)
        _font(p.add_run(line), size, bold)
    if shade:
        tcpr = cell._element.get_or_add_tcPr()
        sh = tcpr.makeelement(qn("w:shd"), {qn("w:val"): "clear", qn("w:color"): "auto", qn("w:fill"): "F3E9D6"})
        tcpr.append(sh)


def _table(doc, rows, widths, header=True):
    t = doc.add_table(rows=len(rows), cols=len(widths))
    t.style = "Table Grid"
    t.alignment = WD_TABLE_ALIGNMENT.CENTER
    _widths(t, widths)
    for r, row in enumerate(rows):
        for c, val in enumerate(row):
            _cell(t.cell(r, c), val, bold=header and r == 0, shade=header and r == 0)
            t.cell(r, c).width = Cm(widths[c])
    doc.add_paragraph()
    return t


def _kv_table(doc, pairs):
    t = doc.add_table(rows=len(pairs), cols=2)
    t.style = "Table Grid"
    _widths(t, [3.6, 13.4])
    for r, (k, v) in enumerate(pairs):
        _cell(t.cell(r, 0), k, bold=True, shade=True)
        _cell(t.cell(r, 1), v)
        t.cell(r, 0).width, t.cell(r, 1).width = Cm(3.6), Cm(13.4)
    doc.add_paragraph()


def _widths(t, widths):
    """Word 與 Google 文件看 tblGrid 的欄寬，只設儲存格寬度不夠。"""
    t.autofit = False
    for c, w in enumerate(widths):
        t.columns[c].width = Cm(w)


def _h(doc, text):
    _para(doc, text, 13, True, space_after=6)


def build_docx(lesson: dict, form: dict) -> bytes:
    doc = Document()
    sec = doc.sections[0]
    sec.page_width, sec.page_height = Cm(21), Cm(29.7)
    sec.left_margin = sec.right_margin = Cm(2)
    sec.top_margin = sec.bottom_margin = Cm(1.8)
    style = doc.styles["Normal"]
    style.font.name = FONT
    style.element.rPr.rFonts.set(qn("w:eastAsia"), FONT)

    _para(doc, f"{SCHOOL} 國際教育課程教案", 16, True, WD_ALIGN_PARAGRAPH.CENTER)
    _para(doc, lesson["title"], 15, True, WD_ALIGN_PARAGRAPH.CENTER)
    if lesson["subtitle"]:
        _para(doc, lesson["subtitle"], 11, align=WD_ALIGN_PARAGRAPH.CENTER, space_after=10)

    _kv_table(doc, [
        ("課程名稱", lesson["title"]),
        ("教學年段", f"{form['level']}（{lesson['grade']}）"),
        ("教學時間", form["time"] if lesson["total_time"] in form["time"] else f"{form['time']}（{lesson['total_time']}）"),
        ("融入領域／科目", lesson["domains"]),
        ("進行方式", lesson["approach"]),
        ("融入議題", "、".join(i["name"] for i in lesson["issues"]) or "—"),
        ("課程目標", form["goal"]),
        ("期望成效", form["outcome"]),
    ])

    _h(doc, "一、設計理念")
    _para(doc, lesson["design_rationale"])

    _h(doc, "二、國際教育議題實質內涵、學習目標與總結性評量")
    rows = [["國際教育議題實質內涵", "學習目標", "總結性評量"]]
    summ = f"【{lesson['summative']['name']}】\n{lesson['summative']['description']}"
    for o in lesson["objectives"]:
        rows.append([f"{o['code']} {o['text']}", [f"{g['code']} {g['text']}" for g in o["goals"]], ""])
    t = _table(doc, rows, [4.5, 8, 4.5])
    if len(rows) > 1:
        merged = t.cell(1, 2).merge(t.cell(len(rows) - 1, 2))
        _cell(merged, summ.split("\n"))

    if lesson["issues"]:
        _h(doc, "三、議題融入")
        _table(doc, [["議題", "融入方式"]] + [[i["name"], i["integration"]] for i in lesson["issues"]], [3.5, 13.5])

    _h(doc, "四、關鍵概念與探究問題")
    _para(doc, "關鍵概念：" + "、".join(lesson["key_concepts"]))
    q = lesson["inquiry"]
    _table(doc, [["問題類型", "探究問題"],
                 ["事實性問題", q["factual"]], ["概念性問題", q["conceptual"]], ["辯論性問題", q["debatable"]]],
           [3.5, 13.5])

    _h(doc, "五、教學活動與評量")
    rows = [["教學活動", "內容簡述", "時間", "目標", "評量方式"]]
    for a in lesson["activities"]:
        rows.append([a["name"], [f"{i}. {s}" for i, s in enumerate(a["steps"], 1)], a["time"],
                     a["goal_codes"], a["formative"]])
    _table(doc, rows, [2.8, 8.4, 1.6, 1.8, 2.4])

    _h(doc, f"六、總結性評量規準：【{lesson['summative']['name']}】")
    _table(doc, [["向度", "優秀", "良好", "待加強"]] +
           [[r["dimension"], r["excellent"], r["good"], r["developing"]] for r in lesson["summative"]["rubric"]],
           [2.6, 4.8, 4.8, 4.8])

    _h(doc, "七、預期成效")
    for i, s in enumerate(lesson["expected_outcomes"], 1):
        _para(doc, f"{i}. {s}")

    _h(doc, "八、教學資源與參考資料")
    for s in lesson["materials"]:
        _para(doc, f"・{s}")
    for r in lesson["toolkit_refs"]:
        _para(doc, f"・{r['title']}：{r['url']}（{r['how_used']}）")
    for link in form["links"]:
        _para(doc, f"・{link}")

    buf = io.BytesIO()
    doc.save(buf)
    return buf.getvalue()


# ---------------------------------------------------------------- 簡報

PARCH = PRGB(0xF7, 0xF1, 0xE3)
MAPLE = PRGB(0xB2, 0x3A, 0x2B)
AMBER = PRGB(0xC8, 0x89, 0x2B)
PBLACK = PRGB(0, 0, 0)
WHITE = PRGB(0xFF, 0xFF, 0xFF)


def _ptext(tf, text, size, bold=False, color=PBLACK, align=PP_ALIGN.LEFT, first=True):
    p = tf.paragraphs[0] if first else tf.add_paragraph()
    p.alignment = align
    r = p.add_run()
    r.text = text
    f = r.font
    f.size, f.bold, f.name = PPt(size), bold, FONT
    f.color.rgb = color
    rpr = r._r.get_or_add_rPr()
    rpr.append(rpr.makeelement(qn("a:ea"), {"typeface": FONT}))  # 中文字型
    return p


def _rect(slide, x, y, w, h, color, shape=MSO_SHAPE.RECTANGLE):
    s = slide.shapes.add_shape(shape, x, y, w, h)
    s.fill.solid()
    s.fill.fore_color.rgb = color
    s.line.fill.background()
    s.shadow.inherit = False
    return s


def _box(slide, x, y, w, h):
    tf = slide.shapes.add_textbox(x, y, w, h).text_frame
    tf.word_wrap = True
    tf.margin_left = tf.margin_right = Inches(0.1)
    return tf


def _fit(texts, base, width_in, max_lines):
    """字越多字越小，但不低於 24pt（使用者要求字要大）。"""
    longest = max((len(t) for t in texts), default=1)
    size = base
    while size > 24 and (longest * size / 72 > width_in * 0.95 * 2 or len(texts) * size > max_lines * base):
        size -= 2
    return size


def build_pptx(lesson: dict, form: dict) -> bytes:
    prs = Presentation()
    prs.slide_width, prs.slide_height = Inches(13.333), Inches(7.5)
    blank = prs.slide_layouts[6]
    W, H = prs.slide_width, prs.slide_height
    total = len(lesson["slides"])

    for i, s in enumerate(lesson["slides"]):
        slide = prs.slides.add_slide(blank)
        bg = slide.background.fill
        bg.solid()
        bg.fore_color.rgb = PARCH
        if i == 0:
            _rect(slide, 0, 0, W, Inches(0.35), MAPLE)
            _rect(slide, 0, H - Inches(0.35), W, Inches(0.35), AMBER)
            chip = _rect(slide, Inches(0.9), Inches(1.0), Inches(4.2), Inches(0.7), MAPLE, MSO_SHAPE.ROUNDED_RECTANGLE)
            ctf = chip.text_frame
            ctf.vertical_anchor = MSO_ANCHOR.MIDDLE
            _ptext(ctf, "永平高中・國際教育", 24, True, WHITE, PP_ALIGN.CENTER)
            tf = _box(slide, Inches(0.9), Inches(2.1), Inches(11.5), Inches(2.6))
            tf.vertical_anchor = MSO_ANCHOR.MIDDLE
            _ptext(tf, s["title"], _fit([s["title"]], 60, 11.5, 2), True)
            sub = s["bullets"][0] if s["bullets"] else lesson["subtitle"]
            tf = _box(slide, Inches(0.9), Inches(4.8), Inches(11.5), Inches(1.0))
            _ptext(tf, sub, 30)
            tf = _box(slide, Inches(0.9), Inches(6.0), Inches(11.5), Inches(0.7))
            _ptext(tf, f"{SCHOOL}｜{form['level']}｜{form['time']}", 22)
        else:
            _rect(slide, 0, 0, Inches(0.3), H, MAPLE)
            _rect(slide, Inches(0.8), Inches(1.55), Inches(2.2), Emu(54000), AMBER)
            tf = _box(slide, Inches(0.75), Inches(0.35), Inches(11.8), Inches(1.15))
            tf.vertical_anchor = MSO_ANCHOR.MIDDLE
            _ptext(tf, s["title"], _fit([s["title"]], 44, 11.8, 1), True)
            bullets = s["bullets"][:5]
            if bullets:
                size = _fit(bullets, 34, 11.4, 4)
                tf = _box(slide, Inches(0.8), Inches(1.9), Inches(11.6), Inches(5.0))
                for j, b in enumerate(bullets):
                    p = _ptext(tf, "● " + b, size, first=j == 0)
                    p.space_after = PPt(size * 0.6)
            tf = _box(slide, W - Inches(1.5), H - Inches(0.65), Inches(1.2), Inches(0.5))
            _ptext(tf, f"{i + 1}/{total}", 16, align=PP_ALIGN.RIGHT)
        slide.notes_slide.notes_text_frame.text = s["notes"]

    buf = io.BytesIO()
    prs.save(buf)
    return buf.getvalue()


# ---------------------------------------------------------------- 課程網站

def _e(s):
    return html.escape(str(s))


def _li(items):
    return "".join(f"<li>{_e(x)}</li>" for x in items)


def build_site(lesson: dict, form: dict) -> str:
    """{{SLIDES_ID}}、{{DOC_URL}}、{{SLIDES_URL}}、{{FOLDER_URL}} 由 Apps Script 建好檔案後代入。"""
    site = lesson["site"]
    text = " ".join([form["goal"], form["note"], lesson["title"], lesson["design_rationale"]])
    show_video = any(k in text for k in ("馬來西亞", "循人", "循中", "服務學習", "志工", "老婦院"))
    goals = "".join(
        f"<div class='card'><b>{_e(o['code'])} {_e(o['text'])}</b><ul>"
        + _li(f"{g['code']} {g['text']}" for g in o["goals"]) + "</ul></div>" for o in lesson["objectives"])
    acts = "".join(
        f"<div class='card'><div class='tag'>{_e(a['time'])}</div><h3>{_e(a['name'])}</h3>"
        f"<ol>{_li(a['steps'])}</ol><p><b>怎麼看出學會了？</b>{_e(a['formative'])}</p></div>"
        for a in lesson["activities"])
    rubric = "".join(
        f"<tr><th>{_e(r['dimension'])}</th><td>{_e(r['excellent'])}</td><td>{_e(r['good'])}</td>"
        f"<td>{_e(r['developing'])}</td></tr>" for r in lesson["summative"]["rubric"])
    faq = "".join(f"<details><summary>{_e(f['q'])}</summary><p>{_e(f['a'])}</p></details>" for f in site["faq"])
    refs = "".join(f"<li><a href='{_e(r['url'])}' target='_blank'>{_e(r['title'])}</a>：{_e(r['how_used'])}</li>"
                   for r in lesson["toolkit_refs"])
    refs += "".join(f"<li><a href='{_e(u)}' target='_blank'>{_e(u)}</a></li>" for u in form["links"])
    q = lesson["inquiry"]
    video = (f"<section><h2>永平 × 循人：我們的交流</h2><div class='video'>"
             f"<iframe src='https://www.youtube.com/embed/{VIDEO_ID}' allowfullscreen></iframe></div></section>"
             if show_video else "")
    return f"""<!doctype html><html lang="zh-Hant"><head><meta charset="utf-8">
<meta name="viewport" content="width=device-width,initial-scale=1"><title>{_e(lesson['title'])}</title>
<link href="https://fonts.googleapis.com/css2?family=Noto+Sans+TC:wght@400;700&family=Noto+Serif+TC:wght@700;900&display=swap" rel="stylesheet">
<style>
*{{box-sizing:border-box}} body{{margin:0;background:#F7F1E3;color:#000;font:17px/1.75 'Noto Sans TC',sans-serif}}
header{{background:linear-gradient(135deg,#FBF6EA,#F3E6CC);border-bottom:6px solid #B23A2B;padding:40px 16px 30px}}
.wrap{{max-width:980px;margin:0 auto;padding:0 16px}} h1,h2,h3{{font-family:'Noto Serif TC',serif;color:#000}}
h1{{font-size:clamp(28px,5vw,44px);margin:.2em 0}} h2{{border-left:8px solid #B23A2B;padding-left:12px;margin-top:2em}}
.chip{{display:inline-block;background:#B23A2B;color:#fff;border-radius:999px;padding:4px 14px;font-weight:700}}
.btns a{{display:inline-block;margin:8px 8px 0 0;background:#B23A2B;color:#fff;text-decoration:none;padding:10px 18px;border-radius:10px;font-weight:700}}
.card{{background:#FFFBF2;border:1px solid #8C6A4F55;border-radius:12px;padding:14px 18px;margin:12px 0}}
.tag{{float:right;background:#C8892B;color:#000;border-radius:8px;padding:0 10px;font-weight:700}}
.slides,.video{{position:relative;padding-top:56.25%;border-radius:12px;overflow:hidden;background:#000}}
.slides iframe,.video iframe{{position:absolute;inset:0;width:100%;height:100%;border:0}}
table{{width:100%;border-collapse:collapse;background:#fff}} th,td{{border:1px solid #9C8775;padding:8px;vertical-align:top}}
.scroll{{overflow-x:auto}} details{{background:#FFFBF2;border-radius:10px;padding:10px 14px;margin:8px 0}}
summary{{font-weight:700;cursor:pointer}} a{{color:#000}} footer{{padding:30px 16px;text-align:center}}
</style></head><body>
<header><div class="wrap"><span class="chip">永平高中・國際教育</span><h1>{_e(lesson['title'])}</h1>
<p style="font-size:1.2em">{_e(site['tagline'])}</p>
<p>{_e(form['level'])}｜{_e(form['time'])}｜{_e(lesson['domains'])}</p>
<div class="btns"><a href="{{{{SLIDES_URL}}}}" target="_blank">開啟簡報</a><a href="{{{{DOC_URL}}}}" target="_blank">開啟教案</a><a href="{{{{FOLDER_URL}}}}" target="_blank">課程資料夾</a></div>
</div></header><main class="wrap">
<section><h2>這堂課在幹嘛？</h2><p>{_e(site['intro'])}</p></section>
<section><h2>本課簡報</h2><div class="slides"><iframe src="https://docs.google.com/presentation/d/{{{{SLIDES_ID}}}}/embed?start=false&loop=false" allowfullscreen></iframe></div></section>
<section><h2>你的任務</h2><div class="card"><b>【{_e(lesson['summative']['name'])}】</b><p>{_e(site['student_mission'])}</p></div></section>
<section><h2>學習目標</h2>{goals}</section>
<section><h2>想一想</h2><div class="card"><b>事實性</b><ul>{_li(q['factual'])}</ul><b>概念性</b><ul>{_li(q['conceptual'])}</ul><b>辯論性</b><ul>{_li(q['debatable'])}</ul></div></section>
<section><h2>課程活動</h2>{acts}</section>
<section><h2>評量規準</h2><div class="scroll"><table><tr><th>向度</th><th>優秀</th><th>良好</th><th>待加強</th></tr>{rubric}</table></div></section>
{video}
<section><h2>給家長的話</h2><div class="card">{_e(site['family_note'])}</div></section>
<section><h2>常見問題</h2>{faq}</section>
<section><h2>參考資源</h2><ul>{refs}<li><a href="https://www.ietw2.edu.tw/" target="_blank">教育部中小學國際教育資訊網</a></li></ul></section>
</main><footer>{SCHOOL}・國際教育課程</footer></body></html>"""
