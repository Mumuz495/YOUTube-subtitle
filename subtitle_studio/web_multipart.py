"""Parse multipart/form-data uploads for the local HTTP server."""

from __future__ import annotations

import cgi
import io
from dataclasses import dataclass, field


@dataclass
class UploadedFile:
    filename: str
    data: bytes
    content_type: str = "application/octet-stream"


@dataclass
class MultipartForm:
    fields: dict[str, str] = field(default_factory=dict)
    files: dict[str, UploadedFile] = field(default_factory=dict)


def parse_multipart_form(
    content_type: str,
    body: bytes,
    *,
    max_bytes: int,
) -> MultipartForm:
    if len(body) > max_bytes:
        limit_mb = max_bytes / 1024 / 1024
        raise ValueError(
            f"PDF 文件超过上传上限（最大 {limit_mb:.0f} MB）。"
            "请压缩 PDF、拆分文件，或调大 PDF_MAX_UPLOAD_BYTES。"
        )

    if "multipart/form-data" not in str(content_type or "").lower():
        raise ValueError("请使用 multipart/form-data 上传 PDF。")

    environ = {
        "REQUEST_METHOD": "POST",
        "CONTENT_TYPE": content_type,
        "CONTENT_LENGTH": str(len(body)),
    }
    form = cgi.FieldStorage(
        fp=io.BytesIO(body),
        environ=environ,
        keep_blank_values=True,
    )

    fields: dict[str, str] = {}
    files: dict[str, UploadedFile] = {}
    if not form.list:
        return MultipartForm(fields=fields, files=files)

    for item in form.list:
        name = str(item.name or "").strip()
        if not name:
            continue
        if item.filename:
            files[name] = UploadedFile(
                filename=str(item.filename),
                data=item.file.read() if item.file else b"",
                content_type=str(item.type or "application/octet-stream"),
            )
        else:
            fields[name] = str(item.value or "")

    return MultipartForm(fields=fields, files=files)


def pick_uploaded_pdf(form: MultipartForm) -> UploadedFile | None:
    for key in ("pdf", "pdf_file", "file"):
        uploaded = form.files.get(key)
        if uploaded and uploaded.data:
            return uploaded
    for uploaded in form.files.values():
        if uploaded.data:
            return uploaded
    return None
