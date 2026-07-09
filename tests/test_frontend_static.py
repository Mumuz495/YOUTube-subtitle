import unittest
from pathlib import Path


ROOT = Path(__file__).resolve().parents[1]


class FrontendStaticTests(unittest.TestCase):
    def test_immersive_translate_button_exists(self):
        html = (ROOT / "static" / "index.html").read_text(encoding="utf-8")

        self.assertIn('id="immersive-translate"', html)
        self.assertIn('type="submit"', html)
        self.assertIn("沉浸式翻译", html)

    def test_immersive_translate_submit_forces_translation(self):
        script = (ROOT / "static" / "app.js").read_text(encoding="utf-8")

        self.assertIn('submitter?.id === "immersive-translate"', script)
        self.assertIn("translate: isImmersive || translateCheckbox.checked", script)
        self.assertIn("translateCheckbox.checked = true", script)

    def test_study_sheet_has_vocab_sidebar_and_context_menu_annotation(self):
        script = (ROOT / "static" / "app.js").read_text(encoding="utf-8")
        styles = (ROOT / "static" / "styles.css").read_text(encoding="utf-8")

        self.assertIn("renderStudySheet", script)
        self.assertIn('addEventListener("contextmenu"', script)
        self.assertIn('fetch("/api/vocab"', script)
        self.assertIn("生词合集", script)
        self.assertIn(".study-sheet", styles)
        self.assertIn(".vocab-sidebar", styles)

    def test_study_sheet_can_render_media_player_and_article_source(self):
        script = (ROOT / "static" / "app.js").read_text(encoding="utf-8")
        styles = (ROOT / "static" / "styles.css").read_text(encoding="utf-8")

        self.assertIn("renderMediaPanel", script)
        self.assertIn("media_embed_url", script)
        self.assertIn("study-media", script)
        self.assertIn("sheet-row", script)
        self.assertIn("paragraph-vocab-list", script)
        self.assertIn("paragraphIndex", script)
        self.assertIn("sheet-meta", script)
        self.assertIn("题目：", script)
        self.assertIn("作者：", script)
        self.assertIn("网址：", script)
        self.assertIn("source_type", script)
        self.assertIn(".study-media", styles)
        self.assertIn(".transcript.has-media", styles)
        self.assertIn(".transcript.has-media .study-sheet", styles)
        self.assertIn(".sheet-row", styles)
        self.assertIn(".paragraph-vocab", styles)
        self.assertIn(".sheet-meta-row", styles)
        self.assertIn("position: sticky", styles)
        self.assertIn("height: calc(100vh - 24px)", styles)
        self.assertIn("height: clamp(190px, 34vh, 315px)", styles)
        self.assertIn("height: calc(100vh - 16px)", styles)
        self.assertIn('tabindex="0"', script)

    def test_study_sheet_can_be_exported_as_html(self):
        script = (ROOT / "static" / "app.js").read_text(encoding="utf-8")
        styles = (ROOT / "static" / "styles.css").read_text(encoding="utf-8")

        self.assertIn('id="export-study-sheet"', script)
        self.assertIn('id="export-format"', script)
        self.assertIn("exportStudySheet", script)
        self.assertIn("item.full || item.preview", script)
        self.assertIn("study-sheet.html", script)
        self.assertIn('fetch("/api/export-study-sheet"', script)
        self.assertIn("DOCX", script)
        self.assertIn("PDF", script)
        self.assertIn("URL.createObjectURL", script)
        self.assertIn("triggerStudySheetDownload", script)
        self.assertIn("已生成", script)
        self.assertIn("download", script)
        self.assertIn(".export-choice", styles)

    def test_study_sheet_supports_speech_controls(self):
        script = (ROOT / "static" / "app.js").read_text(encoding="utf-8")
        styles = (ROOT / "static" / "styles.css").read_text(encoding="utf-8")

        self.assertIn("speechSynthesis", script)
        self.assertIn("SpeechSynthesisUtterance", script)
        self.assertIn("renderTtsControls", script)
        self.assertIn('id="voice-profile"', script)
        self.assertIn('id="voice-rate"', script)
        self.assertIn('data-speak="all"', script)
        self.assertIn('data-speak="paragraph"', script)
        self.assertIn('data-speak="word"', script)
        self.assertIn("chooseVoice", script)
        self.assertIn("stopSpeech", script)
        self.assertIn('fetch("/api/tts"', script)
        self.assertIn("splitSpeechText", script)
        self.assertIn("playAudioUrl", script)
        self.assertIn("new Audio", script)
        self.assertIn(".tts-controls", styles)
        self.assertIn(".speak-button", styles)
        self.assertIn(".is-speaking", styles)

    def test_pdf_upload_can_be_sent_for_reading(self):
        html = (ROOT / "static" / "index.html").read_text(encoding="utf-8")
        script = (ROOT / "static" / "app.js").read_text(encoding="utf-8")
        styles = (ROOT / "static" / "styles.css").read_text(encoding="utf-8")

        self.assertIn('id="pdf-file"', html)
        self.assertIn('accept="application/pdf,.pdf"', html)
        self.assertIn("PDF", html)
        self.assertIn('fetch("/api/pdf-upload"', script)
        self.assertIn("new FormData()", script)
        self.assertIn('formData.append("pdf"', script)
        self.assertIn('fetch("/api/config"', script)
        self.assertIn("source_type === \"pdf\"", script)
        self.assertIn(".pdf-upload", styles)

    def test_pdf_upload_uses_configured_size_limit(self):
        script = (ROOT / "static" / "app.js").read_text(encoding="utf-8")

        self.assertIn("pdfMaxUploadBytes", script)
        self.assertIn("pdfMaxUploadLabel", script)
        self.assertIn("pdfFile.size > pdfMaxUploadBytes", script)
        self.assertIn("PDF 文件太大", script)
        self.assertIn("OCR", script)


if __name__ == "__main__":
    unittest.main()
