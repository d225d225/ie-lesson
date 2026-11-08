"""Google Gemini（免費版）：先查教育部國際教育網站與課程工具包，再撰寫教案、簡報講稿與課程網站內容。"""
from __future__ import annotations

import json
import re
import time
from pathlib import Path

from google import genai
from opencc import OpenCC
from google.genai import errors, types

# 免費額度用完或模型不存在時依序改用下一個；可用 secrets 的 GEMINI_MODEL 指定第一順位
MODELS = ["gemini-3.5-flash", "gemini-flash-latest", "gemini-3.8-flash", "gemini-3.5-flash-lite",
          "gemini-3.1-flash-lite", "gemini-flash-lite-latest"]
KNOWLEDGE = (Path(__file__).with_name("knowledge.md")).read_text(encoding="utf-8")

# 免費方案的 Google 搜尋額度是 0（一用就 429），只用免費的網址讀取
WEB_TOOLS = [types.Tool(url_context=types.UrlContext())]

STYLE_GUIDE = """\
你是新北市立永平高級中學的國際教育課程設計師，也是很會講笑話的資深老師。
你要依教師輸入，產出一套「國際教育課程」：教案、上課簡報（含講稿）、課程網站內容。

撰寫依據：
1. 使用者訊息最後附有〈教育部國際教育網站閱讀筆記〉，是剛讀過 https://www.ietw2.edu.tw/ 課程工具包的結果，
   請參考其中的工具包作法、學習目標寫法與評量方式。
2. 依下方〈永平高中背景知識〉與〈教師修改後回饋的經驗〉撰寫，讓內容貼近永平真實的交流經驗
   （例如馬來西亞循人中學學伴、銀禧老婦院、長照／日照中心、聖愛教養院、脊髓損傷重建中心、淨灘）。

寫作規範：
- 一律使用台灣繁體中文（不可出現簡體字）、十二年國教用語。教案語氣專業具體；講稿與網站可以幽默風趣（諧音梗、生活比喻、和學生對話），但不嘲笑長者、身障者或任何文化。
- 指標對應（最重要，務必逐條做到）：
  1. objectives 只能、也必須包含教師勾選的每一個實質內涵（代碼與文字照抄），不可漏掉、不可自行增加。
  2. 每個實質內涵轉化 2～3 條學習目標，編號「國U9-1、國U9-2」；寫法依實作手冊：以學生為主詞、
     使用與該內涵相符的具體動詞（說明、比較、分析、設計、反思、提出…）、寫出情境或條件、具體結果、可衡量的標準
     （例：「能比較臺灣與馬來西亞至少兩項長者照顧方式的異同，並寫出一項自己的反思」）。
  3. 每條學習目標至少要出現在一個活動的 goal_codes；每個活動的 formative 要寫出「看到什麼表現代表達成哪個目標」，
     例如「國U5-1：學習單能寫出兩項文化異同」。
  4. 總結性評量的 goal_codes 要涵蓋全部學習目標；評量規準每個向度都要標 goal_codes，
     所有向度合起來要涵蓋全部學習目標（「彰顯國家價值」面向的目標也要有向度評量）。
  5. goal_codes 一律用學習目標編號（國U9-1），不要只寫內涵代碼（國U9）。summative.name 只寫任務名稱，不要加【】。
- 教學活動節數／分鐘數加總要等於教師填的教學時間（一節 50 分鐘；國中 45 分鐘；高國中混齡以 50 分鐘計）。
- 每個活動寫具體步驟（教師提問、學生任務、分組方式），並寫形成性評量；總結性評量是一個【探究與行動任務】，附 3 等第評量規準。
- 探究問題分事實性、概念性、辯論性。
- 簡報：每張投影片字要少、字要大——標題 14 字內、條列最多 4 點、每點 18 字內；講稿寫在 notes，
  是老師可以直接照著念的口語稿（120～250 字），要幽默、有互動提問、有轉場句。投影片 12～20 張，
  包含：封面、今天的任務、暖身提問、各活動、探究問題、小組任務、評量規準、反思、結語。
- 只引用確定存在的網址；toolkit_refs 只能列你實際讀到的頁面。不要編造學生姓名或具體人數。
- 不要提到 AI、本工具或「教師輸入」等字眼。
"""

RESEARCH_GUIDE = """\
你是國際教育課程研究助理。請閱讀（用網址讀取工具）教育部中小學國際教育網站 https://www.ietw2.edu.tw/ 的課程工具包
（https://www.ietw2.edu.tw/toolkit/index/type/0801 ）以及使用者列出的每個學習目標檢索網址，
從這些頁面中找出與課程主題相關的工具包或教學資源連結，再讀進去看內容。
最後用條列整理（1500 字內）：每個找到的工具包／資源的名稱、網址（只列實際讀到的）、
可借用的學習目標寫法、教學活動、評量方式與評量規準。只寫讀到的事實，不要自己編課程。
"""

S = {"type": "string"}
LS = {"type": "array", "items": S}


def _obj(**props):
    return {"type": "object", "properties": props, "required": list(props)}


SCHEMA = _obj(
    title=S, subtitle=S, design_rationale=S, domains=S, grade=S, total_time=S,
    approach=S, key_concepts=LS,
    objectives={"type": "array", "items": _obj(
        code=S, text=S, goals={"type": "array", "items": _obj(code=S, text=S)})},
    issues={"type": "array", "items": _obj(name=S, integration=S)},
    inquiry=_obj(factual=LS, conceptual=LS, debatable=LS),
    summative=_obj(name=S, description=S, goal_codes=LS, rubric={"type": "array", "items": _obj(
        dimension=S, goal_codes=LS, excellent=S, good=S, developing=S)}),
    activities={"type": "array", "items": _obj(
        name=S, time=S, goal_codes=LS, steps=LS, formative=S)},
    expected_outcomes=LS, materials=LS,
    toolkit_refs={"type": "array", "items": _obj(title=S, url=S, how_used=S)},
)
# 一次輸出太長容易被截斷，簡報與網站分開第二次產生
DECK_SCHEMA = _obj(
    slides={"type": "array", "items": _obj(title=S, bullets=LS, notes=S)},
    site=_obj(tagline=S, intro=S, student_mission=S, family_note=S, faq={"type": "array", "items": _obj(q=S, a=S)}),
)

LEARN_SCHEMA = _obj(summary=S, lessons=LS)


class AIError(RuntimeError):
    pass


def _parts(attachments: list[dict]) -> list:
    """drive.to_blocks 的結果轉成 Gemini 的 Part。"""
    out = []
    for a in attachments:
        if "text" in a:
            out.append(types.Part.from_text(text=f"《{a['name']}》\n{a['text']}"))
        else:
            out.append(types.Part.from_bytes(data=a["data"], mime_type=a["mime"]))
    return out


def _gen(api_key: str, models: list[str], system: str, parts: list, schema: dict | None = None,
         tools: list | None = None):
    client = genai.Client(api_key=api_key)
    config = types.GenerateContentConfig(system_instruction=system, max_output_tokens=65536, tools=tools)
    if schema:
        config.response_mime_type = "application/json"
        config.response_json_schema = schema
    last = None
    models = list(models)
    # 免費版常忙線（503）或達每分鐘上限（429）：輪流試每個模型，整輪失敗就等一下再來，最多約 3 分鐘
    for rnd in range(5):
        for model in list(models):
            try:
                resp = client.models.generate_content(model=model, contents=parts, config=config)
            except errors.ClientError as e:
                last = e
                if e.code == 404:  # 模型已停用
                    models.remove(model)
                    continue
                if e.code == 429:
                    continue
                if e.code in (401, 403) or "API key" in str(e):
                    raise AIError("Gemini 金鑰無效，請管理者檢查 secrets 的 GEMINI_API_KEY") from e
                raise AIError(f"AI 請求錯誤：{e.message}") from e
            except errors.ServerError as e:
                last = e
                continue
            if not resp.candidates:
                raise AIError("AI 無法處理這份資料，請調整內容後再試")
            if str(resp.candidates[0].finish_reason).endswith("MAX_TOKENS"):
                raise AIError("AI 回覆太長被截斷，請縮短教學時間或補充說明後再試")
            return resp
        if not models:  # 名單上的模型都被停用：向 Google 查詢目前可用的 Flash 模型
            models = _discover(client)
            if not models:
                break
        if rnd < 4:
            time.sleep(15 + 15 * rnd)
    if isinstance(last, errors.ClientError) and last.code == 429:
        raise AIError("今天的 Gemini 免費額度用完了（或使用的人太多），請過幾分鐘或明天再試")
    raise AIError(f"AI 服務暫時無法使用：{last}")


def _discover(client) -> list[str]:
    try:
        names = [m.name.removeprefix("models/") for m in client.models.list()
                 if "generateContent" in (m.supported_actions or [])]
    except errors.APIError:
        return []
    skip = ("tts", "image", "omni", "audio", "live", "embedding")
    return sorted((n for n in names if "flash" in n and not any(x in n for x in skip)), reverse=True)[:6]


def _json(resp) -> dict:
    text = resp.text or ""
    try:
        return json.loads(text[text.find("{"):text.rfind("}") + 1])
    except json.JSONDecodeError as e:
        raise AIError("AI 回覆格式錯誤，請再試一次") from e


def _system(learned: str) -> str:
    text = STYLE_GUIDE + "\n〈永平高中背景知識〉\n" + KNOWLEDGE
    if learned.strip():
        text += "\n〈教師修改後回饋的經驗〉（請優先遵循）\n" + learned
    return text


_S2TW = OpenCC("s2tw")


def _to_trad(v):
    """Gemini 偶爾混用簡體字與“”引號：全部轉成台灣繁體與「」。"""
    if isinstance(v, str):
        return _S2TW.convert(v).replace("“", "「").replace("”", "」")
    if isinstance(v, list):
        return [_to_trad(x) for x in v]
    if isinstance(v, dict):
        return {k: _to_trad(x) for k, x in v.items()}
    return v


def _fix_codes(lesson: dict, form: dict):
    """統一編號：內涵用勾選的代碼與原文，目標依序編成「國U2-1」，活動、總結性評量與規準裡的引用一起改。"""
    texts = {c: t for c, _, t, _ in form["objectives"]}
    remap: dict[str, str] = {}  # 模型原本寫的目標編號 → 正確編號
    groups: dict[str, list[str]] = {}  # 內涵代碼 → 底下的目標編號
    for o in lesson["objectives"]:
        m = re.match(r"國[EJU]\d+", o["code"].replace(" ", ""))
        if not m:
            continue
        base = m.group()
        o["code"] = base
        o["text"] = texts.get(base, o["text"])
        for i, g in enumerate(o["goals"], 1):
            new = f"{base}-{i}"
            remap[g["code"].replace(" ", "")] = new
            g["code"] = new
        groups[base] = [g["code"] for g in o["goals"]]

    def fix(codes: list[str]) -> list[str]:
        out = []
        for c in codes:
            c = c.replace(" ", "")
            if c in remap:
                out.append(remap[c])
            elif c in groups:  # 只寫內涵代碼：視為對應底下全部目標
                out += groups[c]
            else:
                m = re.match(r"國[EJU]\d+-\d+", c)
                out.append(m.group() if m else c)
        return list(dict.fromkeys(out))

    for a in lesson["activities"]:
        a["goal_codes"] = fix(a.get("goal_codes", []))
    summ = lesson["summative"]
    summ["goal_codes"] = fix(summ.get("goal_codes", []))
    for r in summ["rubric"]:
        r["goal_codes"] = fix(r.get("goal_codes", []))
    summ["name"] = re.sub(r"[【】]", "", summ["name"]).removesuffix("總結性評量").strip()


def check_alignment(lesson: dict, form: dict) -> list[str]:
    """檢查教案是否對應教師勾選的指標；回傳問題清單（空清單代表全部對應）。"""
    problems = []
    chosen = [c for c, *_ in form["objectives"]]
    have = {o["code"]: o for o in lesson["objectives"]}
    for c in chosen:
        if c not in have:
            problems.append(f"勾選的指標 {c} 沒有出現在教案中")
        elif not have[c]["goals"]:
            problems.append(f"{c} 沒有轉化成學習目標")
    for c in have:
        if c not in chosen:
            problems.append(f"{c} 不是勾選的指標")
    used = {c for a in lesson["activities"] for c in a["goal_codes"]}
    summ = set(lesson["summative"]["goal_codes"])
    rubric = {c for r in lesson["summative"]["rubric"] for c in r["goal_codes"]}
    for o in lesson["objectives"]:
        for g in o["goals"]:
            code = g["code"]
            if code not in used:
                problems.append(f"學習目標 {code} 沒有對應的教學活動")
            if code not in summ:
                problems.append(f"學習目標 {code} 沒有納入總結性評量")
            if code not in rubric:
                problems.append(f"學習目標 {code} 沒有對應的評量規準向度")
    return problems


def _report(resp, on_event):
    """把 Gemini 實際搜尋與讀取的網址顯示給使用者。"""
    cand = resp.candidates[0]
    gm = getattr(cand, "grounding_metadata", None)
    for q in (gm.web_search_queries or []) if gm else []:
        on_event("web_search", {"query": q})
    um = getattr(cand, "url_context_metadata", None)
    for m in (um.url_metadata or []) if um else []:
        on_event("web_fetch", {"url": m.retrieved_url})


def generate(api_key: str, form: dict, attachments: list[dict], learned: str, on_event=None,
             models: list[str] = MODELS) -> dict:
    """form：教師輸入；attachments：drive.to_blocks 轉好的參考教材。"""
    lines = [
        f"教學年段：{form['level']}",
        f"教學時間：{form['time']}",
        f"課程目標：{form['goal']}",
        f"期望達到的課程成效：{form['outcome']}",
        f"要融合的議題：{'、'.join(form['issues']) or '（未勾選）'}",
        "國際教育議題實質內涵（請逐一閱讀後面的學習目標檢索網址）：",
        *[f"- {c} {t}（{face}）：{url}" for c, face, t, url in form["objectives"]],
        f"課程補充說明：{form['note'] or '（無）'}",
        "相關連結：" + ("\n" + "\n".join(form["links"]) if form["links"] else "（無）"),
    ]
    request = "\n".join(lines)
    resp = _gen(api_key, models, RESEARCH_GUIDE, [request + "\n\n請先讀 https://www.ietw2.edu.tw/toolkit/index/type/0801"],
                tools=WEB_TOOLS)
    research = resp.text or ""
    if on_event:
        _report(resp, on_event)
        on_event("lesson", {})
    system = _system(learned)
    parts = [*_parts(attachments), request + "\n\n〈教育部國際教育網站閱讀筆記〉\n" + research
             + "\n\n先輸出教案（簡報與網站下一步再做）。"]
    lesson = _json(_gen(api_key, models, system, parts, SCHEMA))
    _fix_codes(lesson, form)
    problems = check_alignment(lesson, form)
    if problems:  # 有沒對應到的指標：請 AI 只修正對應問題
        if on_event:
            on_event("repair", {"problems": problems})
        fix_req = (request + "\n\n〈教案初稿〉\n" + json.dumps(lesson, ensure_ascii=False)
                   + "\n\n這份教案的指標對應有以下問題，請修正後輸出完整教案（其餘內容盡量保留）：\n- "
                   + "\n- ".join(problems))
        lesson = _json(_gen(api_key, models, system, [fix_req], SCHEMA))
        _fix_codes(lesson, form)
        problems = check_alignment(lesson, form)
    lesson["alignment_issues"] = problems
    if on_event:
        on_event("deck", {})
    deck_req = (request + "\n\n〈已完成的教案〉\n" + json.dumps(lesson, ensure_ascii=False)
                + "\n\n請依這份教案輸出上課簡報（slides，含幽默講稿）與課程網站文字（site）。")
    lesson.update(_json(_gen(api_key, models, system, [deck_req], DECK_SCHEMA)))
    return _to_trad(lesson)


def learn(api_key: str, name: str, attachments: list[dict], models: list[str] = MODELS) -> dict:
    """讀一份老師修改後的檔案（或學校參考資料），整理成之後產生課程時要遵循的經驗。"""
    system = (
        "你在幫永平高中的國際教育課程產生器累積經驗。以下是一份教師修改後上傳的教案／簡報，或學校的參考資料。"
        "請整理：summary（80 字內說明這份檔案是什麼）、lessons（3～8 條具體、可直接套用的寫作原則或在地事實，"
        "例如老師偏好的活動流程、用詞、評量方式、時間配置、服務機構細節）。不要寫學生姓名或個資。"
    )
    return _to_trad(_json(_gen(api_key, models, system, [*_parts(attachments), f"檔名：{name}"], LEARN_SCHEMA)))
