"""
Factory y registro de procesadores de archivos.
Proporciona una interfaz unificada para obtener el procesador adecuado
según el tipo de archivo.
"""
from typing import Dict, Type

from src.core.models import FileType
from src.processors.base import BaseFileProcessor
from src.processors.pdf_processor import PdfProcessor
from src.processors.docx_processor import DocxProcessor
from src.processors.txt_processor import TxtProcessor
from src.processors.latex_processor import LatexProcessor


class ProcessorFactory:
    """Fábrica que devuelve el procesador adecuado para cada tipo de archivo."""

    _processors: Dict[FileType, Type[BaseFileProcessor]] = {
        FileType.PDF: PdfProcessor,
        FileType.DOCX: DocxProcessor,
        FileType.TXT: TxtProcessor,
        FileType.LATEX: LatexProcessor,
    }

    @classmethod
    def get_processor(cls, file_type: FileType) -> BaseFileProcessor:
        """Devuelve una instancia del procesador para el tipo de archivo."""
        processor_class = cls._processors.get(file_type)
        if processor_class is None:
            raise ValueError(f"No hay procesador para el tipo de archivo: {file_type}")
        return processor_class()

    @classmethod
    def register_processor(cls, file_type: FileType, processor_class: Type[BaseFileProcessor]) -> None:
        """Registra un nuevo procesador para un tipo de archivo."""
        cls._processors[file_type] = processor_class

    @classmethod
    def supported_types(cls) -> list:
        """Devuelve la lista de tipos de archivo soportados."""
        return list(cls._processors.keys())
