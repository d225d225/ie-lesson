"""永平高中・國際教育課程教案投影片產生器（秋楓樣式）。

執行：streamlit run app.py
"""
from __future__ import annotations

import datetime as dt
import os

import streamlit as st
import streamlit.components.v1 as components

from core import ai, builders, data, style
from core.drive import Drive, DriveError, guess_mime, to_blocks

st.set_page_config(page_title="國際教育課程產生器", layout="wide", initial_sidebar_state="collapsed")
st.markdown(style.CSS, unsafe_allow_html=True)

REFERENCE_PATH = "04-reference/"
MAX_LEARNED_CHARS = 30000


# ---------------------------------------------------------------- 設定

def secret(key: str) -> str:
    try:
        v = st.secrets.get(key, "")
    except Exception:  # 沒有 secrets.toml 時
        v = ""
    return str(v or os.environ.get(key, "")).strip().strip("　")


API_KEY = secret("GEMINI_API_KEY")
MODELS = [m for m in [secret("GEMINI_MODEL")] if m] + ai.MODELS
GAS_URL = secret("GAS_WEBHOOK_URL")
drive = Drive(GAS_URL, secret("GAS_SECRET")) if GAS_URL else None
ss = st.session_state

EXAMPLE = {
    "time": "3 節（150 分鐘）",
    "goal": "讓學生在出發到馬來西亞前，認識循人中學與馬來西亞多元文化，學會與長者互動的方法，"
            "和學伴一起規劃銀禧老婦院的關懷服務與淨灘行動。",
    "outcome": "學生能用合宜的禮儀和學伴、長者互動；能分組設計一套長者健康操或互動小遊戲；"
               "服務後能以海報反思「當婆婆一天的孫子」「飲水思源」，並提出一項回臺後到長照或日照中心延續服務的行動方案。",
    "issues": ["SDGs", "服務學習", "品德教育", "生命教育", "多元文化教育", "海洋教育"],
    "objectives": ["國U2", "國U5", "國U9", "國U11"],
    "note": "這是永平高中與吉隆坡循人中學的國際志工服務學習交流（兩校學伴事先配對）。"
            "在馬來西亞會去銀禧老婦院服務、巴生淨灘；在臺灣會去長照中心或日照中心服務老人，也去過聖愛教養院服務老憨兒、"
            "脊髓損傷重建中心參訪。課程要讓學生在行前做好準備，並在交流後反思與行動。",
    "links": "https://www.youtube.com/watch?v=Z1K2ERjquD0",
}


def tidy(text: str) -> str:
    """去掉多按的空白行（避免教案表格出現一大片空白）。"""
    lines = [x.rstrip() for x in text.strip().splitlines()]
    return "\n".join(x for x in lines if x)


def learned_text(knowledge: dict) -> str:
    """老師修改後上傳的檔案排前面，其餘學校資料在後。"""
    items = sorted(knowledge.get("files", {}).values(),
                   key=lambda f: (not f.get("path", "").startswith(REFERENCE_PATH), f.get("name", "")))
    out, size = [], 0
    for f in items:
        if not f.get("lessons"):
            continue
        block = f"《{f['path']}{f['name']}》{f['summary']}\n" + "\n".join("- " + x for x in f["lessons"])
        if size + len(block) > MAX_LEARNED_CHARS:
            break
        out.append(block)
        size += len(block)
    return "\n\n".join(out)


# ---------------------------------------------------------------- 頁首

st.markdown(style.hero("國際教育課程教案投影片產生器",
                       "填寫課程需求 → AI 查閱教育部國際教育課程工具包 → 一次產出教案、上課簡報（含講稿）與課程網站",
                       "新北市立永平高級中學"), unsafe_allow_html=True)
if not API_KEY:
    st.error("尚未設定 AI 金鑰，請管理者在 secrets 設定 GEMINI_API_KEY（Google AI Studio 免費申請）。")
if not drive:
    st.warning("尚未連線雲端硬碟（GAS_WEBHOOK_URL），仍可產生並下載檔案，但不會建立 Google 文件／簡報／課程網站。")

tab_make, tab_upload, tab_learn = st.tabs(["✦ 產生課程", "⇪ 上傳修改後的檔案", "🤖 讓 AI 閱讀資料"])

# ---------------------------------------------------------------- 產生課程

with tab_make:
    c1, c2 = st.columns([3, 1])
    c1.markdown("#### 課程需求")
    if c2.button("填入馬來西亞交流範例", width="stretch"):
        ss.update(level="高中", time=EXAMPLE["time"], goal=EXAMPLE["goal"], outcome=EXAMPLE["outcome"],
                  issues=EXAMPLE["issues"], note=EXAMPLE["note"], links=EXAMPLE["links"])
        for code in data.ALL:
            ss[f"obj_{code}"] = code in EXAMPLE["objectives"]
        st.rerun()

    level = st.radio("（1）教學年段", list(data.LEVELS), horizontal=True, key="level")
    time = st.text_input("（2）教學時間", key="time", placeholder="例：2 節（100 分鐘）、3 週共 6 節")
    goal = st.text_area("（3）課程目標", key="goal", height=100)
    outcome = st.text_area("（4）期望達到的課程成效", key="outcome", height=100)
    issues = st.pills("（5）要融合的議題（可複選）", data.ISSUES, selection_mode="multi", key="issues")

    st.markdown("**（6）國際教育目標**（「彰顯國家價值」為必選面向，至少勾一項）")
    stages = data.LEVELS[level]
    chosen = []
    cols = st.columns(2)
    for i, (face, by_stage) in enumerate(data.OBJECTIVES.items()):
        with cols[i % 2].container(border=True):
            st.markdown(f"**{face}**")
            for stage in stages:
                for code, text, n in by_stage[stage]:
                    if st.checkbox(f"{code} {text}", key=f"obj_{code}"):
                        chosen.append(code)

    note = st.text_area("（7）課程補充說明", key="note", height=110,
                        placeholder="例：交流對象、服務機構、學生背景、想要的活動形式…")
    files = st.file_uploader("（8）上傳參考教材（PDF、Word、PPT、圖片）", accept_multiple_files=True,
                             type=["pdf", "docx", "pptx", "png", "jpg", "jpeg", "txt", "md"])
    links = st.text_area("（9）相關連結（一行一個）", key="links", height=80)

    missing = [n for n, v in [("教學時間", time), ("課程目標", goal), ("期望成效", outcome)] if not v.strip()]
    if not chosen:
        missing.append("國際教育目標")
    if chosen and not any(data.ALL[c][0] == data.NATIONAL_VALUE for c in chosen):
        st.info("提醒：教育部實作手冊規定至少要選一項「彰顯國家價值」的實質內涵。")
    if missing:
        st.caption("還需要填寫：" + "、".join(missing))

    if st.button("✦ AI 產生教案、簡報與課程網站", type="primary", width="stretch",
                 disabled=bool(missing) or not API_KEY):
        form = {
            "level": level, "time": time.strip(), "goal": tidy(goal), "outcome": tidy(outcome),
            "issues": issues or [], "note": tidy(note),
            "links": [x.strip() for x in links.splitlines() if x.strip()],
            "objectives": [(c, data.ALL[c][0], data.ALL[c][1], data.ALL[c][2]) for c in chosen],
        }
        with st.status("AI 正在查閱教育部國際教育網站與課程工具包，並撰寫課程（約 2～5 分鐘；免費版人多時會稍等）…", expanded=True) as status:
            try:
                knowledge = drive.knowledge() if drive else {}
                attachments = []
                for f in files or []:
                    blocks = to_blocks(f.name, guess_mime(f.name, f.type), f.getvalue())
                    if not blocks:
                        st.write(f"⚠ 無法讀取「{f.name}」，已略過")
                    attachments += blocks

                def show(name, inp):
                    if name == "web_fetch":
                        st.write(f"🔎 閱讀 {inp.get('url', '')}")
                    elif name == "web_search":
                        st.write(f"🔎 搜尋「{inp.get('query', '')}」")
                    elif name == "lesson":
                        st.write("✍ 網站讀完了，開始撰寫教案…")
                    elif name == "repair":
                        st.write("🔧 檢查指標對應，補齊遺漏：" + "；".join(inp["problems"][:4]) + "…")
                    elif name == "deck":
                        st.write("✍ 教案完成，接著寫簡報講稿與課程網站…")

                lesson = ai.generate(API_KEY, form, attachments, learned_text(knowledge), on_event=show, models=MODELS)
                status.update(label="撰寫完成，正在製作檔案…")
                docx = builders.build_docx(lesson, form)
                pptx = builders.build_pptx(lesson, form)
                site = builders.build_site(lesson, form)
                result = {"lesson": lesson, "form": form, "docx": docx, "pptx": pptx, "site": site, "links": None}
                if drive:
                    status.update(label="存到雲端硬碟，轉成 Google 文件、Google 簡報與課程網站…")
                    stem = builders.file_stem(lesson)
                    folder = f"{dt.datetime.now():%Y%m%d-%H%M} {stem}"
                    result["links"] = drive.publish(folder, stem, docx, pptx, site)
                ss.result = result
                status.update(label="完成！", state="complete", expanded=False)
            except (ai.AIError, DriveError) as e:
                status.update(label="發生錯誤", state="error")
                st.error(str(e))

    r = ss.get("result")
    if r:
        lesson = r["lesson"]
        stem = builders.file_stem(lesson)
        st.divider()
        st.markdown(f"### {lesson['title']}")
        st.write(lesson["subtitle"])
        if lesson.get("alignment_issues"):
            st.warning("指標對應檢核：" + "；".join(lesson["alignment_issues"]) + "。請在 Google 文件中補充修改。")
        elif "alignment_issues" in lesson:
            st.success("指標對應檢核通過：每個勾選的指標都有學習目標，且都對應到教學活動、總結性評量與評量規準。")
        if r["links"]:
            b = st.columns(4)
            b[0].link_button("開啟 Google 文件（教案）", r["links"]["docUrl"], width="stretch")
            b[1].link_button("開啟 Google 簡報（含講稿）", r["links"]["slidesUrl"], width="stretch")
            b[2].link_button("開啟課程網站", r["links"]["siteUrl"], width="stretch")
            b[3].link_button("開啟課程資料夾", r["links"]["folderUrl"], width="stretch")
        d = st.columns(3)
        d[0].download_button("下載 Word 教案", r["docx"], f"{stem}－教案.docx", width="stretch")
        d[1].download_button("下載 PPT 簡報", r["pptx"], f"{stem}－簡報.pptx", width="stretch")
        d[2].download_button("下載課程網站 HTML", r["site"].encode("utf-8"), f"{stem}－課程網站.html",
                             mime="text/html", width="stretch")

        p_slides, p_plan, p_site = st.tabs(["簡報與講稿", "教案重點", "課程網站預覽"])
        with p_slides:
            for i, s in enumerate(lesson["slides"], 1):
                with st.container(border=True):
                    st.markdown(f"**{i}. {s['title']}**")
                    for b in s["bullets"]:
                        st.markdown(f"- {b}")
                    st.caption("講稿：" + s["notes"])
        with p_plan:
            st.markdown("**設計理念**")
            st.write(lesson["design_rationale"])
            st.markdown("**學習目標**")
            for o in lesson["objectives"]:
                st.markdown(f"- **{o['code']} {o['text']}**")
                for g in o["goals"]:
                    st.markdown(f"    - {g['code']} {g['text']}")
            st.markdown(f"**總結性評量：【{lesson['summative']['name']}】** {lesson['summative']['description']}")
            st.markdown("**指標對應檢核表**")
            header, rows = builders.alignment_matrix(lesson)
            st.table([dict(zip(header, row)) for row in rows])
            st.markdown("**教學活動**")
            for a in lesson["activities"]:
                st.markdown(f"- **{a['name']}**（{a['time']}）：" + "；".join(a["steps"]))
            if lesson["toolkit_refs"]:
                st.markdown("**參考的教育部課程工具包／資源**")
                for t in lesson["toolkit_refs"]:
                    st.markdown(f"- [{t['title']}]({t['url']})：{t['how_used']}")
        with p_site:
            components.html(r["site"], height=900, scrolling=True)

# ---------------------------------------------------------------- 上傳修改後的檔案

with tab_upload:
    st.markdown("老師修改 AI 產生的教案或簡報後，請下載成 Word／PowerPoint／PDF 再上傳，"
                "檔案會存到雲端「04-reference」資料夾。之後按「讓 AI 閱讀資料」，AI 就會學起來，下次產生得更好。")
    up = st.file_uploader("選擇修改後的檔案", accept_multiple_files=True, key="revised",
                          type=["pdf", "docx", "pptx", "png", "jpg", "jpeg", "txt", "md"])
    if st.button("⇪ 上傳到雲端", type="primary", disabled=not up or not drive):
        for f in up:
            try:
                drive.upload(f.name, guess_mime(f.name, f.type), f.getvalue())
                st.success(f"已上傳：{f.name}")
            except DriveError as e:
                st.error(f"{f.name}：{e}")

# ---------------------------------------------------------------- AI 閱讀資料

with tab_learn:
    st.markdown("AI 會逐一閱讀國際教育雲端資料夾裡的檔案（01-國際教育、02-計畫、03-成果報告、04-reference 老師修改檔），"
                "整理成「AI學習筆記」，之後每次產生課程都會參考。已讀過且沒修改的檔案不會重讀。")
    if st.button("🤖 讓 AI 閱讀資料", type="primary", disabled=not drive or not API_KEY):
        try:
            knowledge = drive.knowledge()
            known = knowledge.setdefault("files", {})
            todo = [f for f in drive.sources() if known.get(f["id"], {}).get("modified") != f["modified"]]
            if not todo:
                st.success("沒有新的資料，AI 已經讀過全部檔案了。")
            bar = st.progress(0.0)
            for i, f in enumerate(todo, 1):
                bar.progress((i - 1) / len(todo), text=f"閱讀中（{i}/{len(todo)}）：{f['path']}{f['name']}")
                entry = {"name": f["name"], "path": f["path"], "modified": f["modified"], "summary": "", "lessons": []}
                try:
                    name, mime, raw = drive.get_file(f["id"])
                    blocks = to_blocks(name, mime, raw)
                    if blocks:
                        entry.update(ai.learn(API_KEY, f["path"] + name, blocks, models=MODELS))
                    else:
                        entry["summary"] = "（格式無法閱讀或檔案過大，已略過）"
                except (ai.AIError, DriveError) as e:
                    st.warning(f"{f['name']}：{e}")
                    continue
                known[f["id"]] = entry
                knowledge["updated"] = dt.datetime.now().isoformat(timespec="seconds")
                drive.save_knowledge(knowledge)  # 每讀完一個就存，中斷也不會白讀
            bar.progress(1.0, text="閱讀完成")
            ss.knowledge = knowledge
        except DriveError as e:
            st.error(str(e))

    if drive and st.button("查看 AI 學習筆記"):
        try:
            ss.knowledge = drive.knowledge()
        except DriveError as e:
            st.error(str(e))
    k = ss.get("knowledge")
    if k:
        st.caption(f"共 {len(k.get('files', {}))} 個檔案，最後更新 {k.get('updated', '—')}")
        for f in sorted(k.get("files", {}).values(), key=lambda f: f["path"] + f["name"]):
            with st.expander(f"{f['path']}{f['name']}"):
                st.write(f["summary"])
                for x in f["lessons"]:
                    st.markdown(f"- {x}")
