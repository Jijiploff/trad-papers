"""
Módulo de chunking inteligente para documentos largos.
Divide el texto en fragmentos manteniendo la coherencia semántica,
respetando límites de tokens y preservando elementos especiales
(ecuaciones, tablas, citas).
"""
import re
from typing import List, Tuple
from dataclasses import dataclass

from src.core.models import Section, TranslationChunk


# Patrones para identificar elementos que no deben romperse
EQUATION_PATTERNS = [
    r'\$\$[\s\S]*?\$\$',          # LaTeX display math
    r'\$[^$\n]+\$',               # LaTeX inline math
    r'\\\[[\s\S]*?\\\]',          # LaTeX display alt
    r'\\\([\s\S]*?\\\)',          # LaTeX inline alt
    r'\\begin\{equation\}[\s\S]*?\\end\{equation\}',
    r'\\begin\{align\}[\s\S]*?\\end\{align\}',
    r'\\begin\{eqnarray\}[\s\S]*?\\end\{eqnarray\}',
]

CITATION_PATTERNS = [
    r'\[[\d,\s\-]+\]',            # [1], [1,2], [1-5]
    r'\([A-Z][a-z]+(?:\s+and\s+[A-Z][a-z]+)?,\s*\d{4}(?:;\s*[^)]+)?\)',  # (Author, 2020)
    r'\\cite\{[^}]+\}',           # LaTeX \cite{}
    r'\\citep\{[^}]+\}',
    r'\\citet\{[^}]+\}',
]

TABLE_MARKERS = [
    r'\\begin\{table',
    r'\\end\{table',
    r'\\begin\{tabular',
    r'\\end\{tabular',
]


@dataclass
class ChunkingConfig:
    """Configuración para el algoritmo de chunking."""
    max_tokens: int = 3500
    overlap_tokens: int = 200
    min_chunk_tokens: int = 100
    respect_boundaries: bool = True


def estimate_tokens(text: str) -> int:
    """
    Estimación aproximada de tokens (4 caracteres ~ 1 token para GPT).
    Más conservador que el tokenizador real para evitar exceder límites.
    """
    if not text:
        return 0
    return max(1, len(text) // 4)


def find_safe_split_point(text: str, target_pos: int, lookback: int = 500) -> int:
    """
    Busca un punto de división seguro cerca de target_pos.
    Prefiere saltos de párrafo, luego oraciones, luego espacios.
    Evita dividir dentro de ecuaciones o citas.
    """
    if target_pos >= len(text):
        return len(text)

    # Buscar hacia atrás desde target_pos
    start_look = max(0, target_pos - lookback)
    search_region = text[start_look:target_pos + 1]

    # Patrones que no deben romperse
    protected_patterns = EQUATION_PATTERNS + CITATION_PATTERNS

    def is_in_protected(pos: int) -> bool:
        absolute_pos = start_look + pos
        for pattern in protected_patterns:
            for match in re.finditer(pattern, text):
                if match.start() <= absolute_pos < match.end():
                    return True
        return False

    # 1. Buscar salto de párrafo (doble salto de línea)
    for m in re.finditer(r'\n\s*\n', search_region):
        pos = m.end()
        if not is_in_protected(pos):
            return start_look + pos

    # 2. Buscar final de oración
    for m in re.finditer(r'[.!?]\s+', search_region):
        pos = m.end()
        if not is_in_protected(pos):
            return start_look + pos

    # 3. Buscar salto de línea simple
    for m in re.finditer(r'\n', search_region):
        pos = m.end()
        if not is_in_protected(pos):
            return start_look + pos

    # 4. Buscar espacio
    for m in re.finditer(r'\s', search_region):
        pos = m.end()
        if not is_in_protected(pos):
            return start_look + pos

    # Último recurso: dividir en target_pos
    return target_pos


def chunk_text(
    text: str,
    config: ChunkingConfig,
    section_id: str = "default",
) -> List[TranslationChunk]:
    """
    Divide un texto en chunks según la configuración.

    Args:
        text: Texto completo a dividir
        config: Configuración de chunking
        section_id: Identificador de la sección padre

    Returns:
        Lista de TranslationChunk
    """
    if not text or not text.strip():
        return []

    total_tokens = estimate_tokens(text)
    if total_tokens <= config.max_tokens:
        return [
            TranslationChunk(
                chunk_id=f"{section_id}_0",
                text=text,
                section_id=section_id,
                start_idx=0,
                end_idx=len(text),
                token_count=total_tokens,
            )
        ]

    chunks: List[TranslationChunk] = []
    current_pos = 0
    chunk_idx = 0

    while current_pos < len(text):
        # Calcular posición objetivo basada en tokens
        remaining = text[current_pos:]
        remaining_tokens = estimate_tokens(remaining)

        if remaining_tokens <= config.max_tokens:
            chunks.append(
                TranslationChunk(
                    chunk_id=f"{section_id}_{chunk_idx}",
                    text=remaining,
                    section_id=section_id,
                    start_idx=current_pos,
                    end_idx=len(text),
                    token_count=remaining_tokens,
                )
            )
            break

        # Estimar caracteres para max_tokens
        target_chars = config.max_tokens * 4
        target_pos = current_pos + target_chars

        # Encontrar punto seguro
        split_pos = find_safe_split_point(text, target_pos)
        if split_pos <= current_pos:
            split_pos = current_pos + target_chars  # Forzar división

        chunk_text_content = text[current_pos:split_pos]
        chunk_tokens = estimate_tokens(chunk_text_content)

        if chunk_tokens < config.min_chunk_tokens and chunk_idx > 0:
            # Fragmento muy pequeño, unir con el anterior si es posible
            if chunks:
                last = chunks[-1]
                last.text += chunk_text_content
                last.end_idx = split_pos
                last.token_count = estimate_tokens(last.text)
                current_pos = split_pos
                continue

        chunks.append(
            TranslationChunk(
                chunk_id=f"{section_id}_{chunk_idx}",
                text=chunk_text_content,
                section_id=section_id,
                start_idx=current_pos,
                end_idx=split_pos,
                token_count=chunk_tokens,
            )
        )

        # Aplicar solapamiento (overlap)
        if config.overlap_tokens > 0 and split_pos < len(text):
            overlap_chars = config.overlap_tokens * 4
            overlap_pos = max(current_pos, split_pos - overlap_chars)
            current_pos = overlap_pos
        else:
            current_pos = split_pos

        chunk_idx += 1

    return chunks


def chunk_document_sections(
    sections: List[Section],
    config: ChunkingConfig,
) -> List[TranslationChunk]:
    """
    Procesa todas las secciones de un documento y genera chunks.
    """
    all_chunks: List[TranslationChunk] = []
    for section in sections:
        section_chunks = chunk_text(
            section.original_text,
            config,
            section_id=section.section_id,
        )
        all_chunks.extend(section_chunks)
    return all_chunks
