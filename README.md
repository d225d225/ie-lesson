# 永平高中・國際教育課程教案投影片產生器

教師填寫課程需求（教學年段、教學時間、課程目標、期望成效、融合議題、國際教育議題實質內涵、補充說明、參考教材、相關連結），
AI 先閱讀教育部中小學國際教育網站與課程工具包，再依永平高中的交流經驗撰寫，一次產出：

- **教案**（Google 文件／Word）：依教育部《國際教育融入課程實作手冊》教學活動與評量設計表格式
- **上課簡報**（Google 簡報／PPT）：大字、每張都有幽默的口語講稿（在講者備忘稿）
- **課程網站**：由 Apps Script 網頁應用程式顯示（`…/exec?site=<檔案ID>`），內嵌簡報與交流影片

每組課程存在雲端「國際教育」資料夾的 `05-AI產出課程/<日期 課程名稱>/`。不需要密碼。

教師修改後可在「上傳修改後的檔案」上傳（存到 `04-reference`），按「讓 AI 閱讀資料」後，
AI 會逐一閱讀 01～04 資料夾的檔案，整理成 `AI學習筆記.json`，之後每次產生課程都會參考（老師修改檔優先）。

## 檔案
- `app.py`：Streamlit 介面
- `core/ai.py`：Claude（claude-opus-5-5）三步驟：查網站 → 寫教案 → 寫簡報講稿與網站
- `core/knowledge.md`：永平高中國際交流背景知識（馬來西亞循人中學、銀禧老婦院、長照／日照中心、聖愛教養院、脊損中心、淨灘…）
- `core/builders.py`：產生 Word、PPT、課程網站 HTML
- `core/data.py`：國際教育議題實質內涵與議題清單
- `apps_script/Code.gs`：雲端硬碟橋接（建資料夾、轉 Google 格式、上傳、AI 學習筆記、顯示課程網站）

## 部署
1. **Apps Script**：到 https://script.google.com 用擁有「國際教育」資料夾的帳號（d225@yphs.tw）新增專案，
   貼上 `apps_script/Code.txt`（含真正的 SECRET，未上傳 GitHub），在「專案設定」勾選顯示 appsscript.json 並貼上 `apps_script/appsscript.json`。
   先選函式 `authorize` 按「執行」授權，再「部署 → 新增部署作業 → 網頁應用程式」，執行身分「我」、存取權「任何人」，複製網址。
2. **Streamlit**：`secrets.toml` 填 `ANTHROPIC_API_KEY_B64`、`GAS_WEBHOOK_URL`（上一步的網址）、`GAS_SECRET`。
3. 本機執行：`pip install -r requirements.txt && streamlit run app.py`

## 注意
- Google 協作平台（Google Sites）沒有開放 API，無法由程式自動建立；課程網站改由 Apps Script 網頁應用程式提供，
  若要放進 Google 協作平台，可在協作平台用「嵌入 → 網址」貼上課程網站連結。
- 學校網域若禁止對外分享，課程資料夾會自動改為「網域內知道連結者可檢視」。
