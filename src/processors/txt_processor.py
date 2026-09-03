"""
Procesador para archivos de texto plano (TXT).
"""
from typing import Optional

from src.core.models import FileType
from src.processors.base import (
    BaseFileProcessor,
    CorruptedFileError,
    FileProcessingError,
)
from src.utils.logger import get_logger

logger = get_logger(__name__)


class TxtProcessor(BaseFileProcessor):
    """Procesador de archivos de texto plano."""

    def can_handle(self, file_type: FileType) -> bool:
        return file_type == FileType.TXT

    def extract_text(self, document) -> str:
        """Extrae texto de un archivo TXT probando múltiples codificaciones."""
        encodings = ['utf-8', 'latin-1', 'cp1252', 'iso-8859-1']

        for encoding in encodings:
            try:
                text = document.content.decode(encoding)
                # Estimar páginas
                word_count = len(text.split())
                self._page_count = max(1, word_count // 500)
                return text
            except UnicodeDecodeError:
                continue

        raise CorruptedFileError(
            "No se pudo decodificar el archivo de texto. "
            "Las codificaciones probadas fueron: UTF-8, Latin-1, CP1252."
        )

    def get_page_count(self, document) -> Optional[int]:
        if hasattr(self, '_page_count'):
            return self._page_count
        return None
