import unittest

from subtitle_studio.web_multipart import parse_multipart_form, pick_uploaded_pdf


def build_multipart_body(
    *,
    fields: dict[str, str] | None = None,
    files: dict[str, tuple[str, bytes, str]] | None = None,
    boundary: str = "----SubtitleStudioBoundary",
) -> tuple[bytes, str]:
    fields = fields or {}
    files = files or {}
    chunks: list[bytes] = []
    for name, value in fields.items():
        chunks.append(f"--{boundary}\r\n".encode("utf-8"))
        chunks.append(f'Content-Disposition: form-data; name="{name}"\r\n\r\n'.encode("utf-8"))
        chunks.append(f"{value}\r\n".encode("utf-8"))
    for name, (filename, content, content_type) in files.items():
        chunks.append(f"--{boundary}\r\n".encode("utf-8"))
        chunks.append(
            f'Content-Disposition: form-data; name="{name}"; filename="{filename}"\r\n'.encode("utf-8")
        )
        chunks.append(f"Content-Type: {content_type}\r\n\r\n".encode("utf-8"))
        chunks.append(content)
        chunks.append(b"\r\n")
    chunks.append(f"--{boundary}--\r\n".encode("utf-8"))
    return b"".join(chunks), f"multipart/form-data; boundary={boundary}"


class WebMultipartTests(unittest.TestCase):
    def test_parse_multipart_form_extracts_fields_and_files(self):
        body, content_type = build_multipart_body(
            fields={"output": "output", "translate": "true"},
            files={"pdf": ("sample.pdf", b"%PDF-1.4 test", "application/pdf")},
        )

        form = parse_multipart_form(content_type, body, max_bytes=1024 * 1024)
        uploaded = pick_uploaded_pdf(form)

        self.assertEqual(form.fields["output"], "output")
        self.assertEqual(form.fields["translate"], "true")
        self.assertIsNotNone(uploaded)
        self.assertEqual(uploaded.filename, "sample.pdf")
        self.assertEqual(uploaded.data, b"%PDF-1.4 test")

    def test_parse_multipart_form_rejects_oversized_body(self):
        body, content_type = build_multipart_body(
            files={"pdf": ("big.pdf", b"x" * 20, "application/pdf")},
        )

        with self.assertRaisesRegex(ValueError, "超过上传上限"):
            parse_multipart_form(content_type, body, max_bytes=10)


if __name__ == "__main__":
    unittest.main()
