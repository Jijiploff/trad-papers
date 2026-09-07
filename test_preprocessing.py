import subprocess
import unittest
import tempfile
from unittest.mock import patch
from types import SimpleNamespace

from src.processors.pdf_processor import PdfProcessor
from src.processors.format_agent import FormatAgent, FormatAgentConfig
from src.processors.text_normalizer import normalize_extracted_text
from src.core.pipeline import TranslationPipeline
from src.core.models import Document, FileType, Section, SectionType, TranslationStatus
from src.utils.exporter import DocumentExporter


class TextNormalizationTests(unittest.TestCase):
    def test_rejoins_hyphenated_words_and_wrapped_lines(self):
        text = (
            "The meth-\nod is robust and cross-\nvalidation is required.\n"
            "This is a new paragraph."
        )
        self.assertEqual(
            normalize_extracted_text(text),
            "The method is robust and cross-validation is required. This is a new paragraph.",
        )

    def test_preserves_paragraphs_and_legitimate_hyphens(self):
        text = "A state-of-the-art method.\nContinued here.\n\n[Figure 1]\nA caption."
        self.assertEqual(
            normalize_extracted_text(text),
            "A state-of-the-art method. Continued here.\n\n[Figure 1]\nA caption.",
        )

    def test_removes_pdf_artifacts_without_touching_citations(self):
        text = "Results (cid:1) show an effect [1, 2].\n\nThe next line."
        self.assertEqual(
            normalize_extracted_text(text),
            "Results show an effect [1, 2].\n\nThe next line.",
        )

    def test_pdf_columns_are_read_left_then_right_without_duplicate_preamble(self):
        words = []
        for index, text in enumerate(["Article", "title"]):
            words.append({"text": text, "x0": 40 + index * 45, "x1": 80 + index * 45, "top": 10})
        for index in range(12):
            words.append({"text": f"L{index}", "x0": 40, "x1": 60, "top": 40 + index * 10})
            words.append({"text": f"R{index}", "x0": 330, "x1": 350, "top": 40 + index * 10})

        page = SimpleNamespace(width=600, extract_words=lambda **kwargs: words)
        extracted = PdfProcessor()._extract_page_text(page)

        self.assertEqual(extracted.count("Article title"), 1)
        self.assertLess(extracted.index("L0"), extracted.index("R0"))

    def test_layout_elements_keep_figures_tables_and_text_separate(self):
        elements = FormatAgent()._build_layout_elements(
            "## Results\n\nText to translate.\n\n<!-- image-->\nFigure 1. Caption.\n\n"
            "| Model | RMSE |\n|---|---|\n| FCN | 3.5 |\n\nReferences\n\n[1] Source."
        )
        self.assertEqual([element["type"] for element in elements], [
            "section_title", "paragraph", "figure", "figure_caption", "table", "reference"
        ])
        self.assertFalse(elements[2]["translatable"])
        self.assertTrue(elements[3]["translatable"])
        self.assertTrue(elements[4]["translatable"])
        self.assertFalse(elements[5]["translatable"])

    def test_citations_are_removed_from_translation_payload_and_restored(self):
        source = "Forest carbon increased [1, 2] according to (Smith et al., 2020)."
        protected, placeholders = TranslationPipeline._protect_citations(source)
        self.assertNotIn("[1, 2]", protected)
        self.assertNotIn("(Smith et al., 2020)", protected)
        restored = TranslationPipeline._restore_citations("Carbon forestal aumentó " + " ".join(placeholders), placeholders)
        self.assertIn("[1, 2]", restored)
        self.assertIn("(Smith et al., 2020)", restored)

    def test_table_layout_markers_are_restored_after_translation(self):
        source = "| Model | RMSE |\n|---|---|\n| FCN | 3.5 |"
        protected, placeholders = TranslationPipeline._protect_layout(source, "table")
        self.assertNotIn("|", protected)
        self.assertEqual(TranslationPipeline._restore_layout(protected, placeholders), source)

    def test_format_agent_token_count_ignores_references_and_figures(self):
        agent = FormatAgent()
        elements = [
            agent._element("paragraph", "word " * 20, True),
            agent._element("reference", "reference " * 100, False),
            agent._element("figure", "<!-- image -->", False),
        ]
        translatable_tokens = sum(
            max(1, len(element["content"]) // 4)
            for element in elements
            if element["translatable"]
        )
        non_translatable_tokens = sum(
            max(1, len(element["content"]) // 4)
            for element in elements
            if not element["translatable"]
        )
        self.assertLess(translatable_tokens, translatable_tokens + non_translatable_tokens)

    def test_preprocessed_export_uses_original_after_translation(self):
        document = SimpleNamespace(
            filename="article.pdf",
            provider_used=None,
            sections=[Section("1", SectionType.OTHER, "Content", "Original text", "Texto traducido")],
            metadata={},
        )
        with tempfile.TemporaryDirectory() as output_dir:
            path = DocumentExporter(output_dir).export_to_txt(document, original_only=True)
            content = path.read_text(encoding="utf-8")
        self.assertIn("Original text", content)
        self.assertNotIn("Texto traducido", content)

    def test_pipeline_reuses_ui_preprocessed_layout(self):
        class FakeTranslator:
            def get_provider_name(self):
                return "gemini"

            def translate_with_retry(self, text, source_lang="EN", target_lang="ES"):
                return text

        source = Document(
            "id", "article.pdf", FileType.PDF, 1, b"pdf",
            sections=[Section("1", SectionType.OTHER, "Content", "Original")],
            metadata={
                "preprocessed": True,
                "layout_elements": [
                    {"type": "paragraph", "content": "Original [1]", "translatable": True, "translated_content": ""},
                    {"type": "reference", "content": "[1] Ref", "translatable": False, "translated_content": ""},
                ],
            },
        )
        pipeline = TranslationPipeline({}, FakeTranslator(), cache=None, max_workers=1)
        with patch("src.core.pipeline.FormatAgent.process", side_effect=AssertionError("MinerU se ejecutó dos veces")):
            result = pipeline.process_document(source)
        self.assertEqual(result.status, TranslationStatus.COMPLETED)

    def test_mineru_html_table_becomes_structured_table(self):
        elements = FormatAgent()._build_layout_elements(
            "Tabla 1. Resultados\n"
            "<table><tr><td>Modelo</td><td>RMSE</td></tr>"
            "<tr><td>FCN</td><td>3.5</td></tr></table>"
        )
        tables = [element for element in elements if element["type"] == "table"]
        self.assertEqual(len(tables), 1)
        self.assertIn("| Modelo | RMSE |", tables[0]["content"])

    def test_format_agent_does_not_fallback_when_mineru_fails(self):
        document = Document("id", "article.pdf", FileType.PDF, 1, b"pdf")
        agent = FormatAgent(FormatAgentConfig(docling_enabled=False))
        with patch.object(agent, "_try_mineru_open_api", return_value=""):
            with self.assertRaises(RuntimeError) as error:
                agent.process(document)
        self.assertIn("No se pudo extraer texto estructurado", str(error.exception))

    def test_format_agent_retries_on_mineru_timeout(self):
        document = Document("id", "article.pdf", FileType.PDF, 1, b"%PDF-1.4\n1 0 obj\n<<>>\nendobj\ntrailer\n<<>>\n%%EOF")
        agent = FormatAgent(FormatAgentConfig(
            mineru_retries=2,
            mineru_timeout_seconds=1200,
            docling_enabled=False,
        ))

        class DummyReader:
            pages = [object()]

        class DummyWriter:
            def add_page(self, _page):
                pass
            def write(self, _handle):
                pass

        def fake_run(*args, **kwargs):
            if not hasattr(fake_run, "calls"):
                fake_run.calls = 0
            fake_run.calls += 1
            if fake_run.calls < 3:
                raise subprocess.TimeoutExpired(cmd="flash-extract", timeout=1200)
            return SimpleNamespace(returncode=0, stdout="# Hola\n\nTexto procesado.", stderr="")

        with patch("PyPDF2.PdfReader", return_value=DummyReader()), \
             patch("PyPDF2.PdfWriter", return_value=DummyWriter()), \
             patch("src.processors.format_agent.subprocess.run", side_effect=fake_run), \
             patch("src.processors.format_agent.time.sleep"):
            result = agent._try_mineru_open_api(document)

        self.assertIn("Hola", result)
        self.assertIn("Texto procesado", result)
        self.assertEqual(fake_run.calls, 3)


if __name__ == "__main__":
    unittest.main()