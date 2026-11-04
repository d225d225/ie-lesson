"""Apps Script 橋接（雲端硬碟）與檔案轉成 AI 可讀的內容。"""
from __future__ import annotations

import base64
import io

import requests

IMAGE_MIMES = {"image/jpeg", "image/png", "image/gif", "image/webp"}
MAX_INLINE = 18 * 1024 * 1024  # Gemini 單次請求內嵌檔案上限約 20MB


class DriveError(RuntimeError):
    pass


class Drive:
    def __init__(self, url: str, secret: str):
        self.url = url
        self.secret = secret

    def _call(self, action: str, timeout: int = 300, **params):
        try:
            r = requests.post(self.url, json={"secret": self.secret, "action": action, **params}, timeout=timeout)
        except requests.RequestException as e:
            raise DriveError(f"連不上雲端硬碟服務：{e}") from e
        try:
            body = r.json()
        except ValueError as e:
            raise DriveError(f"雲端硬碟服務回傳格式錯誤（HTTP {r.status_code}），請確認 Apps Script 部署的存取權是「任何人」。") from e
        if not body.get("ok"):
            raise DriveError(f"雲端硬碟服務錯誤：{body.get('error')}")
        return body.get("result")

    def ping(self):
        return self._call("ping", timeout=30)

    def publish(self, folder: str, name: str, docx: bytes, pptx: bytes, site: str) -> dict:
        return self._call("publish", folder=folder, name=name, site=site, webapp=self.url,
                          docx=base64.b64encode(docx).decode("ascii"), pptx=base64.b64encode(pptx).decode("ascii"))

    def upload(self, name: str, mime: str, data: bytes) -> dict:
        return self._call("upload", name=name, mime=mime, base64=base64.b64encode(data).decode("ascii"))

    def sources(self) -> list[dict]:
        return self._call("listSources", timeout=120)

    def get_file(self, file_id: str) -> tuple[str, str, bytes]:
        r = self._call("getFile", id=file_id)
        return r["name"], r["mime"], base64.b64decode(r["base64"])

    def knowledge(self) -> dict:
        return self._call("getKnowledge", timeout=60)

    def save_knowledge(self, knowledge: dict):
        return self._call("saveKnowledge", knowledge=knowledge, timeout=60)


def to_blocks(name: str, mime: str, data: bytes) -> list[dict]:
    """把一個檔案轉成 AI 可讀的內容：PDF／圖片保留原檔，Word／PPT 取出文字；讀不了回傳空清單。"""
    low = name.lower()
    if mime == "application/pdf" or low.endswith(".pdf"):
        return [{"name": name, "mime": "application/pdf", "data": data}] if len(data) <= MAX_INLINE else []
    if mime in IMAGE_MIMES:
        return [{"name": name, "mime": mime, "data": data}] if len(data) <= MAX_INLINE else []
    text = _text(low, data)
    return [{"name": name, "text": text}] if text.strip() else []


def _text(low: str, data: bytes) -> str:
    if low.endswith(".docx"):
        from docx import Document
        doc = Document(io.BytesIO(data))
        parts = [p.text for p in doc.paragraphs]
        for t in doc.tables:
            for row in t.rows:
                parts.append(" | ".join(c.text for c in row.cells))
        return "\n".join(parts)
    if low.endswith(".pptx"):
        from pptx import Presentation
        out = []
        for i, s in enumerate(Presentation(io.BytesIO(data)).slides, 1):
            out.append(f"--- 第 {i} 張 ---")
            out += [sh.text_frame.text for sh in s.shapes if sh.has_text_frame]
            if s.has_notes_slide:
                out.append("講稿：" + s.notes_slide.notes_text_frame.text)
        return "\n".join(out)
    if low.endswith((".txt", ".md", ".csv", ".html", ".htm", ".json")):
        return data.decode("utf-8", errors="ignore")
    return ""


def guess_mime(name: str, given: str | None) -> str:
    low = name.lower()
    table = {".pdf": "application/pdf", ".png": "image/png", ".jpg": "image/jpeg", ".jpeg": "image/jpeg",
             ".gif": "image/gif", ".webp": "image/webp",
             ".docx": "application/vnd.openxmlformats-officedocument.wordprocessingml.document",
             ".pptx": "application/vnd.openxmlformats-officedocument.presentationml.presentation"}
    for ext, m in table.items():
        if low.endswith(ext):
            return m
    return given or "application/octet-stream"
