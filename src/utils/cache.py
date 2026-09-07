"""
Sistema de caché de traducciones basado en disco.
Almacena traducciones completas por hash de contenido para evitar
re-procesar archivos idénticos.
"""
import json
import hashlib
import os
from pathlib import Path
from typing import Optional, Dict, Any
from datetime import datetime

from src.core.models import Document, Section, TranslationStatus, SectionType
from src.utils.logger import get_logger

logger = get_logger(__name__)


class TranslationCache:
    """
    Caché persistente de traducciones almacenada en disco.
    Usa SHA-256 del contenido del archivo como clave.
    """

    def __init__(self, cache_dir: str = "cache"):
        self.cache_dir = Path(cache_dir)
        self.cache_dir.mkdir(parents=True, exist_ok=True)
        self.index_path = self.cache_dir / "index.json"
        self.index: Dict[str, Dict[str, Any]] = self._load_index()
        logger.info(f"Caché inicializado en: {self.cache_dir.absolute()}")

    def _load_index(self) -> Dict[str, Dict[str, Any]]:
        if self.index_path.exists():
            try:
                with open(self.index_path, 'r', encoding='utf-8') as f:
                    return json.load(f)
            except Exception as e:
                logger.warning(f"No se pudo cargar índice de caché: {e}")
        return {}

    def _save_index(self) -> None:
        try:
            with open(self.index_path, 'w', encoding='utf-8') as f:
                json.dump(self.index, f, indent=2, ensure_ascii=False)
        except Exception as e:
            logger.error(f"No se pudo guardar índice de caché: {e}")

    def _get_cache_path(self, content_hash: str) -> Path:
        return self.cache_dir / f"{content_hash}.json"

    def get(self, content_hash: str, provider: str) -> Optional[Dict[str, Any]]:
        """
        Busca una traducción en caché.

        Args:
            content_hash: Hash SHA-256 del contenido original
            provider: Nombre del proveedor de traducción

        Returns:
            Diccionario con datos de la traducción o None si no existe
        """
        entry = self.index.get(content_hash)
        if not entry:
            return None

        if entry.get("provider") != provider:
            logger.debug(f"Caché encontrado pero para proveedor diferente: {entry.get('provider')} != {provider}")
            return None

        cache_path = self._get_cache_path(content_hash)
        if not cache_path.exists():
            logger.warning(f"Entrada en índice pero archivo no encontrado: {content_hash}")
            del self.index[content_hash]
            self._save_index()
            return None

        try:
            with open(cache_path, 'r', encoding='utf-8') as f:
                data = json.load(f)
            logger.info(f"Traducción recuperada de caché: {content_hash[:16]}...")
            return data
        except Exception as e:
            logger.error(f"Error leyendo caché: {e}")
            return None

    def put(self, document: Document, provider: str) -> None:
        """
        Almacena una traducción en caché.

        Args:
            document: Documento traducido
            provider: Proveedor utilizado
        """
        content_hash = document.content_hash
        cache_path = self._get_cache_path(content_hash)

        # Serializar secciones
        sections_data = []
        for section in document.sections:
            sections_data.append({
                "section_id": section.section_id,
                "section_type": section.section_type.value,
                "title": section.title,
                "original_text": section.original_text,
                "translated_text": section.translated_text,
                "metadata": section.metadata,
            })

        cache_data = {
            "content_hash": content_hash,
            "filename": document.filename,
            "file_type": document.file_type.value,
            "provider": provider,
            "created_at": datetime.now().isoformat(),
            "estimated_tokens": document.estimated_tokens,
            "sections": sections_data,
            "metadata": {
                "layout_elements": document.metadata.get("layout_elements", []),
                "layout_backend": document.metadata.get("layout_backend", ""),
                "preprocessed": document.metadata.get("preprocessed", False),
            },
            "page_count": document.page_count,
        }

        try:
            with open(cache_path, 'w', encoding='utf-8') as f:
                json.dump(cache_data, f, ensure_ascii=False, indent=2)

            self.index[content_hash] = {
                "filename": document.filename,
                "provider": provider,
                "created_at": datetime.now().isoformat(),
                "size_bytes": document.file_size_bytes,
                "estimated_tokens": document.estimated_tokens,
            }
            self._save_index()
            logger.info(f"Traducción guardada en caché: {content_hash[:16]}...")
        except Exception as e:
            logger.error(f"Error guardando en caché: {e}")

    def restore_to_document(self, document: Document, cache_data: Dict[str, Any]) -> Document:
        """
        Restaura los datos de caché a un objeto Document.

        Args:
            document: Documento original (vacío de secciones)
            cache_data: Datos desde la caché

        Returns:
            Document con secciones y traducciones restauradas
        """
        document.sections = []
        for s_data in cache_data.get("sections", []):
            section = Section(
                section_id=s_data["section_id"],
                section_type=SectionType(s_data["section_type"]),
                title=s_data["title"],
                original_text=s_data["original_text"],
                translated_text=s_data["translated_text"],
                metadata=s_data.get("metadata", {}),
            )
            document.sections.append(section)

        document.status = TranslationStatus.CACHED
        document.progress = 1.0
        document.estimated_tokens = cache_data.get("estimated_tokens", 0)
        document.translated_tokens = document.estimated_tokens
        document.page_count = cache_data.get("page_count")
        document.metadata.update(cache_data.get("metadata", {}))
        document.provider_used = cache_data.get("provider")
        return document

    def clear(self) -> None:
        """Limpia toda la caché."""
        import shutil
        for item in self.cache_dir.iterdir():
            if item.is_file() and item.suffix == '.json':
                item.unlink()
        self.index = {}
        self._save_index()
        logger.info("Caché limpiada completamente")

    def stats(self) -> Dict[str, Any]:
        """Devuelve estadísticas de la caché."""
        total_size = 0
        for content_hash in self.index:
            cache_path = self._get_cache_path(content_hash)
            if cache_path.exists():
                total_size += cache_path.stat().st_size

        return {
            "entry_count": len(self.index),
            "total_size_bytes": total_size,
            "total_size_kb": total_size / 1024,
            "total_size_mb": total_size / (1024 * 1024),
        }
