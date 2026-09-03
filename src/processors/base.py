"""
Clase base abstracta para procesadores de archivos.
Define la interfaz común que deben implementar todos los procesadores.
"""
from abc import ABC, abstractmethod
from typing import List, Optional
import uuid
import re

from src.core.models import Document, Section, SectionType, FileType
from src.utils.logger import get_logger

logger = get_logger(__name__)


class FileProcessingError(Exception):
    """Error genérico durante el procesamiento de un archivo."""
    pass


class CorruptedFileError(FileProcessingError):
    """El archivo está corrupto o no se puede leer."""
    pass


class PasswordProtectedError(FileProcessingError):
    """El archivo está protegido con contraseña."""
    pass


class BaseFileProcessor(ABC):
    """
    Clase base abstracta para procesadores de archivos.
    Se encarga de extraer texto y detectar secciones.
    """

    # Palabras clave para detectar secciones estándar (inglés)
    SECTION_KEYWORDS = {
        SectionType.ABSTRACT: ['abstract', 'summary', 'executive summary'],
        SectionType.INTRODUCTION: ['introduction', 'background', 'motivation', '1. introduction'],
        SectionType.METHODOLOGY: [
            'methodology', 'methods', 'materials and methods',
            'experimental setup', 'experimental procedures',
            '2. methodology', '2. methods',
        ],
        SectionType.RESULTS: [
            'results', 'experimental results', 'findings',
            '3. results',
        ],
        SectionType.DISCUSSION: [
            'discussion', 'analysis', 'discussion and analysis',
            '4. discussion',
        ],
        SectionType.CONCLUSIONS: [
            'conclusions', 'conclusion', 'summary and conclusions',
            'final remarks', 'closing remarks',
            '5. conclusions', '6. conclusions',
        ],
        SectionType.REFERENCES: [
            'references', 'bibliography', 'works cited',
            'literature cited',
        ],
        SectionType.ACKNOWLEDGMENTS: [
            'acknowledgments', 'acknowledgements', 'funding',
        ],
        SectionType.APPENDIX: [
            'appendix', 'appendices', 'supplementary material',
        ],
    }

    def __init__(self):
        self.section_counter = 0

    @abstractmethod
    def can_handle(self, file_type: FileType) -> bool:
        """Indica si este procesador puede manejar el tipo de archivo."""
        pass

    @abstractmethod
    def extract_text(self, document: Document) -> str:
        """
        Extrae el texto completo del documento.
        Puede lanzar excepciones: CorruptedFileError, PasswordProtectedError.
        """
        pass

    @abstractmethod
    def get_page_count(self, document: Document) -> Optional[int]:
        """Devuelve el número de páginas si aplica."""
        pass

    def process(self, document: Document) -> Document:
        """
        Procesa el documento completo: extrae texto y detecta secciones.
        """
        logger.info(f"Procesando archivo: {document.filename} [{document.file_type.value}]")

        try:
            # Extraer texto
            full_text = self.extract_text(document)

            # Obtener número de páginas
            document.page_count = self.get_page_count(document)

            if not full_text or not full_text.strip():
                raise FileProcessingError("No se pudo extraer texto del archivo")

            # Detectar y crear secciones
            document.sections = self._detect_sections(full_text)

            # Estimar tokens
            document.estimated_tokens = sum(s.token_count for s in document.sections)

            logger.info(
                f"Procesado: {document.filename} | "
                f"Secciones: {len(document.sections)} | "
                f"Tokens estimados: {document.estimated_tokens} | "
                f"Páginas: {document.page_count}"
            )

            return document

        except (CorruptedFileError, PasswordProtectedError, FileProcessingError):
            raise
        except Exception as e:
            logger.exception(f"Error inesperado procesando {document.filename}")
            raise FileProcessingError(f"Error procesando archivo: {str(e)}")

    def _detect_sections(self, full_text: str) -> List[Section]:
        """
        Detecta secciones estándar en el texto y devuelve una lista de Section.
        Usa heurísticas basadas en palabras clave y patrones de formato.
        """
        lines = full_text.split('\n')
        sections: List[Section] = []
        current_section_type = SectionType.OTHER
        current_title = "Contenido"
        current_lines: List[str] = []

        def _add_section():
            if current_lines:
                section = Section(
                    section_id=f"sec_{self.section_counter}",
                    section_type=current_section_type,
                    title=current_title,
                    original_text="\n".join(current_lines).strip(),
                )
                sections.append(section)
                self.section_counter += 1

        for line in lines:
            stripped = line.strip()

            # Detectar encabezado de sección
            detected_type, detected_title = self._identify_section_header(stripped)

            if detected_type is not None:
                # Guardar sección anterior
                _add_section()
                current_section_type = detected_type
                current_title = detected_title
                current_lines = []
            else:
                current_lines.append(line)

        # Guardar última sección
        _add_section()

        # Si no se detectaron secciones o solo una, crear una estructura básica
        if len(sections) <= 1:
            sections = self._create_default_sections(full_text)

        return sections

    def _identify_section_header(self, line: str) -> tuple:
        """
        Intenta identificar una línea como encabezado de sección.
        Returns: (SectionType o None, título detectado o None)
        """
        if not line or len(line) > 150:
            return None, None

        line_lower = line.lower().strip()

        # Limpiar números de sección comunes (1., 2.1, etc.)
        cleaned = re.sub(r'^\d+(\.\d+)*\s*\.?\s*', '', line_lower).strip()

        for section_type, keywords in self.SECTION_KEYWORDS.items():
            for kw in keywords:
                if cleaned == kw or line_lower == kw:
                    # Formatear título
                    title = line.strip()
                    title = re.sub(r'^\d+(\.\d+)*\s*\.?\s*', '', title).strip()
                    title = title.capitalize() if title.islower() else title
                    return section_type, title

        return None, None

    def _create_default_sections(self, full_text: str) -> List[Section]:
        """
        Crea una estructura de secciones por defecto cuando no se detectan.
        Divide el texto en fragmentos lógicos.
        """
        sections: List[Section] = []

        # Intentar extraer abstract (primer párrafo corto)
        paragraphs = re.split(r'\n\s*\n', full_text)

        if paragraphs:
            # Primer párrafo como abstract si es corto
            first = paragraphs[0].strip()
            if 50 < len(first) < 2000:
                sections.append(Section(
                    section_id=f"sec_{self.section_counter}",
                    section_type=SectionType.ABSTRACT,
                    title="Resumen / Abstract",
                    original_text=first,
                ))
                self.section_counter += 1
                remaining = "\n\n".join(paragraphs[1:])
            else:
                remaining = full_text

            # Resto como contenido principal
            if remaining.strip():
                sections.append(Section(
                    section_id=f"sec_{self.section_counter}",
                    section_type=SectionType.OTHER,
                    title="Contenido principal",
                    original_text=remaining.strip(),
                ))
                self.section_counter += 1

        return sections

    def _generate_section_id(self) -> str:
        """Genera un ID único para una sección."""
        return f"sec_{uuid.uuid4().hex[:12]}"
