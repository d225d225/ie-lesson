"""秋楓樣式：配色、字型、楓葉 SVG。"""

PARCHMENT = "#F7F1E3"
MAPLE = "#B23A2B"
DEEP_MAPLE = "#7A1F16"
AMBER = "#C8892B"
LEAF_BROWN = "#8C6A4F"
INK = "#3B2A20"
TEXT = "#000000"  # 所有文字一律黑色（使用者要求）


def maple_svg(size: int = 28, color: str = MAPLE, rotate: int = 0, opacity: float = 1.0) -> str:
    return (
        f'<svg width="{size}" height="{size}" viewBox="0 0 64 64" '
        f'style="transform:rotate({rotate}deg);opacity:{opacity}" aria-hidden="true">'
        f'<path fill="{color}" d="M32 2l5 11 9-5-2 12 12-3-5 10 11 3-12 8 3 6-14-2 1 9-6-4'
        f'-2 15h-2l-2-15-6 4 1-9-14 2 3-6-12-8 11-3-5-10 12 3-2-12 9 5z"/>'
        f'<path stroke="{DEEP_MAPLE}" stroke-width="1.6" fill="none" d="M32 14v48"/></svg>'
    )


CSS = f"""
<style>
@import url('https://fonts.googleapis.com/css2?family=Noto+Sans+TC:wght@400;500;700&family=Noto+Serif+TC:wght@600;700;900&display=swap');

html, body, [class*="css"], .stApp, .stMarkdown, input, textarea, button, select {{
  font-family: 'Noto Sans TC', sans-serif !important;
}}
.stApp {{ background: {PARCHMENT}; color: {TEXT}; }}
h1, h2, h3, h4, .serif {{ font-family: 'Noto Serif TC', serif !important; color: {TEXT}; letter-spacing: .02em; }}
[data-testid="stSidebar"] {{ background: #EFE5CF; border-right: 1px solid {LEAF_BROWN}33; }}
.block-container {{ padding-top: 1.6rem; max-width: 1180px; }}

/* 頁首 */
.hero {{ position: relative; overflow: hidden; padding: 22px 26px 18px; margin-bottom: 14px;
  background: linear-gradient(135deg, #FBF6EA 0%, #F3E6CC 100%);
  border: 1px solid {LEAF_BROWN}55; border-radius: 12px; }}
.hero h1 {{ margin: 0; font-size: 1.75rem; font-weight: 900; display: flex; align-items: center; gap: 10px; }}
.hero .sub {{ color: {TEXT}; margin-top: 4px; font-size: .95rem; }}
.hero .chip {{ display: inline-block; margin-top: 10px; padding: 3px 12px; border-radius: 999px;
  background: {MAPLE}; color: #fff; font-size: .85rem; font-weight: 500; }}
.hero .leaves {{ position: absolute; right: 18px; top: 8px; pointer-events: none; }}
.hero .leaves span {{ position: absolute; }}

/* 部別選擇列 */
.st-key-picker {{ background: #FFFBF2; border: 1px solid {LEAF_BROWN}55; border-radius: 10px;
  padding: 12px 16px 4px; margin-bottom: 8px; }}
.st-key-picker [data-testid="stWidgetLabel"] p {{ font-family: 'Noto Serif TC', serif; color: {TEXT}; font-weight: 700; }}
.st-key-picker button[kind^="segmented_control"] {{ border-color: {LEAF_BROWN}66; color: {TEXT}; min-width: 64px; }}
.st-key-picker button[kind="segmented_controlActive"] {{ background: {MAPLE} !important; border-color: {MAPLE} !important; color: #fff !important; }}

/* 卡片與數字 */
.card {{ background: #FFFBF2; border: 1px solid {LEAF_BROWN}55; border-radius: 10px;
  padding: 14px 18px; box-shadow: 0 1px 3px rgba(59,42,32,.08); margin-bottom: 12px; }}
.stat {{ text-align: center; }}
.stat .n {{ font-family: 'Noto Serif TC', serif; font-size: 2rem; font-weight: 900; color: {TEXT}; line-height: 1.1; }}
.stat .l {{ color: {TEXT}; font-size: .85rem; }}

/* 步驟列 */
.steps {{ display: flex; gap: 6px; margin: 4px 0 16px; flex-wrap: wrap; }}
.steps div {{ flex: 1; min-width: 120px; text-align: center; padding: 8px 6px; border-radius: 8px;
  background: #EFE5CF; color: {TEXT}; font-size: .9rem; border: 1px solid transparent; }}
.steps div.on {{ background: {MAPLE}; color: #fff; font-weight: 700; }}
.steps div.done {{ background: #fff; color: {TEXT}; border-color: {MAPLE}66; }}

/* 按鈕 */
.stButton > button, .stDownloadButton > button, .stLinkButton > a {{
  border-radius: 8px !important; border: 1px solid {MAPLE} !important; color: {TEXT} !important;
  background: #FFFBF2 !important; }}
.stButton > button[kind="primary"], .stFormSubmitButton > button {{
  background: {MAPLE} !important; color: #fff !important; }}
.stButton > button:hover {{ border-color: {DEEP_MAPLE} !important; }}

/* 分頁 */
.stTabs [data-baseweb="tab-list"] {{ gap: 4px; border-bottom: 1px solid {LEAF_BROWN}44; flex-wrap: wrap; }}
.stTabs [data-baseweb="tab"] {{ font-family: 'Noto Serif TC', serif; color: {TEXT}; }}
.stTabs [aria-selected="true"] {{ color: {TEXT} !important; font-weight: 700; }}
.stTabs [data-baseweb="tab-highlight"] {{ background: {MAPLE}; }}
.stProgress > div > div > div > div {{ background: {AMBER}; }}

/* 預覽 */
.pv {{ background: #fff; border: 1px solid {LEAF_BROWN}55; border-radius: 10px; padding: 18px; }}
.pv-title {{ text-align: center; font-family: 'Noto Serif TC', serif; font-weight: 700; font-size: 1.1rem; }}
.pv-meta {{ text-align: center; color: {TEXT}; margin: 6px 0 10px; }}
.pv table {{ width: 100%; border-collapse: collapse; margin-bottom: 10px; font-size: .9rem; }}
.pv th, .pv td {{ border: 1px solid #9C8775; padding: 6px 8px; vertical-align: top; }}
.pv th {{ background: #F3E9D6; white-space: nowrap; width: 1%; }}
.pv .star {{ color: {TEXT}; white-space: nowrap; }}
.pv .muted, .muted {{ color: {TEXT}; }}

/* 其他文字：說明小字、欄位標題、提示框、側欄文字也都改黑色 */
[data-testid="stCaptionContainer"], [data-testid="stCaptionContainer"] *,
[data-testid="stWidgetLabel"], [data-testid="stWidgetLabel"] *,
[data-testid="stMarkdownContainer"], [data-testid="stMarkdownContainer"] p,
[data-testid="stAlert"] *, [data-testid="stExpander"] summary *,
[data-testid="stSidebar"] *, .stTextArea textarea, .stTextInput input {{ color: {TEXT} !important; }}
/* 輸入框提示字、上傳框說明、勾選框與下拉選單文字也用黑色 */
input::placeholder, textarea::placeholder {{ color: {TEXT} !important; opacity: 1 !important; }}
[data-testid="stFileUploaderDropzoneInstructions"] *, [data-testid="stFileUploaderFile"] *,
[data-testid="stCheckbox"] *, [data-baseweb="select"] *, [data-testid="stToggle"] *,
[data-testid="stMetric"] *, [data-testid="stTooltipIcon"] *, small {{ color: {TEXT} !important; }}

/* 紅底按鈕維持白字，才看得清楚 */
.stButton > button[kind="primary"] *, .stFormSubmitButton > button *,
button[kind="segmented_controlActive"] *, .steps div.on {{ color: #fff !important; }}

@media (max-width: 640px) {{
  .hero h1 {{ font-size: 1.3rem; }}
  .hero .leaves {{ display: none; }}
  .block-container {{ padding-left: 1rem; padding-right: 1rem; }}
}}
</style>
"""


def hero(title: str, sub: str, chip: str = "") -> str:
    leaves = (
        f'<span style="right:0;top:0">{maple_svg(54, MAPLE, 18, .9)}</span>'
        f'<span style="right:64px;top:34px">{maple_svg(22, AMBER, -30, .55)}</span>'
        f'<span style="right:30px;top:70px">{maple_svg(16, DEEP_MAPLE, 50, .4)}</span>'
    )
    return (
        f'<div class="hero"><div class="leaves">{leaves}</div>'
        f'<h1>{maple_svg(30)}{title}</h1><div class="sub">{sub}</div>'
        + (f'<span class="chip">{chip}</span>' if chip else '') + '</div>'
    )


def steps(current: int) -> str:
    names = ["① 填寫資料", "② AI 撰寫", "③ 確認內容", "④ 下載表件"]
    out = []
    for i, n in enumerate(names, 1):
        cls = "on" if i == current else ("done" if i < current else "")
        out.append(f'<div class="{cls}">{n}</div>')
    return f'<div class="steps">{"".join(out)}</div>'


def stat(n, label: str) -> str:
    return f'<div class="card stat"><div class="n">{n}</div><div class="l">{label}</div></div>'
