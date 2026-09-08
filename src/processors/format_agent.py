"""Agente de formato previo a la traducción.

Ofrece dos rutas: ``local`` (determinista, sin red) y ``gemini`` (reconstruye
la estructura con Gemini y valida que no se haya perdido texto). Ninguna ruta
traduce el documento; las referencias se conservan en el idioma original.
"""
import json
import re
import subprocess
import tempfile
import threading
import time
from collections import deque
from dataclasses import dataclass
from typing import Any, Dict, List, Optional
from pathlib import Path

from src.core.models import Document, Section, SectionType
from src.processors.pdf_processor import PdfProcessor
from src.processors.text_normalizer import normalize_extracted_text
from src.utils.logger import get_logger

logger = get_logger(__name__)

REFERENCE_HEADING_BOLD = re.compile(
    r"^\s*(?:\*{1,3}\s*)?(references|bibliography|literature cited|works cited)"
    r"(?:\s*\*{1,3})?\s*$",
    re.IGNORECASE,
)
REFERENCE_START = re.compile(r"(?:^|\n)\s*(?:\[\d{1,4}\]|\d{1,4}[.)])\s+")


@dataclass
class FormatAgentConfig:
    mode: str = "local"
    model: str = "gemini-3.1-flash-lite"
    requests_per_minute: int = 4
    max_pages_per_request: int = 2
    max_words_per_request: int = 2800
    min_completeness_ratio: float = 0.90
    require_mineru: bool = True
    mineru_enabled: bool = True
    mineru_retries: int = 3
    mineru_timeout_seconds: int = 600
    mineru_pages_per_chunk: int = 20
    mineru_max_pages: int = 20
    mineru_max_file_size_mb: int = 10
    llama_enabled: bool = True
    llama_api_key: str = ""
    llama_tier: str = "cost_effective"
    llama_version: str = "latest"
    llama_timeout_seconds: int = 600


class FormatAgent:
    """Convierte el texto extraído en secciones aptas para traducción."""

    _rate_lock = threading.Lock()
    _request_times: deque = deque()
    _backend_turn = 0
    _backend_turn_lock = threading.Lock()

    def __init__(self, config: Optional[FormatAgentConfig] = None, api_key: str = ""):
        self.config = config or FormatAgentConfig()
        self.api_key = api_key
        self._model = None

    def process(self, document: Document) -> Document:
        """Procesa un PDF separando contenido traducible de su estructura."""
        if self.config.mode not in {"local", "gemini"}:
            raise ValueError("mode debe ser 'local' o 'gemini'")

        base = PdfProcessor()
        full_text, backend = self._extract_layout_text(document, base)
        if self.config.mode == "gemini":
            formatted_text = self._format_with_gemini(full_text)
        else:
            formatted_text = full_text

        layout_elements = self._build_layout_elements(formatted_text)
        sections = self._build_sections(formatted_text)
        document.sections = sections
        document.metadata["layout_elements"] = layout_elements
        document.metadata["translatable_elements"] = [
            element for element in layout_elements if element["translatable"]
        ]
        document.metadata["layout_backend"] = backend
        document.metadata["preprocessed"] = True
        document.page_count = base.get_page_count(document)
        document.estimated_tokens = sum(
            max(1, len(element["content"]) // 4)
            for element in layout_elements
            if element["translatable"]
        )
        document.metadata["format_agent"] = self.config.mode
        document.metadata["format_agent_model"] = self.config.model if self.config.mode == "gemini" else "local"
        return document

    def _extract_layout_text(self, document: Document, base: PdfProcessor) -> tuple[str, str]:
        """Cola estructurada MinerU ↔ LlamaParse con fallback mutuo.

        El backend primario rota por documento (doc1→MinerU, doc2→LlamaParse, ...).
        Si el primario falla, se intenta el otro; si ambos fallan se respeta
        ``require_mineru`` o se cae a pdfplumber.
        """
        for backend in self._ordered_backends():
            if backend == "mineru":
                text = self._try_mineru_open_api(document)
                label = "mineru-open-api-flash"
            else:
                text = self._try_llama_parse(document)
                label = "llamaparse"
            if text:
                logger.info("Extractor %s OK para %s", label, document.filename)
                return text, label

        if self.config.require_mineru:
            parts = []
            mineru_err = document.metadata.get("mineru_error")
            if mineru_err:
                parts.append(f"MinerU: {mineru_err}")
            llama_err = document.metadata.get("llama_error")
            if llama_err:
                parts.append(f"LlamaParse: {llama_err}")
            detail = " | ".join(parts) if parts else "sin detalle"
            raise RuntimeError(
                f"No se pudo extraer texto estructurado. {detail}. "
                "Revisa la conexión (MinerU/LlamaParse) o desactiva "
                "`require_mineru` para usar pdfplumber como último recurso."
            )

        return normalize_extracted_text(base.extract_text(document)), "pdfplumber-layout-fallback"

    def _available_backends(self) -> List[str]:
        """Lista de extractores estructurados disponibles."""
        backends: List[str] = []
        if self.config.mineru_enabled:
            backends.append("mineru")
        if self.config.llama_enabled and self.config.llama_api_key:
            backends.append("llamaparse")
        return backends

    def _ordered_backends(self) -> List[str]:
        """Devuelve la cola de extractores con el primario rotado por documento."""
        backends = self._available_backends()
        if not backends:
            return []
        with self._backend_turn_lock:
            index = self._backend_turn % len(backends)
            self._backend_turn += 1
        return backends[index:] + backends[:index]

    def _try_llama_parse(self, document: Document) -> str:
        """Extrae Markdown con LlamaParse (LlamaCloud) en una sola llamada por PDF."""
        if not self.config.llama_api_key:
            return ""
        try:
            from llama_cloud import LlamaCloud
        except ImportError as exc:
            logger.error("LlamaCloud no disponible: %s", exc)
            document.metadata["llama_error"] = f"llama-cloud no instalado: {exc}"
            return ""

        timeout_seconds = max(60, int(self.config.llama_timeout_seconds))
        try:
            with tempfile.TemporaryDirectory(prefix="paper_llama_") as temp_dir:
                temp_pdf = Path(temp_dir) / f"input_{document.doc_id or 'doc'}.pdf"
                with open(temp_pdf, "wb") as handle:
                    handle.write(document.content)

                client = LlamaCloud(api_key=self.config.llama_api_key)
                file_obj = client.files.create(file=str(temp_pdf), purpose="parse")
                try:
                    start = time.time()
                    result = client.parsing.parse(
                        file_id=file_obj.id,
                        tier=self.config.llama_tier,
                        version=self.config.llama_version,
                        expand=["markdown_full", "text_full"],
                        timeout=timeout_seconds,
                    )
                    elapsed = time.time() - start
                    markdown = (getattr(result, "markdown_full", "") or "").strip()
                    if not markdown:
                        markdown = (getattr(result, "text_full", "") or "").strip()
                    if not markdown:
                        detail = "LlamaParse no devolvió texto"
                        document.metadata["llama_error"] = detail
                        logger.warning("LlamaParse vacío %s", document.filename)
                        return ""
                    logger.info(
                        "LlamaParse OK para %s: %.1fs, %s caracteres",
                        document.filename,
                        elapsed,
                        len(markdown),
                    )
                    return markdown
                finally:
                    try:
                        client.files.delete(file_obj.id)
                    except Exception:
                        pass
        except Exception as exc:
            detail = f"{type(exc).__name__}: {exc}"
            logger.error("LlamaParse excepción %s: %s", document.filename, detail)
            document.metadata["llama_error"] = detail[-1000:]
        return ""

    def _try_mineru_open_api(self, document: Document) -> str:
        """Extrae Markdown con MinerU Flash.

        Divide el PDF en bloques adaptativos: solo se parte si supera el máximo
        de páginas o de peso; en ese caso el tamaño de cada bloque se reduce
        hasta que quede bajo el límite de MB.
        """
        try:
            from mineru_open_api._cli import _get_binary_path
            from PyPDF2 import PdfReader, PdfWriter
        except ImportError as exc:
            logger.error("Falta MinerU Open API o PyPDF2: %s", exc)
            document.metadata["mineru_error"] = str(exc)
            return ""

        pages_per_chunk = max(1, int(self.config.mineru_pages_per_chunk))
        max_pages = max(1, int(self.config.mineru_max_pages))
        max_file_size_bytes = max(
            1, int(self.config.mineru_max_file_size_mb)
        ) * 1024 * 1024
        timeout_seconds = max(60, int(self.config.mineru_timeout_seconds))

        try:
            with tempfile.TemporaryDirectory(prefix="paper_mineru_") as temp_dir:
                reader = PdfReader(__import__("io").BytesIO(document.content))
                total_pages = len(reader.pages)
                file_size_bytes = len(document.content)

                needs_split = (
                    total_pages > max_pages or file_size_bytes > max_file_size_bytes
                )

                chunks: List[tuple[int, int]] = []
                if needs_split:
                    chunks = self._plan_chunks(
                        reader, file_size_bytes, pages_per_chunk, max_pages, max_file_size_bytes
                    )
                else:
                    chunks = [(0, total_pages)]

                binary = _get_binary_path()
                markdown_parts = []
                pending = list(chunks)
                seq = 0

                while pending:
                    seq += 1
                    start, end = pending.pop(0)
                    chunk_path = Path(temp_dir) / f"part_{seq:04d}.pdf"
                    writer = PdfWriter()
                    for page in reader.pages[start:end]:
                        writer.add_page(page)
                    with chunk_path.open("wb") as handle:
                        writer.write(handle)

                    actual_size = chunk_path.stat().st_size if chunk_path.exists() else 0
                    if actual_size > max_file_size_bytes and end - start > 1:
                        mid = (start + end) // 2
                        pending.insert(0, (mid, end))
                        pending.insert(0, (start, mid))
                        logger.warning(
                            "MinerU división por peso real para %s: "
                            "bloque págs. %s-%s supera %sMB; se parte en dos",
                            document.filename,
                            start + 1,
                            end,
                            self.config.mineru_max_file_size_mb,
                        )
                        continue

                    markdown = self._run_flash_extract(
                        binary,
                        chunk_path,
                        document,
                        start,
                        end,
                        seq,
                        len(pending) + 1,
                        timeout_seconds,
                    )
                    if markdown:
                        markdown_parts.append(markdown)

                if markdown_parts:
                    return "\n\n".join(markdown_parts)
        except Exception as exc:
            logger.error("MinerU Open API no pudo procesar %s: %s", document.filename, exc)
            document.metadata["mineru_error"] = str(exc)
        return ""

    def _run_flash_extract(
        self,
        binary: str,
        chunk_path: Path,
        document: Document,
        start: int,
        end: int,
        seq: int,
        total_chunks: int,
        timeout_seconds: int,
    ) -> str:
        """Ejecuta MinerU Flash sobre un bloque de páginas con reintentos y backoff."""
        result = None
        for attempt in range(self.config.mineru_retries + 1):
            try:
                result = subprocess.run(
                    [binary, "flash-extract", str(chunk_path)],
                    capture_output=True,
                    text=True,
                    encoding="utf-8",
                    errors="replace",
                    timeout=timeout_seconds,
                )
            except subprocess.TimeoutExpired as exc:
                result = None
                detail = (
                    f"timeout tras {exc.timeout}s al subir el PDF a MinerU "
                    f"(chunk {seq}/{total_chunks}, páginas {start + 1}-{end})"
                )
                document.metadata["mineru_error"] = detail
                logger.warning(
                    "MinerU timeout %s/%s para %s chunk %s/%s: %s",
                    attempt + 1,
                    self.config.mineru_retries + 1,
                    document.filename,
                    seq,
                    total_chunks,
                    detail,
                )
                if attempt == self.config.mineru_retries:
                    raise RuntimeError(detail)
                time.sleep(2 ** attempt)
                continue
            except OSError as exc:
                result = None
                detail = (
                    f"error ejecutando MinerU (chunk {seq}/{total_chunks}, "
                    f"páginas {start + 1}-{end}): {exc}"
                )
                document.metadata["mineru_error"] = detail
                logger.warning(
                    "MinerU error %s/%s para %s chunk %s/%s: %s",
                    attempt + 1,
                    self.config.mineru_retries + 1,
                    document.filename,
                    seq,
                    total_chunks,
                    detail,
                )
                if attempt == self.config.mineru_retries:
                    raise RuntimeError(detail)
                time.sleep(2 ** attempt)
                continue

            if result.returncode == 0 and result.stdout.strip():
                break
            detail = (result.stderr or result.stdout or "sin respuesta").strip()
            document.metadata["mineru_error"] = detail[-1000:]
            logger.warning(
                "MinerU intento %s/%s para %s: %s",
                attempt + 1,
                self.config.mineru_retries + 1,
                document.filename,
                detail,
            )
            if attempt == self.config.mineru_retries:
                break
            time.sleep(2 ** attempt)

        return result.stdout.strip() if result and result.returncode == 0 else ""

    def _plan_chunks(
        self,
        reader: Any,
        file_size_bytes: int,
        pages_per_chunk: int,
        max_pages: int,
        max_file_size_bytes: int,
    ) -> List[tuple[int, int]]:
        """Divide el PDF en bloques (inicio, fin) respetando límites de páginas y peso.

        Si el PDF pesa más que ``max_file_size_bytes`` aun con pocas páginas,
        reduce el número de páginas por bloque hasta que cada parte quede bajo
        el límite de peso.
        """
        total_pages = len(reader.pages)
        if total_pages == 0:
            return []
        est_bytes_per_page = max(1, file_size_bytes) / max(1, total_pages)
        chunk_size = max(1, min(int(pages_per_chunk), int(max_pages)))
        planned: List[tuple[int, int]] = []
        start = 0
        while start < total_pages:
            end = min(total_pages, start + chunk_size)
            if est_bytes_per_page * (end - start) > max_file_size_bytes:
                planned.extend(
                    self._split_range_by_size(
                        start, end, est_bytes_per_page, max_file_size_bytes
                    )
                )
            else:
                planned.append((start, end))
            start = end
        return planned

    def _split_range_by_size(
        self,
        start: int,
        end: int,
        est_bytes_per_page: float,
        max_file_size_bytes: int,
    ) -> List[tuple[int, int]]:
        """Divide recursivamente un rango de páginas hasta que su peso estimado sea menor al límite."""
        if end - start <= 1 or est_bytes_per_page * (end - start) <= max_file_size_bytes:
            return [(start, end)]
        mid = (start + end) // 2
        return [
            *self._split_range_by_size(start, mid, est_bytes_per_page, max_file_size_bytes),
            *self._split_range_by_size(mid, end, est_bytes_per_page, max_file_size_bytes),
        ]

    def _build_layout_elements(self, text: str) -> List[Dict[str, Any]]:
        """Construye un orden de lectura explícito y marca qué se traduce."""
        elements: List[Dict[str, Any]] = []
        lines = text.splitlines()
        index = 0
        while index < len(lines):
            line = lines[index].strip()
            if not line:
                index += 1
                continue

            if REFERENCE_HEADING_BOLD.match(re.sub(r"^\s{0,3}#{1,6}\s+", "", line)):
                index += 1
                continue

            if re.match(r"^<!--\s*(?:image|figure)\s*-->$", line, re.IGNORECASE):
                elements.append(self._element("figure", line, False))
                index += 1
                continue

            if line.startswith("|") and "|" in line[1:]:
                table_lines = [line]
                index += 1
                while index < len(lines) and lines[index].strip().startswith("|"):
                    table_lines.append(lines[index].strip())
                    index += 1
                elements.append(self._element("table", "\n".join(table_lines), True))
                continue

            if "<table" in line.lower():
                table_text = line
                index += 1
                while "</table>" not in table_text.lower() and index < len(lines):
                    table_text += lines[index].strip()
                    index += 1
                table_markdown = self._html_table_to_markdown(table_text)
                if table_markdown:
                    elements.append(self._element("table", table_markdown, True))
                    continue

            if re.match(r"^(?:!\[|\[(?:figure|figura)\b)", line, re.IGNORECASE):
                elements.append(self._element("figure", line, False))
                index += 1
                continue

            if re.match(r"^(?:figure|figura)\s+\d+\b", line, re.IGNORECASE):
                elements.append(self._element("figure_caption", line, True))
                index += 1
                continue

            if line.startswith(("$$", "\\[", "\\begin{")):
                equation = [line]
                end_marker = "$$" if line.startswith("$$") else "\\]" if line.startswith("\\[") else "\\end{"
                index += 1
                while index < len(lines):
                    equation.append(lines[index].strip())
                    if end_marker in lines[index]:
                        index += 1
                        break
                    index += 1
                elements.append(self._element("equation", "\n".join(equation), False))
                continue

            if line.startswith("#") or re.match(r"^\d+(?:\.\d+)*\.?\s+\S", line):
                cleaned = re.sub(r"\*{1,3}([^*]*?)\*{1,3}", r"\1", re.sub(r"^#+\s*", "", line))
                elements.append(self._element("section_title", cleaned, True))
                index += 1
                continue

            if re.match(r"^(?:\*\s+|-\s+|\d+[.)]\s+)", line):
                elements.append(self._element("list_item", line, True))
                index += 1
                continue

            paragraph = [line]
            index += 1
            while index < len(lines) and lines[index].strip():
                next_line = lines[index].strip()
                if (next_line.startswith("|") or next_line.startswith("#") or
                    "<table" in next_line.lower() or
                    re.match(r"^(?:\d+(?:\.\d+)*\.?\s+|!\[|\[(?:figure|figura)\b|(?:figure|figura)\s+\d+\b)", next_line, re.IGNORECASE)):
                    break
                paragraph.append(next_line)
                index += 1
            elements.append(self._element("paragraph", " ".join(paragraph), True))

        body, references = self._split_references(text)
        if references and not any(element["type"] == "reference" for element in elements):
            elements = [element for element in elements if element["content"] not in references]
            for reference in self._normalize_references(references).split("\n\n"):
                if reference.strip():
                    elements.append(self._element("reference", reference, False))
        return elements

    @staticmethod
    def _element(element_type: str, content: str, translatable: bool) -> Dict[str, Any]:
        return {
            "type": element_type,
            "content": content.strip(),
            "translatable": translatable,
            "skip_translation": not translatable,
            "translated_content": "",
        }

    @staticmethod
    def _html_table_to_markdown(html: str) -> str:
        """Convierte las tablas HTML que devuelve MinerU a filas Markdown."""
        rows = []
        for row in re.findall(r"<tr[^>]*>(.*?)</tr>", html, flags=re.IGNORECASE | re.DOTALL):
            cells = re.findall(r"<t[dh][^>]*>(.*?)</t[dh]>", row, flags=re.IGNORECASE | re.DOTALL)
            cells = [re.sub(r"<[^>]+>", "", cell).strip() for cell in cells]
            if cells:
                rows.append("| " + " | ".join(cells) + " |")
        if not rows:
            return ""
        separator = "| " + " | ".join("---" for _ in rows[0].strip("|").split("|")) + " |"
        return "\n".join([rows[0], separator, *rows[1:]])

    def _build_sections(self, text: str) -> List[Section]:
        body, references = self._split_references(text)
        body = self._strip_markdown_heading_prefixes(body)
        processor = PdfProcessor()
        sections = processor._detect_sections(body)
        if references:
            sections.append(Section(
                section_id=f"sec_{processor.section_counter}",
                section_type=SectionType.REFERENCES,
                title="References",
                original_text=references,
            ))
        return sections

    @staticmethod
    def _strip_markdown_heading_prefixes(text: str) -> str:
        output = []
        for raw in text.splitlines():
            if re.match(r"^\s{0,3}#{1,6}\s+", raw):
                line = re.sub(r"^\s{0,3}#{1,6}\s+", "", raw)
                output.append(re.sub(r"\*{1,3}([^*]*?)\*{1,3}", r"\1", line))
            else:
                output.append(raw)
        return "\n".join(output)

    def _split_references(self, text: str) -> tuple[str, str]:
        lines = text.splitlines()
        for index, line in enumerate(lines):
            heading = re.sub(r"\*{1,3}([^*]*?)\*{1,3}", r"\1", re.sub(r"^\s{0,3}#{1,6}\s+", "", line.strip()))
            if REFERENCE_HEADING_BOLD.match(heading):
                body = "\n".join(lines[:index]).strip()
                refs = "\n".join(lines[index + 1:]).strip()
                return body, self._normalize_references(refs)
        return text, ""

    def _normalize_references(self, text: str) -> str:
        if not text:
            return ""
        matches = list(REFERENCE_START.finditer(text))
        if len(matches) < 2:
            return normalize_extracted_text(text)
        entries = []
        for index, match in enumerate(matches):
            end = matches[index + 1].start() if index + 1 < len(matches) else len(text)
            entry = normalize_extracted_text(text[match.start():end])
            if entry:
                entries.append(entry)
        return "\n\n".join(entries)

    def _format_with_gemini(self, text: str) -> str:
        if not self.api_key:
            raise RuntimeError("El modo Gemini requiere GEMINI_API_KEY o providers.gemini.api_key")
        model = self._get_model()
        body, references = self._split_references(text)
        paragraphs = [paragraph.strip() for paragraph in re.split(r"\n\s*\n", body) if paragraph.strip()]
        chunks: List[str] = []
        current: List[str] = []
        current_words = 0
        for paragraph in paragraphs:
            paragraph_words = self._word_count(paragraph)
            if current and current_words + paragraph_words > self.config.max_words_per_request:
                chunks.append("\n\n".join(current))
                current = []
                current_words = 0
            current.append(paragraph)
            current_words += paragraph_words
        if current:
            chunks.append("\n\n".join(current))
        formatted_chunks = []
        for chunk in chunks:
            if not chunk.strip():
                continue
            try:
                result = self._call_gemini(model, chunk)
            except Exception as exc:
                logger.warning("Gemini no pudo formatear un bloque; se usa la ruta local: %s", exc)
                result = ""
            if self._word_count(result) / max(1, self._word_count(chunk)) < self.config.min_completeness_ratio:
                logger.warning("Gemini omitió contenido; se conserva el bloque local")
                result = normalize_extracted_text(chunk)
            formatted_chunks.append(result)
        formatted_body = "\n\n".join(formatted_chunks)
        if references:
            return f"{formatted_body}\n\nReferences\n\n{references}".strip()
        return formatted_body

    def _get_model(self):
        if self._model is None:
            try:
                from google import genai
                from google.genai import types
            except ImportError as exc:
                raise RuntimeError("Instala google-genai para usar el modo Gemini") from exc
            self._model = genai.Client(
                api_key=self.api_key,
                http_options=types.HttpOptions(api_version="v1beta"),
            )
        return self._model

    def _call_gemini(self, model: Any, text: str) -> str:
        self._throttle()
        prompt = (
            "Eres un agente de formateo de artículos científicos extraídos de PDF. "
            "No traduzcas, resumas ni inventes. Devuelve solo el texto original "
            "reconstruido: ordena primero la columna izquierda y luego la derecha, "
            "une líneas del mismo párrafo, corrige guiones de fin de línea, conserva "
            "citas, números, ecuaciones, tablas y referencias. No elimines contenido.\n\n"
            f"TEXTO:\n{text}"
        )
        from google.genai import types

        response = model.models.generate_content(
            model=self.config.model,
            contents=prompt,
            config=types.GenerateContentConfig(
                temperature=0.1,
                max_output_tokens=8192,
            ),
        )
        try:
            result = response.text or ""
        except (AttributeError, ValueError):
            return ""
        return normalize_extracted_text(result.strip())

    def _throttle(self) -> None:
        while True:
            with self._rate_lock:
                now = time.monotonic()
                while self._request_times and now - self._request_times[0] >= 60:
                    self._request_times.popleft()
                if len(self._request_times) < max(1, self.config.requests_per_minute):
                    self._request_times.append(now)
                    return
                wait = 60 - (now - self._request_times[0]) + 0.05
            time.sleep(max(wait, 0.05))

    @staticmethod
    def _word_count(text: str) -> int:
        return len(re.findall(r"\b[\wÀ-ÿ]+\b", text))