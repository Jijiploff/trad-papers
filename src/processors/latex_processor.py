"""
Procesador para archivos LaTeX (.tex).
Extrae texto preservando comandos matemáticos y estructura.
"""
import re
from typing import Optional

from src.core.models import FileType, SectionType, Section
from src.processors.base import (
    BaseFileProcessor,
    CorruptedFileError,
    FileProcessingError,
)
from src.utils.logger import get_logger

logger = get_logger(__name__)


class LatexProcessor(BaseFileProcessor):
    """Procesador de archivos LaTeX."""

    # Mapeo de comandos LaTeX a tipos de sección
    LATEX_SECTION_COMMANDS = {
        'title': SectionType.TITLE,
        'abstract': SectionType.ABSTRACT,
        'section': SectionType.OTHER,
        'subsection': SectionType.OTHER,
        'subsubsection': SectionType.OTHER,
    }

    # Comandos que deben preservarse literalmente (matemáticas, citas, referencias)
    PROTECTED_COMMANDS = [
        r'\\cite[tp]?\{[^}]+\}',
        r'\\ref\{[^}]+\}',
        r'\\eqref\{[^}]+\}',
        r'\\label\{[^}]+\}',
        r'\\begin\{equation\}[\s\S]*?\\end\{equation\}',
        r'\\begin\{align\}[\s\S]*?\\end\{align\}',
        r'\\begin\{eqnarray\}[\s\S]*?\\end\{eqnarray\}',
        r'\\begin\{table\}[\s\S]*?\\end\{table\}',
        r'\\begin\{figure\}[\s\S]*?\\end\{figure\}',
        r'\\begin\{tabular\}[\s\S]*?\\end\{tabular\}',
        r'\$\$[\s\S]*?\$\$',
        r'\$[^$\n]+\$',
        r'\\\[[\s\S]*?\\\]',
        r'\\\([\s\S]*?\\\)',
    ]

    def can_handle(self, file_type: FileType) -> bool:
        return file_type == FileType.LATEX

    def extract_text(self, document) -> str:
        """Extrae texto de un archivo LaTeX preservando elementos importantes."""
        encodings = ['utf-8', 'latin-1']

        text = None
        for encoding in encodings:
            try:
                text = document.content.decode(encoding)
                break
            except UnicodeDecodeError:
                continue

        if text is None:
            raise CorruptedFileError("No se pudo decodificar el archivo LaTeX")

        # Limpiar comentarios de LaTeX (líneas que empiezan con %)
        lines = text.split('\n')
        cleaned_lines = []
        for line in lines:
            # Eliminar comentarios pero preservar % dentro de comandos
            if '%' in line:
                # Buscar % no escapado
                idx = 0
                while idx < len(line):
                    if line[idx] == '%' and (idx == 0 or line[idx - 1] != '\\'):
                        line = line[:idx]
                        break
                    idx += 1
            cleaned_lines.append(line)

        cleaned_text = '\n'.join(cleaned_lines)

        # Estimar páginas
        word_count = len(re.findall(r'\b\w+\b', cleaned_text))
        self._page_count = max(1, word_count // 400)

        return cleaned_text

    def _detect_sections(self, full_text: str) -> list:
        """
        Sobreescribe la detección de secciones para usar comandos LaTeX nativos:
        \section{}, \subsection{}, \begin{abstract}, etc.
        """
        sections: list = []
        current_type = SectionType.OTHER
        current_title = "Contenido"
        current_content_parts = []

        # Patrones para detectar secciones
        section_patterns = [
            (r'\\section\*?\{([^}]+)\}', SectionType.OTHER, 1),
            (r'\\subsection\*?\{([^}]+)\}', SectionType.OTHER, 2),
            (r'\\subsubsection\*?\{([^}]+)\}', SectionType.OTHER, 3),
            (r'\\chapter\*?\{([^}]+)\}', SectionType.OTHER, 0),
        ]

        # Buscar entorno abstract
        abstract_match = re.search(
            r'\\begin\{abstract\}([\s\S]*?)\\end\{abstract\}',
            full_text
        )

        processed_pos = 0

        if abstract_match:
            sections.append(Section(
                section_id=f"sec_{self.section_counter}",
                section_type=SectionType.ABSTRACT,
                title="Abstract",
                original_text=abstract_match.group(1).strip(),
            ))
            self.section_counter += 1
            processed_pos = abstract_match.end()

        # Encontrar todas las secciones en el resto del texto
        remaining = full_text[processed_pos:]

        # Encontrar todos los comandos de sección
        matches = []
        for pattern, sec_type, level in section_patterns:
            for m in re.finditer(pattern, remaining):
                matches.append((m.start(), m.end(), m.group(1), sec_type, level))

        matches.sort(key=lambda x: x[0])

        if not matches:
            # Sin secciones detectadas, usar método padre
            return super()._detect_sections(full_text)

        last_end = 0
        current_title = "Introducción"
        current_type = SectionType.INTRODUCTION

        for start, end, title, sec_type, level in matches:
            # Guardar contenido anterior
            if start > last_end:
                content = remaining[last_end:start].strip()
                if content:
                    sections.append(Section(
                        section_id=f"sec_{self.section_counter}",
                        section_type=current_type,
                        title=current_title,
                        original_text=content,
                    ))
                    self.section_counter += 1

            # Nueva sección
            current_title = self._clean_latex_text(title)
            current_type = self._classify_section_title(current_title)
            last_end = end

        # Guardar última sección
        if last_end < len(remaining):
            content = remaining[last_end:].strip()
            if content:
                sections.append(Section(
                    section_id=f"sec_{self.section_counter}",
                    section_type=current_type,
                    title=current_title,
                    original_text=content,
                ))
                self.section_counter += 1

        return sections

    def _clean_latex_text(self, text: str) -> str:
        """Elimina comandos LaTeX simples de un texto."""
        # Eliminar \textit{}, \textbf{}, etc.
        text = re.sub(r'\\(textbf|textit|emph|textsc|textrm|textsf)\{([^}]+)\}', r'\2', text)
        return text.strip()

    def _classify_section_title(self, title: str) -> SectionType:
        """Clasifica un título de sección según su contenido."""
        title_lower = title.lower()

        for section_type, keywords in self.SECTION_KEYWORDS.items():
            for kw in keywords:
                if kw in title_lower:
                    return section_type

        return SectionType.OTHER

    def get_page_count(self, document) -> Optional[int]:
        if hasattr(self, '_page_count'):
            return self._page_count
        return None
