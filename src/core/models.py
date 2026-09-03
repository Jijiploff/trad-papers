"""
Modelos de datos para la aplicación de traducción de papers.
Define dataclasses y enumeraciones para representar documentos, secciones y estados.
"""
from dataclasses import dataclass, field
from enum import Enum
from typing import List, Optional, Dict, Any
from datetime import datetime
import hashlib
import os


class TranslationStatus(Enum):
    """Estado del proceso de traducción de un documento."""
    PENDING = "pending"
    LOADING = "loading"
    LOADED = "loaded"
    CHUNKING = "chunking"
    TRANSLATING = "translating"
    TRANSLATED = "translated"
    EXPORTING = "exporting"
    COMPLETED = "completed"
    ERROR = "error"
    CACHED = "cached"


class FileType(Enum):
    """Tipos de archivo soportados."""
    PDF = "pdf"
    DOCX = "docx"
    TXT = "txt"
    LATEX = "tex"

    @classmethod
    def from_extension(cls, filename: str) -> Optional['FileType']:
        ext = filename.lower().rsplit('.', 1)[-1] if '.' in filename else ''
        mapping = {
            'pdf': cls.PDF,
            'docx': cls.DOCX,
            'doc': cls.DOCX,
            'txt': cls.TXT,
            'tex': cls.LATEX,
            'latex': cls.LATEX,
        }
        return mapping.get(ext)


class TranslationProvider(Enum):
    """Proveedores de traducción soportados."""
    GEMINI = "gemini"
    DEEPL = "deepl"
    OPENAI = "openai"


class SectionType(Enum):
    """Tipos de secciones estándar en papers académicos."""
    ABSTRACT = "abstract"
    INTRODUCTION = "introduction"
    METHODOLOGY = "methodology"
    RESULTS = "results"
    DISCUSSION = "discussion"
    CONCLUSIONS = "conclusions"
    REFERENCES = "references"
    ACKNOWLEDGMENTS = "acknowledgments"
    APPENDIX = "appendix"
    OTHER = "other"
    TITLE = "title"


@dataclass
class Section:
    """Representa una sección dentro de un documento."""
    section_id: str
    section_type: SectionType
    title: str
    original_text: str
    translated_text: str = ""
    start_token: int = 0
    end_token: int = 0
    metadata: Dict[str, Any] = field(default_factory=dict)

    @property
    def token_count(self) -> int:
        return max(1, len(self.original_text) // 4)


@dataclass
class TranslationChunk:
    """Fragmento de texto para procesamiento por lotes."""
    chunk_id: str
    text: str
    section_id: str
    start_idx: int
    end_idx: int
    translated_text: str = ""
    token_count: int = 0
    status: TranslationStatus = TranslationStatus.PENDING


@dataclass
class Document:
    """Representa un documento cargado por el usuario."""
    doc_id: str
    filename: str
    file_type: FileType
    file_size_bytes: int
    content: bytes = field(repr=False)
    sections: List[Section] = field(default_factory=list)
    chunks: List[TranslationChunk] = field(default_factory=list)
    status: TranslationStatus = TranslationStatus.PENDING
    error_message: str = ""
    progress: float = 0.0
    estimated_tokens: int = 0
    translated_tokens: int = 0
    created_at: datetime = field(default_factory=datetime.now)
    completed_at: Optional[datetime] = None
    provider_used: Optional[TranslationProvider] = None
    metadata: Dict[str, Any] = field(default_factory=dict)
    page_count: Optional[int] = None

    @property
    def file_size_kb(self) -> float:
        return self.file_size_bytes / 1024

    @property
    def file_size_mb(self) -> float:
        return self.file_size_bytes / (1024 * 1024)

    @property
    def content_hash(self) -> str:
        """Genera un hash único del contenido para caché."""
        return hashlib.sha256(self.content).hexdigest()

    @property
    def full_original_text(self) -> str:
        return "\n\n".join(s.original_text for s in self.sections)

    @property
    def full_translated_text(self) -> str:
        return "\n\n".join(s.translated_text for s in self.sections if s.translated_text)

    def get_section_by_type(self, section_type: SectionType) -> Optional[Section]:
        for s in self.sections:
            if s.section_type == section_type:
                return s
        return None
