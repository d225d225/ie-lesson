/**
 * 永平高中國際教育課程產生器 — Google Apps Script 橋接
 *
 * 部署方式：網頁應用程式，執行身分「我」，存取權「任何人」。
 * 不需要啟用進階服務。第一次貼上後，請先在編輯器上方選「authorize」按「執行」完成授權。
 *
 * 課程網站：本網頁應用程式的網址加上 ?site=<課程網站.html 的檔案 ID> 就會顯示該課程的網站。
 */

// 與 Streamlit secrets 的 GAS_SECRET 相同
const SECRET = '請改成與 GAS_SECRET 相同的一串亂碼';

const ROOT_FOLDER_ID = '1IZGDtBSv-ijCZk8Gk79wV8WGRNCYDeyV';      // 國際教育總資料夾
const REFERENCE_FOLDER_ID = '1vXv2l5m6n9fHiWqV0oExdl-CXHsqpGiT'; // 04-reference：老師修改後上傳
const OUTPUT_FOLDER_NAME = '05-AI產出課程';                        // 每組課程一個子資料夾
const KNOWLEDGE_FILE = 'AI學習筆記.json';                          // AI 讀過的資料與整理出的經驗

const DOCX_MIME = 'application/vnd.openxmlformats-officedocument.wordprocessingml.document';
const PPTX_MIME = 'application/vnd.openxmlformats-officedocument.presentationml.presentation';
const GDOC_MIME = 'application/vnd.google-apps.document';
const GSLIDES_MIME = 'application/vnd.google-apps.presentation';
const GSHEET_MIME = 'application/vnd.google-apps.spreadsheet';
const FOLDER_MIME = 'application/vnd.google-apps.folder';

function doPost(e) {
  try {
    const p = JSON.parse(e.postData.contents);
    if (p.secret !== SECRET) return json_({ ok: false, error: 'unauthorized' });
    const fn = ACTIONS[p.action];
    if (!fn) return json_({ ok: false, error: 'unknown action: ' + p.action });
    return json_({ ok: true, result: fn(p) });
  } catch (err) {
    return json_({ ok: false, error: String(err && err.stack || err) });
  }
}

/** ?site=<檔案ID> 顯示課程網站；沒有參數時回報服務狀態。 */
function doGet(e) {
  const id = e && e.parameter && e.parameter.site;
  if (!id) return json_({ ok: true, result: 'ie-lesson bridge alive' });
  const file = DriveApp.getFileById(id);
  if (!isInside_(file, ROOT_FOLDER_ID)) return HtmlService.createHtmlOutput('找不到這個課程網站');
  const html = file.getBlob().getDataAsString('UTF-8');
  const title = (html.match(/<title>([^<]*)<\/title>/) || [, '國際教育課程'])[1];
  return HtmlService.createHtmlOutput(html).setTitle(title)
    .addMetaTag('viewport', 'width=device-width, initial-scale=1')
    .setXFrameOptionsMode(HtmlService.XFrameOptionsMode.ALLOWALL);
}

const ACTIONS = {
  ping: () => 'pong',
  publish: publish_,
  upload: upload_,
  listSources: listSources_,
  getFile: getFile_,
  getKnowledge: getKnowledge_,
  saveKnowledge: saveKnowledge_,
};

function json_(obj) {
  return ContentService.createTextOutput(JSON.stringify(obj)).setMimeType(ContentService.MimeType.JSON);
}

/** 第一次部署前在編輯器執行一次，完成雲端硬碟與外部連線授權。 */
function authorize() {
  DriveApp.getFolderById(ROOT_FOLDER_ID).getName();
  DriveApp.getFolderById(REFERENCE_FOLDER_ID).getName();
  UrlFetchApp.fetch('https://www.googleapis.com/drive/v3/about?fields=user', {
    headers: { Authorization: 'Bearer ' + ScriptApp.getOAuthToken() },
  });
}

/**
 * 建立一組課程：一個資料夾放 Google 文件（教案）、Google 簡報（含講稿）、課程網站。
 * p.folder 資料夾名稱、p.name 檔名、p.docx / p.pptx base64、p.site 網站 HTML、p.webapp 本網頁應用程式網址
 */
function publish_(p) {
  const out = childFolder_(DriveApp.getFolderById(ROOT_FOLDER_ID), OUTPUT_FOLDER_NAME);
  const folder = out.createFolder(p.folder);
  shareByLink_(folder);

  const docId = convert_(Utilities.base64Decode(p.docx), DOCX_MIME, GDOC_MIME, p.name + '－教案', folder.getId());
  const slidesId = convert_(Utilities.base64Decode(p.pptx), PPTX_MIME, GSLIDES_MIME, p.name + '－簡報', folder.getId());
  const docUrl = 'https://docs.google.com/document/d/' + docId + '/edit';
  const slidesUrl = 'https://docs.google.com/presentation/d/' + slidesId + '/edit';

  const html = p.site.split('{{SLIDES_ID}}').join(slidesId).split('{{SLIDES_URL}}').join(slidesUrl)
    .split('{{DOC_URL}}').join(docUrl).split('{{FOLDER_URL}}').join(folder.getUrl());
  const site = folder.createFile(Utilities.newBlob(html, 'text/html', p.name + '－課程網站.html'));
  const siteUrl = p.webapp + '?site=' + site.getId();
  folder.createFile(p.name + '－課程網站連結.txt', siteUrl + '\n', 'text/plain');

  return { folderUrl: folder.getUrl(), docUrl: docUrl, slidesUrl: slidesUrl, siteUrl: siteUrl };
}

/** 老師修改後的檔案存到 04-reference。p.name、p.mime、p.base64 */
function upload_(p) {
  const f = DriveApp.getFolderById(REFERENCE_FOLDER_ID)
    .createFile(Utilities.newBlob(Utilities.base64Decode(p.base64), p.mime || 'application/octet-stream', p.name));
  return { id: f.getId(), url: f.getUrl() };
}

/** 列出總資料夾內所有參考資料（不含 AI 產出的課程與學習筆記），供 AI 閱讀。 */
function listSources_() {
  const files = [];
  walk_(DriveApp.getFolderById(ROOT_FOLDER_ID), '', files);
  return files;
}

function walk_(folder, path, files) {
  const it = folder.getFiles();
  while (it.hasNext()) {
    const f = it.next();
    if (f.getName() === KNOWLEDGE_FILE) continue;
    files.push({ id: f.getId(), name: f.getName(), path: path, mime: f.getMimeType(),
      size: f.getSize(), modified: f.getLastUpdated().toISOString() });
  }
  const subs = folder.getFolders();
  while (subs.hasNext()) {
    const s = subs.next();
    if (s.getName() === OUTPUT_FOLDER_NAME) continue;
    walk_(s, path + s.getName() + '/', files);
  }
}

/** 取得檔案內容：Google 文件／簡報轉成 PDF，試算表轉 CSV，其他檔案原樣。 */
function getFile_(p) {
  const f = DriveApp.getFileById(p.id);
  if (!isInside_(f, ROOT_FOLDER_ID)) throw new Error('不在國際教育資料夾內');
  const mime = f.getMimeType();
  let blob;
  if (mime === GDOC_MIME || mime === GSLIDES_MIME) blob = f.getAs('application/pdf');
  else if (mime === GSHEET_MIME) blob = exportSheet_(f.getId());
  else blob = f.getBlob();
  return { name: f.getName(), mime: blob.getContentType(), base64: Utilities.base64Encode(blob.getBytes()) };
}

function exportSheet_(id) {
  const res = UrlFetchApp.fetch('https://www.googleapis.com/drive/v3/files/' + id + '/export?mimeType=text/csv', {
    headers: { Authorization: 'Bearer ' + ScriptApp.getOAuthToken() } });
  return res.getBlob().setContentType('text/csv');
}

function getKnowledge_() {
  const it = DriveApp.getFolderById(ROOT_FOLDER_ID).getFilesByName(KNOWLEDGE_FILE);
  return it.hasNext() ? JSON.parse(it.next().getBlob().getDataAsString('UTF-8')) : { files: {} };
}

function saveKnowledge_(p) {
  const root = DriveApp.getFolderById(ROOT_FOLDER_ID);
  const text = JSON.stringify(p.knowledge, null, 1);
  const it = root.getFilesByName(KNOWLEDGE_FILE);
  if (it.hasNext()) it.next().setContent(text);
  else root.createFile(KNOWLEDGE_FILE, text, 'application/json');
  return true;
}

function childFolder_(parent, name) {
  const it = parent.getFoldersByName(name);
  return it.hasNext() ? it.next() : parent.createFolder(name);
}

/** 知道連結的人可檢視；學校網域禁止對外分享時改成網域內可檢視。 */
function shareByLink_(folder) {
  try {
    folder.setSharing(DriveApp.Access.ANYONE_WITH_LINK, DriveApp.Permission.VIEW);
  } catch (e) {
    try { folder.setSharing(DriveApp.Access.DOMAIN_WITH_LINK, DriveApp.Permission.VIEW); } catch (e2) { /* 維持預設 */ }
  }
}

function isInside_(file, folderId) {
  const queue = [];
  const seen = {};
  const it = file.getParents();
  while (it.hasNext()) queue.push(it.next());
  while (queue.length) {
    const f = queue.shift();
    const id = f.getId();
    if (id === folderId) return true;
    if (seen[id]) continue;
    seen[id] = true;
    const up = f.getParents();
    while (up.hasNext()) queue.push(up.next());
  }
  return false;
}

/** 用 Drive API 上傳 Office 檔並轉成 Google 格式（不需進階服務）。 */
function convert_(bytes, fromMime, toMime, name, folderId) {
  const boundary = 'ielesson' + Date.now();
  const meta = { name: name, mimeType: toMime, parents: [folderId] };
  const head = Utilities.newBlob(
    '--' + boundary + '\r\nContent-Type: application/json; charset=UTF-8\r\n\r\n' +
    JSON.stringify(meta) + '\r\n--' + boundary + '\r\nContent-Type: ' + fromMime + '\r\n\r\n').getBytes();
  const tail = Utilities.newBlob('\r\n--' + boundary + '--').getBytes();
  const res = UrlFetchApp.fetch(
    'https://www.googleapis.com/upload/drive/v3/files?uploadType=multipart&supportsAllDrives=true&fields=id', {
      method: 'post',
      contentType: 'multipart/related; boundary=' + boundary,
      payload: head.concat(bytes).concat(tail),
      headers: { Authorization: 'Bearer ' + ScriptApp.getOAuthToken() },
      muteHttpExceptions: true,
    });
  if (res.getResponseCode() !== 200) {
    throw new Error('轉成 Google 格式失敗（' + res.getResponseCode() + '）：' + res.getContentText());
  }
  return JSON.parse(res.getContentText()).id;
}
