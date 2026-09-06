"""
Pipeline principal de traducción.
Orquesta el procesamiento de archivos, chunking, traducción paralela
y ensamblaje final del documento traducido.
"""
import uuid
from concurrent.futures import ThreadPoolExecutor, as_completed
from typing import List, Optional, Callable, Dict
from dataclasses import dataclass
from datetime import datetime

from src.core.models import (
    Document,
    TranslationStatus,
    TranslationChunk,
    TranslationProvider,
)
from src.processors import ProcessorFactory
from src.translators import TranslatorFactory
from src.translators.base import BaseTranslator
from src.utils.chunker import chunk_document_sections, ChunkingConfig
from src.utils.cache import TranslationCache
from src.utils.logger import get_logger

logger = get_logger(__name__)


@dataclass
class TranslationProgress:
    """Estado de progreso de la traducción de un documento."""
    doc_id: str
    filename: str
    status: TranslationStatus
    progress: float  # 0.0 a 1.0
    current_chunk: int = 0
    total_chunks: int = 0
    error_message: str = ""


class TranslationPipeline:
    """
    Pipeline principal que coordina todo el proceso de traducción:
    1. Procesamiento del archivo (extracción de texto y secciones)
    2. Chunking inteligente
    3. Verificación de caché
    4. Traducción paralela de chunks
    5. Ensamblaje de secciones traducidas
    """

    def __init__(
        self,
        config: dict,
        translator: BaseTranslator,
        cache: Optional[TranslationCache] = None,
        max_workers: int = 4,
    ):
        self.config = config
        self.translator = translator
        self.cache = cache
        self.max_workers = max_workers

        translation_cfg = config.get("translation", {})
        self.chunking_config = ChunkingConfig(
            max_tokens=translation_cfg.get("chunk_size_tokens", 3500),
            overlap_tokens=translation_cfg.get("chunk_overlap_tokens", 200),
        )
        self.source_lang = translation_cfg.get("source_lang", "EN")
        self.target_lang = translation_cfg.get("target_lang", "ES")

    def process_document(
        self,
        document: Document,
        progress_callback: Optional[Callable[[TranslationProgress], None]] = None,
    ) -> Document:
        """
        Procesa un documento completo: extracción -> chunking -> traducción -> ensamblaje.

        Args:
            document: Documento a procesar
            progress_callback: Función para reportar progreso

        Returns:
            Documento con traducciones completadas
        """
        doc_id = document.doc_id
        filename = document.filename

        def _report(status: TranslationStatus, progress: float, **kwargs):
            if progress_callback:
                progress_callback(TranslationProgress(
                    doc_id=doc_id,
                    filename=filename,
                    status=status,
                    progress=progress,
                    **kwargs,
                ))

        try:
            # 1. Procesar archivo: extraer texto y detectar secciones
            _report(TranslationStatus.LOADING, 0.05)
            document.status = TranslationStatus.LOADING

            processor = ProcessorFactory.get_processor(document.file_type)
            document = processor.process(document)
            document.status = TranslationStatus.LOADED
            _report(TranslationStatus.LOADED, 0.1)

            # 2. Verificar caché
            if self.cache:
                cached = self.cache.get(document.content_hash, self.translator.get_provider_name())
                if cached:
                    logger.info(f"Usando caché para: {filename}")
                    document = self.cache.restore_to_document(document, cached)
                    _report(TranslationStatus.CACHED, 1.0)
                    return document

            # 3. Chunking
            _report(TranslationStatus.CHUNKING, 0.15)
            document.status = TranslationStatus.CHUNKING
            document.chunks = chunk_document_sections(document.sections, self.chunking_config)

            if not document.chunks:
                logger.warning(f"No hay chunks para traducir en: {filename}")
                document.status = TranslationStatus.COMPLETED
                document.progress = 1.0
                document.completed_at = datetime.now()
                _report(TranslationStatus.COMPLETED, 1.0)
                return document

            total_chunks = len(document.chunks)
            logger.info(f"Documento {filename}: {total_chunks} chunks para traducir")

            # 4. Traducción paralela de chunks
            _report(TranslationStatus.TRANSLATING, 0.2, total_chunks=total_chunks)
            document.status = TranslationStatus.TRANSLATING

            completed_chunks = 0

            def _translate_chunk(chunk: TranslationChunk) -> TranslationChunk:
                nonlocal completed_chunks
                try:
                    translated = self.translator.translate_with_retry(
                        chunk.text,
                        source_lang=self.source_lang,
                        target_lang=self.target_lang,
                    )
                    chunk.translated_text = translated
                    chunk.status = TranslationStatus.TRANSLATED
                except Exception as e:
                    logger.error(f"Error traduciendo chunk {chunk.chunk_id}: {e}")
                    chunk.status = TranslationStatus.ERROR
                    chunk.translated_text = f"[ERROR DE TRADUCCIÓN: {str(e)}]\n\n{chunk.text}"

                completed_chunks += 1
                base_progress = 0.2
                translation_range = 0.75
                chunk_progress = completed_chunks / total_chunks
                overall = base_progress + (translation_range * chunk_progress)
                _report(
                    TranslationStatus.TRANSLATING,
                    min(0.95, overall),
                    current_chunk=completed_chunks,
                    total_chunks=total_chunks,
                )
                return chunk

            # Ejecutar en paralelo
            with ThreadPoolExecutor(max_workers=self.max_workers) as executor:
                futures = [executor.submit(_translate_chunk, chunk) for chunk in document.chunks]
                for future in as_completed(futures):
                    try:
                        future.result()
                    except Exception as e:
                        logger.error(f"Error en futuro de traducción: {e}")

            # 4.1 Verificar cuántos chunks realmente fallaron. Antes esto no se
            #     comprobaba y el documento se marcaba como COMPLETADO (y se
            #     guardaba en caché) aunque TODOS los fragmentos hubieran
            #     fallado, dejando solo texto "[ERROR DE TRADUCCIÓN: ...]" en
            #     el resultado. Esto hacía parecer que la traducción funcionó
            #     cuando en realidad no tradujo nada.
            error_chunks = sum(1 for c in document.chunks if c.status == TranslationStatus.ERROR)

            if error_chunks == total_chunks:
                # Fallo total: ningún proveedor pudo traducir nada.
                error_msg = (
                    f"Todos los proveedores de traducción fallaron para los "
                    f"{total_chunks} fragmentos de este documento. Revisa tus "
                    f"API keys, el modelo configurado y las cuotas de cada "
                    f"proveedor (Gemini/DeepL/OpenAI)."
                )
                logger.error(f"{filename}: {error_msg}")
                document.status = TranslationStatus.ERROR
                document.error_message = error_msg
                document.progress = min(0.95, 0.2 + 0.75)
                _report(TranslationStatus.ERROR, document.progress, error_message=error_msg)
                # No cachear una traducción que en realidad no existe: si se
                # cacheara, la próxima vez la app "encontraría en caché" el
                # mismo resultado fallido y jamás volvería a intentar traducir.
                return document

            # 5. Ensamblar traducciones en secciones
            _report(TranslationStatus.EXPORTING, 0.95)
            self._assemble_translations(document)

            # 6. Guardar en caché (solo si hubo al menos una traducción real)
            if self.cache:
                try:
                    self.cache.put(document, self.translator.get_provider_name())
                except Exception as e:
                    logger.warning(f"No se pudo guardar en caché: {e}")

            document.status = TranslationStatus.COMPLETED
            document.progress = 1.0
            document.completed_at = datetime.now()

            if error_chunks > 0:
                # Traducción parcial: que quede constancia visible, en vez de
                # marcar el documento como un éxito silencioso.
                document.error_message = (
                    f"⚠️ {error_chunks}/{total_chunks} fragmentos NO se pudieron "
                    f"traducir (quedaron con el texto original y una nota de "
                    f"error). Revisa el documento antes de usarlo."
                )
                logger.warning(f"{filename}: {document.error_message}")

            try:
                provider_name = self.translator.get_provider_name()
                # Si es fallback, extraer el proveedor real
                if provider_name.startswith("fallback->"):
                    provider_name = provider_name.replace("fallback->", "")
                document.provider_used = TranslationProvider(provider_name)
            except ValueError:
                # Si no existe en el enum, usar GEMINI por defecto
                logger.warning(f"Proveedor '{self.translator.get_provider_name()}' no reconocido, usando GEMINI por defecto")
                document.provider_used = TranslationProvider.GEMINI
            document.translated_tokens = document.estimated_tokens

            _report(TranslationStatus.COMPLETED, 1.0)
            logger.info(f"Traducción completada: {filename}")

            return document

        except Exception as e:
            logger.exception(f"Error procesando documento {filename}")
            document.status = TranslationStatus.ERROR
            document.error_message = str(e)
            _report(TranslationStatus.ERROR, 0.0, error_message=str(e))
            raise

    def _assemble_translations(self, document: Document) -> None:
        """
        Ensambla los chunks traducidos de vuelta en sus secciones correspondientes.
        Maneja solapamientos entre chunks.
        """
        # Agrupar chunks por sección
        chunks_by_section: Dict[str, List[TranslationChunk]] = {}
        for chunk in document.chunks:
            if chunk.section_id not in chunks_by_section:
                chunks_by_section[chunk.section_id] = []
            chunks_by_section[chunk.section_id].append(chunk)

        # Ordenar chunks por posición y concatenar
        for section in document.sections:
            section_chunks = chunks_by_section.get(section.section_id, [])
            if not section_chunks:
                section.translated_text = section.original_text
                continue

            # Ordenar por start_idx
            section_chunks.sort(key=lambda c: c.start_idx)

            # Concatenar, eliminando solapamientos
            translated_parts = []
            last_end = 0

            for chunk in section_chunks:
                if chunk.status == TranslationStatus.ERROR:
                    translated_parts.append(chunk.translated_text)
                    continue

                text = chunk.translated_text
                # Eliminar solapamiento simple: si el inicio de este chunk
                # coincide con el final del anterior, omitir la parte duplicada
                if translated_parts and last_end > chunk.start_idx:
                    overlap = last_end - chunk.start_idx
                    # Aproximar solapamiento en texto traducido (50% del overlap en chars)
                    char_overlap = int(overlap * 0.5)
                    if char_overlap > 0 and char_overlap < len(text):
                        # Buscar un punto de corte seguro
                        cut_point = min(char_overlap + 100, len(text))
                        search_region = text[:cut_point]
                        # Buscar final de oración
                        import re
                        sentence_end = re.search(r'[.!?]\s+', search_region[::-1])
                        if sentence_end:
                            idx = len(search_region) - sentence_end.start()
                            text = text[idx:].lstrip()
                        else:
                            text = text[char_overlap:].lstrip()

                if text:
                    translated_parts.append(text)
                last_end = chunk.end_idx

            section.translated_text = "\n\n".join(translated_parts).strip()

    def process_documents_parallel(
        self,
        documents: List[Document],
        doc_progress_callback: Optional[Callable[[TranslationProgress], None]] = None,
        global_progress_callback: Optional[Callable[[float, int, int], None]] = None,
    ) -> List[Document]:
        """
        Procesa múltiples documentos en paralelo.

        Args:
            documents: Lista de documentos a procesar
            doc_progress_callback: Callback por documento
            global_progress_callback: Callback global (progreso, completados, total)

        Returns:
            Lista de documentos procesados
        """
        total = len(documents)
        completed = 0
        results: List[Document] = []

        def _process_single(doc: Document) -> Document:
            nonlocal completed
            try:
                result = self.process_document(doc, doc_progress_callback)
                return result
            except Exception as e:
                logger.error(f"Falló documento {doc.filename}: {e}")
                return doc
            finally:
                completed += 1
                if global_progress_callback:
                    global_progress_callback(completed / total, completed, total)

        # Usar workers limitados para no saturar
        doc_workers = max(1, min(self.max_workers, total))

        with ThreadPoolExecutor(max_workers=doc_workers) as executor:
            futures = [executor.submit(_process_single, doc) for doc in documents]
            for future in as_completed(futures):
                try:
                    results.append(future.result())
                except Exception as e:
                    logger.error(f"Error en futuro de documento: {e}")

        return results