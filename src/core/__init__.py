"""
Módulo core: modelos de datos y pipeline de traducción.
"""
from src.core.models import (
    Document,
    Section,
    TranslationChunk,
    TranslationStatus,
    FileType,
    TranslationProvider,
    SectionType,
)

__all__ = [
    "Document",
    "Section",
    "TranslationChunk",
    "TranslationStatus",
    "FileType",
    "TranslationProvider",
    "SectionType",
    "TranslationPipeline",
    "TranslationProgress",
]


def __getattr__(name):
    """Carga el pipeline bajo demanda para evitar un ciclo de imports."""
    if name in {"TranslationPipeline", "TranslationProgress"}:
        from src.core.pipeline import TranslationPipeline, TranslationProgress
        return {
            "TranslationPipeline": TranslationPipeline,
            "TranslationProgress": TranslationProgress,
        }[name]
    raise AttributeError(f"module {__name__!r} has no attribute {name!r}")
