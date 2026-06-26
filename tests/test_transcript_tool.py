import json
import os
import tempfile
import unittest
import zipfile
from pathlib import Path
from unittest.mock import patch

from transcript_tool import (
    TranscriptSnippet,
    analyze_vocab_term,
    build_process_result,
    build_bilingual_text,
    extract_video_id,
    fetch_article,
    fetch_video_metadata,
    format_timestamp,
    generate_tts_audio,
    get_deepseek_api_key,
    is_single_video,
    process_url,
    process_video,
    save_outputs,
    save_study_sheet_html,
)


class TranscriptToolTests(unittest.TestCase):
    def test_extract_video_id_handles_common_youtube_urls(self):
        cases = {
            "https://www.youtube.com/watch?v=dQw4w9WgXcQ": "dQw4w9WgXcQ",
            "https://youtu.be/dQw4w9WgXcQ?t=42": "dQw4w9WgXcQ",
            "https://www.youtube.com/shorts/dQw4w9WgXcQ": "dQw4w9WgXcQ",
            "https://www.youtube.com/embed/dQw4w9WgXcQ": "dQw4w9WgXcQ",
        }

        for url, expected in cases.items():
            with self.subTest(url=url):
                self.assertEqual(extract_video_id(url), expected)
                self.assertTrue(is_single_video(url))

    def test_extract_video_id_rejects_channel_urls(self):
        self.assertIsNone(extract_video_id("https://www.youtube.com/@somecreator/videos"))
        self.assertFalse(is_single_video("https://www.youtube.com/@somecreator/videos"))

    def test_format_timestamp_uses_hh_mm_ss_milliseconds(self):
        self.assertEqual(format_timestamp(0), "00:00:00.000")
        self.assertEqual(format_timestamp(65.4321), "00:01:05.432")
        self.assertEqual(format_timestamp(3661.7), "01:01:01.700")

    def test_build_bilingual_text_keeps_timestamps_and_line_pairs(self):
        snippets = [
            TranscriptSnippet(text="I thought not.", start=4.0, duration=2.1, text_zh="我想没有。"),
            TranscriptSnippet(text="It is a story.", start=7.4, duration=1.2, text_zh="这是一个故事。"),
        ]

        text = build_bilingual_text(snippets)

        self.assertIn("[00:00:04.000]", text)
        self.assertIn("EN: I thought not.", text)
        self.assertIn("ZH: 我想没有。", text)
        self.assertIn("EN: It is a story.", text)

    def test_save_outputs_writes_json_txt_and_practice_files(self):
        snippets = [
            TranscriptSnippet(text="Hello there.", start=0, duration=1.5, text_zh="你好。"),
            TranscriptSnippet(text="General Kenobi.", start=1.5, duration=1.5, text_zh="肯诺比将军。"),
        ]

        with tempfile.TemporaryDirectory() as tmp:
            written = save_outputs("dQw4w9WgXcQ", snippets, tmp)
            out_dir = Path(tmp) / "dQw4w9WgXcQ"

            self.assertEqual(written["json"], str(out_dir / "transcript.json"))
            self.assertEqual((out_dir / "transcript.txt").read_text(encoding="utf-8").splitlines(), ["Hello there.", "General Kenobi."])
            self.assertEqual((out_dir / "transcript_zh.txt").read_text(encoding="utf-8").splitlines(), ["你好。", "肯诺比将军。"])
            self.assertIn("EN: Hello there.", (out_dir / "practice_bilingual.txt").read_text(encoding="utf-8"))

            data = json.loads((out_dir / "transcript.json").read_text(encoding="utf-8"))
            self.assertEqual(data[0]["text"], "Hello there.")
            self.assertEqual(data[0]["text_zh"], "你好。")

    def test_get_deepseek_api_key_reads_env_file_when_environment_is_empty(self):
        with tempfile.TemporaryDirectory() as tmp:
            env_file = Path(tmp) / ".env"
            env_file.write_text("DEEPSEEK_API_KEY=sk-from-env-file\n", encoding="utf-8")

            with patch.dict(os.environ, {}, clear=True):
                self.assertEqual(get_deepseek_api_key(env_file), "sk-from-env-file")

    def test_get_deepseek_api_key_prefers_environment_variable(self):
        with tempfile.TemporaryDirectory() as tmp:
            env_file = Path(tmp) / ".env"
            env_file.write_text("DEEPSEEK_API_KEY=sk-from-env-file\n", encoding="utf-8")

            with patch.dict(os.environ, {"DEEPSEEK_API_KEY": "sk-from-process"}, clear=True):
                self.assertEqual(get_deepseek_api_key(env_file), "sk-from-process")

    def test_process_video_uses_existing_bilingual_output_for_translate_preview(self):
        snippets = [
            TranscriptSnippet(text="Hello.", start=0, duration=1, text_zh="你好。"),
        ]

        with tempfile.TemporaryDirectory() as tmp:
            save_outputs("dQw4w9WgXcQ", snippets, tmp)

            with patch("transcript_tool.fetch_transcript_for_video", side_effect=AssertionError("should use cache")):
                result = process_video("dQw4w9WgXcQ", tmp, translate=True, api_key="sk-test")

            self.assertTrue(result["ok"])
            self.assertEqual(result["preview"][0]["text"], "Hello.")
            self.assertEqual(result["preview"][0]["text_zh"], "你好。")

    def test_build_process_result_includes_full_transcript_for_study_sheet(self):
        snippets = [
            TranscriptSnippet(text=f"Line {index}", start=index, duration=1, text_zh=f"第 {index} 行")
            for index in range(100)
        ]

        result = build_process_result("dQw4w9WgXcQ", snippets, {"json": "x.json"})

        self.assertEqual(len(result["preview"]), 80)
        self.assertEqual(len(result["full"]), 100)
        self.assertEqual(result["full"][-1]["text"], "Line 99")

    def test_build_process_result_includes_youtube_embed_url(self):
        snippets = [TranscriptSnippet(text="Hello.", start=0, duration=1, text_zh="你好。")]

        result = build_process_result("dQw4w9WgXcQ", snippets, {"json": "x.json"})

        self.assertEqual(result["source_type"], "video")
        self.assertEqual(result["media_embed_url"], "https://www.youtube.com/embed/dQw4w9WgXcQ")

    def test_fetch_article_extracts_public_article_text(self):
        class FakeResponse:
            text = """
            <html>
              <head><title>Example Article</title><meta name="author" content="Jane Author"></head>
              <body>
                <nav>Navigation</nav>
                <article>
                  <h1>The Tribute System</h1>
                  <p>First useful paragraph with enough words to keep.</p>
                  <p>Second useful paragraph with enough words to keep.</p>
                </article>
              </body>
            </html>
            """
            encoding = "utf-8"

            def raise_for_status(self):
                return None

        with patch("transcript_tool.requests.get", return_value=FakeResponse()):
            article = fetch_article("https://example.com/article")

        self.assertEqual(article["title"], "The Tribute System")
        self.assertEqual(article["author"], "Jane Author")
        self.assertEqual(len(article["paragraphs"]), 2)

    def test_fetch_video_metadata_reads_youtube_oembed(self):
        class FakeResponse:
            def raise_for_status(self):
                return None

            def json(self):
                return {"title": "A Useful Talk", "author_name": "TED"}

        with patch("transcript_tool.requests.get", return_value=FakeResponse()):
            metadata = fetch_video_metadata("dQw4w9WgXcQ")

        self.assertEqual(metadata["title"], "A Useful Talk")
        self.assertEqual(metadata["author"], "TED")
        self.assertEqual(metadata["source_url"], "https://www.youtube.com/watch?v=dQw4w9WgXcQ")

    def test_process_url_routes_non_youtube_urls_to_article_mode(self):
        article = {
            "title": "An Article",
            "author": "Writer",
            "paragraphs": ["Paragraph one.", "Paragraph two."],
        }

        with tempfile.TemporaryDirectory() as tmp:
            with patch("transcript_tool.fetch_article", return_value=article):
                with patch("transcript_tool.translate_batch", return_value=["第一段。", "第二段。"]):
                    with patch.dict(os.environ, {"DEEPSEEK_API_KEY": "sk-test"}, clear=True):
                        result = process_url("https://example.com/article", output_root=tmp, translate=True)

        item = result["results"][0]
        self.assertTrue(item["ok"])
        self.assertEqual(item["source_type"], "article")
        self.assertEqual(item["title"], "An Article")
        self.assertEqual(item["full"][0]["text"], "Paragraph one.")
        self.assertEqual(item["full"][0]["text_zh"], "第一段。")

    def test_analyze_vocab_term_returns_structured_definition(self):
        class FakeResponse:
            def raise_for_status(self):
                return None

            def json(self):
                return {
                    "choices": [
                        {
                            "message": {
                                "content": '{"term":"tardiness","part_of_speech":"n.","definition_zh":"迟到；拖延","example_zh":"偶尔迟到"}'
                            }
                        }
                    ]
                }

        with patch("transcript_tool.requests.post", return_value=FakeResponse()) as post:
            result = analyze_vocab_term("tardiness", "occasional tardiness", "sk-test")

        self.assertEqual(result["term"], "tardiness")
        self.assertEqual(result["part_of_speech"], "n.")
        self.assertEqual(result["definition_zh"], "迟到；拖延")
        self.assertEqual(result["example_zh"], "偶尔迟到")
        self.assertIn("Authorization", post.call_args.kwargs["headers"])

    def test_generate_tts_audio_rejects_empty_text(self):
        with tempfile.TemporaryDirectory() as tmp:
            with self.assertRaises(ValueError):
                generate_tts_audio("   ", output_root=tmp)

    def test_save_study_sheet_html_writes_export_file(self):
        with tempfile.TemporaryDirectory() as tmp:
            path = save_study_sheet_html("<!doctype html><html><body>精读稿</body></html>", tmp)

            written = Path(path)
            self.assertEqual(written.name, "study-sheet.html")
            self.assertTrue(written.exists())
            self.assertIn("精读稿", written.read_text(encoding="utf-8"))

    def test_save_study_sheet_html_writes_docx_and_pdf_formats(self):
        html = """
        <!doctype html>
        <html><body>
          <section class="study-sheet">
            <div class="sheet-brand">Study Sheet</div>
            <h3>双语精读稿</h3>
            <p>视频：abc123</p>
            <section class="sheet-line">
              <p class="sheet-en">Hello. Are you ready?</p>
              <p class="sheet-zh">你好。准备好了吗？</p>
            </section>
            <aside class="vocab-sidebar">
              <h3>生词合集</h3>
              <article class="vocab-card"><span class="vocab-term">ready</span><p>adj. 准备好的</p></article>
            </aside>
          </section>
        </body></html>
        """
        with tempfile.TemporaryDirectory() as tmp:
            docx_path = Path(save_study_sheet_html(html, tmp, export_format="docx"))
            pdf_path = Path(save_study_sheet_html(html, tmp, export_format="pdf"))

            self.assertEqual(docx_path.suffix, ".docx")
            self.assertTrue(docx_path.exists())
            self.assertEqual(pdf_path.suffix, ".pdf")
            self.assertTrue(pdf_path.exists())
            self.assertEqual(pdf_path.read_bytes()[:4], b"%PDF")

    def test_study_sheet_export_includes_title_author_and_url_metadata(self):
        html = """
        <!doctype html>
        <html><body>
          <section class="study-sheet">
            <div class="sheet-brand">Study Sheet</div>
            <header class="sheet-titlebar">
              <h3>A Useful Talk</h3>
              <dl class="sheet-meta">
                <div class="sheet-meta-row"><dt>题目：</dt><dd>A Useful Talk</dd></div>
                <div class="sheet-meta-row"><dt>作者：</dt><dd>TED</dd></div>
                <div class="sheet-meta-row"><dt>网址：</dt><dd>https://www.youtube.com/watch?v=abc123</dd></div>
              </dl>
            </header>
            <section class="sheet-row">
              <article class="sheet-line">
                <p class="sheet-en">Hello.</p>
                <p class="sheet-zh">你好。</p>
              </article>
              <aside><article class="vocab-card"><span class="vocab-term">hello</span><p>int. 你好</p></article></aside>
            </section>
          </section>
        </body></html>
        """
        with tempfile.TemporaryDirectory() as tmp:
            docx_path = Path(save_study_sheet_html(html, tmp, export_format="docx"))

            with zipfile.ZipFile(docx_path) as archive:
                document_xml = "\n".join(
                    archive.read(name).decode("utf-8", errors="ignore")
                    for name in archive.namelist()
                    if name.endswith((".xml", ".html"))
                )

        self.assertIn("A Useful Talk", document_xml)
        self.assertIn("TED", document_xml)
        self.assertIn("https://www.youtube.com/watch?v=abc123", document_xml)

    def test_study_sheet_docx_preserves_highlight_and_side_vocab(self):
        html = """
        <!doctype html>
        <html><body>
          <section class="study-sheet">
            <div class="sheet-brand">Study Sheet</div>
            <h3>双语精读稿</h3>
            <section class="sheet-row">
              <article class="sheet-line">
                <p class="sheet-en">Today we're <mark class="vocab-mark">going</mark> to be <mark class="vocab-mark">learning</mark>.</p>
                <p class="sheet-zh">今天我们将要学习。</p>
              </article>
              <aside class="paragraph-vocab">
                <article class="vocab-card"><span class="vocab-term">going</span><p>v. 将要</p><small>今天我们将会学习。</small></article>
                <article class="vocab-card"><span class="vocab-term">learning</span><p>v. 学习</p></article>
              </aside>
            </section>
          </section>
        </body></html>
        """
        with tempfile.TemporaryDirectory() as tmp:
            docx_path = Path(save_study_sheet_html(html, tmp, export_format="docx"))

            with zipfile.ZipFile(docx_path) as archive:
                document_xml = "\n".join(
                    archive.read(name).decode("utf-8", errors="ignore")
                    for name in archive.namelist()
                    if name.endswith((".xml", ".html"))
                )

        self.assertIn("going", document_xml)
        self.assertIn("learning", document_xml)
        self.assertIn("vocab-mark", document_xml)
        self.assertIn("vocab-card", document_xml)
        self.assertIn("v. 将要", document_xml)


if __name__ == "__main__":
    unittest.main()
