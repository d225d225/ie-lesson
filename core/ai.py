"""Claude API：先查教育部國際教育網站與課程工具包，再撰寫教案、簡報講稿與課程網站內容。"""
from __future__ import annotations

import json
from pathlib import Path

import anthropic

MODEL = "claude-opus-5-5"
KNOWLEDGE = (Path(__file__).with_name("knowledge.md")).read_text(encoding="utf-8")

WEB_TOOLS = [
    {"type": "web_search_20260209", "name": "web_search", "max_uses": 6},
    {"type": "web_fetch_20260209", "name": "web_fetch", "max_uses": 8},
]

STYLE_GUIDE = """\
你是新北市立永平高級中學的國際教育課程設計師，也是很會講笑話的資深老師。
你要依教師輸入，產出一套「國際教育課程」：教案、上課簡報（含講稿）、課程網站內容。

撰寫依據：
1. 使用者訊息最後附有〈教育部國際教育網站閱讀筆記〉，是剛讀過 https://www.ietw2.edu.tw/ 課程工具包的結果，
   請參考其中的工具包作法、學習目標寫法與評量方式。
2. 依下方〈永平高中背景知識〉與〈教師修改後回饋的經驗〉撰寫，讓內容貼近永平真實的交流經驗
   （例如馬來西亞循人中學學伴、銀禧老婦院、長照／日照中心、聖愛教養院、脊髓損傷重建中心、淨灘）。

寫作規範：
- 台灣繁體中文、十二年國教用語。教案語氣專業具體；講稿與網站可以幽默風趣（諧音梗、生活比喻、和學生對話），但不嘲笑長者、身障者或任何文化。
- 學習目標：每個勾選的實質內涵轉化 1～3 條，編號「國U9-1」，以學生為主詞、可評量。
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
你是國際教育課程研究助理。請用 web_fetch 閱讀教育部中小學國際教育網站 https://www.ietw2.edu.tw/ 的課程工具包
（https://www.ietw2.edu.tw/toolkit/index/type/0801 ）以及使用者列出的每個學習目標檢索網址，
必要時用 web_search 搜尋 ietw2.edu.tw 上與課程主題相關的工具包或教學資源，點進去讀內容。
最後用條列整理（1500 字內）：每個找到的工具包／資源的名稱、網址（只列實際讀到的）、
可借用的學習目標寫法、教學活動、評量方式與評量規準。只寫讀到的事實，不要自己編課程。
"""

S = {"type": "string"}
LS = {"type": "array", "items": S}


def _obj(**props):
    return {"type": "object", "properties": props, "required": list(props), "additionalProperties": False}


SCHEMA = _obj(
    title=S, subtitle=S, design_rationale=S, domains=S, grade=S, total_time=S,
    approach=S, key_concepts=LS,
    objectives={"type": "array", "items": _obj(
        code=S, text=S, goals={"type": "array", "items": _obj(code=S, text=S)})},
    issues={"type": "array", "items": _obj(name=S, integration=S)},
    inquiry=_obj(factual=LS, conceptual=LS, debatable=LS),
    summative=_obj(name=S, description=S, rubric={"type": "array", "items": _obj(
        dimension=S, excellent=S, good=S, developing=S)}),
    activities={"type": "array", "items": _obj(
        name=S, time=S, goal_codes=LS, steps=LS, formative=S)},
    expected_outcomes=LS, materials=LS,
    toolkit_refs={"type": "array", "items": _obj(title=S, url=S, how_used=S)},
)
# 結構化輸出的文法有大小上限，簡報與網站分開第二次產生
DECK_SCHEMA = _obj(
    slides={"type": "array", "items": _obj(title=S, bullets=LS, notes=S)},
    site=_obj(tagline=S, intro=S, student_mission=S, family_note=S, faq={"type": "array", "items": _obj(q=S, a=S)}),
)

LEARN_SCHEMA = _obj(summary=S, lessons=LS)


class AIError(RuntimeError):
    pass


class GrammarTooLarge(AIError):
    pass


def _client(api_key: str) -> anthropic.Anthropic:
    return anthropic.Anthropic(api_key=api_key, timeout=900, max_retries=3)


def _call(api_key: str, system, content: list, schema: dict | None = None, tools: list | None = None,
          effort: str = "medium", on_event=None) -> str:
    """回傳 AI 的文字回覆。schema 與 tools 不能同時用（結構化輸出的文法會太大）。"""
    client = _client(api_key)
    messages = [{"role": "user", "content": content}]
    done = []  # pause_turn 前已產生的內容
    kwargs = dict(
        model=MODEL, max_tokens=64000, system=system,
        extra_headers={"anthropic-beta": "server-side-fallback-2026-07-01"},
        extra_body={"fallbacks": "default", "output_config": {"effort": effort}},
    )
    if schema:
        kwargs["extra_body"]["output_config"]["format"] = {"type": "json_schema", "schema": schema}
    if tools:
        kwargs["tools"] = tools
    try:
        for _ in range(6):  # 伺服器端工具用到一半可能回 pause_turn，要接著送
            with client.messages.stream(messages=messages, **kwargs) as stream:
                for ev in stream:
                    if on_event and ev.type == "content_block_start":
                        b = ev.content_block
                        if b.type == "server_tool_use":
                            on_event(b.name, b.input)
                msg = stream.get_final_message()
            if msg.stop_reason != "pause_turn":
                break
            done += msg.content
            messages = [messages[0], {"role": "assistant", "content": done}]
    except anthropic.AuthenticationError as e:
        raise AIError("AI 金鑰無效，請管理者檢查 secrets 設定") from e
    except anthropic.RateLimitError as e:
        raise AIError("AI 使用量暫時達到上限，請稍後再試") from e
    except anthropic.APIStatusError as e:
        if "credit balance" in str(e):
            raise AIError("AI 帳戶額度用完了，請管理者到 Anthropic Console 的 Plans & Billing 儲值") from e
        if "grammar is too large" in str(e):
            raise GrammarTooLarge(str(e)) from e
        if isinstance(e, anthropic.BadRequestError):
            raise AIError(f"AI 請求格式錯誤：{e.message}") from e
        raise AIError(f"AI 服務錯誤（{e.status_code}），請稍後再試") from e
    except anthropic.APIConnectionError as e:
        raise AIError("連不上 AI 服務，請檢查網路") from e

    if msg.stop_reason == "refusal":
        raise AIError("AI 無法處理這份資料，請調整內容後再試")
    if msg.stop_reason == "max_tokens":
        raise AIError("AI 回覆太長被截斷，請縮短教學時間或補充說明後再試")
    return "".join(b.text for b in msg.content if b.type == "text")


def _run(api_key: str, system, content: list, schema: dict, effort: str = "medium") -> dict:
    try:
        text = _call(api_key, system, content, schema=schema, effort=effort)
    except GrammarTooLarge:  # 結構化輸出放不下時，改成用文字要求 JSON
        rule = "只輸出一個 JSON 物件（不要 ``` 標記、不要其他文字），欄位必須完全符合這個 JSON Schema：\n"
        text = _call(api_key, system, [*content, {"type": "text", "text": rule + json.dumps(schema, ensure_ascii=False)}],
                     effort=effort)
    try:
        return json.loads(text[text.find("{"):text.rfind("}") + 1])
    except json.JSONDecodeError as e:
        raise AIError("AI 回覆格式錯誤，請再試一次") from e


def _system(learned: str) -> list:
    blocks = [{"type": "text", "text": STYLE_GUIDE},
              {"type": "text", "text": "〈永平高中背景知識〉\n" + KNOWLEDGE, "cache_control": {"type": "ephemeral"}}]
    if learned.strip():
        blocks.append({"type": "text", "text": "〈教師修改後回饋的經驗〉（請優先遵循）\n" + learned})
    return blocks


def generate(api_key: str, form: dict, attachments: list[dict], learned: str, on_event=None) -> dict:
    """form：教師輸入；attachments：已轉成 Claude content block 的參考教材。"""
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
    research = _call(api_key, RESEARCH_GUIDE, [{"type": "text", "text": request}], tools=WEB_TOOLS,
                     effort="medium", on_event=on_event)
    content = [*attachments, {"type": "text", "text": request + "\n\n〈教育部國際教育網站閱讀筆記〉\n" + research
                              + "\n\n先輸出教案（簡報與網站下一步再做）。"}]
    system = _system(learned)
    if on_event:
        on_event("lesson", {})
    lesson = _run(api_key, system, content, SCHEMA, effort="high")
    if on_event:
        on_event("deck", {})
    deck_req = (request + "\n\n〈已完成的教案〉\n" + json.dumps(lesson, ensure_ascii=False)
                + "\n\n請依這份教案輸出上課簡報（slides，含幽默講稿）與課程網站文字（site）。")
    lesson.update(_run(api_key, system, [{"type": "text", "text": deck_req}], DECK_SCHEMA, effort="medium"))
    return lesson


def learn(api_key: str, name: str, attachments: list[dict]) -> dict:
    """讀一份老師修改後的檔案（或學校參考資料），整理成之後產生課程時要遵循的經驗。"""
    system = (
        "你在幫永平高中的國際教育課程產生器累積經驗。以下是一份教師修改後上傳的教案／簡報，或學校的參考資料。"
        "請整理：summary（80 字內說明這份檔案是什麼）、lessons（3～8 條具體、可直接套用的寫作原則或在地事實，"
        "例如老師偏好的活動流程、用詞、評量方式、時間配置、服務機構細節）。不要寫學生姓名或個資。"
    )
    content = [*attachments, {"type": "text", "text": f"檔名：{name}"}]
    return _run(api_key, system, content, LEARN_SCHEMA, effort="low")
