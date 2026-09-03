"""
Procesador para archivos PDF.
Usa PyPDF2 o pdfplumber para extraer texto de manera robusta.
Incluye detección automática de encabezados y pies de página.
"""
import io
import re
from typing import Optional, List, Dict, Tuple
from collections import Counter

from src.core.models import FileType
from src.processors.base import (
    BaseFileProcessor,
    CorruptedFileError,
    PasswordProtectedError,
    FileProcessingError,
)
from src.utils.logger import get_logger

logger = get_logger(__name__)


class PdfProcessor(BaseFileProcessor):
    """Procesador de archivos PDF con detección de encabezados y pies de página."""

    # Patrones comunes de encabezados y pies de página
    HEADER_FOOTER_PATTERNS = [
        r'^\s*\d+\s*$',  # Solo número de página
        r'^\s*Página\s+\d+\s*$',  # "Página X"
        r'^\s*Page\s+\d+\s*$',  # "Page X"
        r'^\s*\d+\s*/\s*\d+\s*$',  # "X/Y"
        r'^\s*Copyright\s+©?\s*\d{4}\s*',  # Copyright
        r'^\s*©\s*\d{4}\s*',  # © año
        r'^\s*Todos\s+los\s+derechos\s+reservados',  # Derechos reservados
        r'^\s*All\s+rights\s+reserved',  # All rights reserved
        r'^\s*Confidencial\s*$',  # Confidencial
        r'^\s*Confidential\s*$',  # Confidential
        r'^\s*Draft\s*$',  # Draft
        r'^\s*Borrador\s*$',  # Borrador
        r'^\s*Página\s+\d+\s+de\s+\d+\s*$',  # "Página X de Y"
        r'^\s*Page\s+\d+\s+of\s+\d+\s*$',  # "Page X of Y"
    ]

    # Umbral para considerar un texto como encabezado/pie de página
    # Si aparece en más del 30% de las páginas, se considera repetitivo
    REPETITION_THRESHOLD = 0.30

    def __init__(self, *args, **kwargs):
        super().__init__(*args, **kwargs)
        self._pages_text: List[str] = []
        self._page_count = 0
        self._header_footer_patterns = self.HEADER_FOOTER_PATTERNS.copy()

    def can_handle(self, file_type: FileType) -> bool:
        return file_type == FileType.PDF

    def extract_text(self, document) -> str:
        """Extrae texto de un PDF excluyendo encabezados y pies de página."""
        try:
            import pdfplumber
        except ImportError:
            pdfplumber = None

        try:
            from PyPDF2 import PdfReader
        except ImportError:
            PdfReader = None

        if pdfplumber is None and PdfReader is None:
            raise FileProcessingError(
                "Se requiere pdfplumber o PyPDF2 para procesar PDFs. "
                "Instálalos con: pip install pdfplumber pypdf"
            )

        pdf_bytes = io.BytesIO(document.content)

        # Intentar con pdfplumber primero (mejor calidad)
        if pdfplumber:
            try:
                return self._extract_with_pdfplumber(pdf_bytes)
            except Exception as e:
                logger.warning(f"pdfplumber falló, intentando PyPDF2: {e}")

        # Fallback a PyPDF2
        if PdfReader:
            return self._extract_with_pypdf(pdf_bytes)

        raise FileProcessingError("No se pudo extraer texto del PDF")

    def _extract_with_pdfplumber(self, pdf_bytes: io.BytesIO) -> str:
        import pdfplumber

        try:
            with pdfplumber.open(pdf_bytes) as pdf:
                # Verificar si está encriptado
                try:
                    if hasattr(pdf, 'is_encrypted') and pdf.is_encrypted:
                        raise PasswordProtectedError(
                            "El PDF está protegido con contraseña."
                        )
                except Exception:
                    pass

                self._page_count = len(pdf.pages)
                self._pages_text = []

                # Extraer texto de cada página
                for page in pdf.pages:
                    page_text = page.extract_text() or ""
                    self._pages_text.append(page_text)

                # Detectar y eliminar encabezados y pies de página
                clean_pages = self._remove_headers_and_footers(self._pages_text)

                return "\n\n".join(clean_pages)

        except PasswordProtectedError:
            raise
        except Exception as e:
            raise CorruptedFileError(f"PDF corrupto o ilegible: {str(e)}")

    def _extract_with_pypdf(self, pdf_bytes: io.BytesIO) -> str:
        from PyPDF2 import PdfReader
        from PyPDF2.errors import PdfReadError

        try:
            reader = PdfReader(pdf_bytes)

            if reader.is_encrypted:
                raise PasswordProtectedError(
                    "El PDF está protegido con contraseña."
                )

            self._page_count = len(reader.pages)
            self._pages_text = []

            for page in reader.pages:
                try:
                    page_text = page.extract_text() or ""
                    self._pages_text.append(page_text)
                except Exception as e:
                    logger.warning(f"Error extrayendo página: {e}")
                    self._pages_text.append("")

            # Detectar y eliminar encabezados y pies de página
            clean_pages = self._remove_headers_and_footers(self._pages_text)

            return "\n\n".join(clean_pages)

        except PasswordProtectedError:
            raise
        except PdfReadError as e:
            raise CorruptedFileError(f"PDF corrupto o ilegible: {str(e)}")
        except Exception as e:
            raise FileProcessingError(f"Error procesando PDF: {str(e)}")

    def _remove_headers_and_footers(self, pages: List[str]) -> List[str]:
        """
        Detecta y elimina encabezados y pies de página de todas las páginas.
        
        Estrategia:
        1. Divide cada página en líneas
        2. Detecta líneas repetitivas que aparecen en varias páginas
        3. Identifica líneas en posiciones consistentes (primera/última línea)
        4. Elimina esas líneas
        """
        if len(pages) < 2:
            # Con una sola página, no podemos detectar patrones
            return pages

        # Dividir cada página en líneas
        page_lines = []
        for page in pages:
            lines = page.split('\n')
            # Eliminar líneas vacías al inicio y final
            while lines and not lines[0].strip():
                lines.pop(0)
            while lines and not lines[-1].strip():
                lines.pop()
            page_lines.append(lines)

        # Contar frecuencia de cada línea en todas las páginas
        all_lines = []
        for lines in page_lines:
            all_lines.extend([line.strip() for line in lines if line.strip()])
        
        line_counter = Counter(all_lines)
        total_pages = len(pages)
        repetition_threshold = max(2, int(total_pages * self.REPETITION_THRESHOLD))

        # Identificar líneas repetitivas (potenciales encabezados/pies)
        repetitive_lines = {
            line for line, count in line_counter.items()
            if count >= repetition_threshold and len(line) > 5  # Ignorar líneas muy cortas
        }

        # También identificar patrones de números de página
        pattern_lines = set()
        for pattern in self._header_footer_patterns:
            for line in all_lines:
                if re.match(pattern, line, re.IGNORECASE):
                    pattern_lines.add(line)

        repetitive_lines.update(pattern_lines)

        # Si no hay líneas repetitivas, no hacer nada
        if not repetitive_lines:
            logger.debug("No se detectaron encabezados o pies de página")
            return pages

        logger.debug(f"Detectadas {len(repetitive_lines)} líneas repetitivas")

        # Eliminar líneas repetitivas de cada página
        clean_pages = []
        for i, lines in enumerate(page_lines):
            # Si la página tiene pocas líneas, preservarla completa
            if len(lines) <= 3:
                clean_pages.append('\n'.join(lines))
                continue

            clean_lines = []
            for j, line in enumerate(lines):
                line_stripped = line.strip()
                
                # Verificar si es una línea repetitiva
                is_repetitive = line_stripped in repetitive_lines
                
                # Verificar si está en posición de encabezado (primeras 3 líneas)
                is_header = j < 3 and is_repetitive
                
                # Verificar si está en posición de pie (últimas 3 líneas)
                is_footer = j >= len(lines) - 3 and is_repetitive
                
                # Verificar si contiene solo números de página
                is_page_number = bool(re.match(r'^\s*\d+\s*$', line_stripped))
                
                # También verificar líneas que son exclusivamente números de página
                if is_page_number and (j < 4 or j >= len(lines) - 4):
                    is_footer = True

                # Si no es encabezado ni pie, preservar la línea
                if not (is_header or is_footer):
                    clean_lines.append(line)

            # Reconstruir la página
            clean_text = '\n'.join(clean_lines).strip()
            if clean_text:
                clean_pages.append(clean_text)
            else:
                # Si la página quedó vacía, mantener el original como fallback
                clean_pages.append('\n'.join(lines))

        logger.info(
            f"Eliminados encabezados/pies de página en {len(pages)} páginas. "
            f"Líneas repetitivas detectadas: {len(repetitive_lines)}"
        )

        return clean_pages

    def _extract_with_pdfplumber_advanced(self, pdf_bytes: io.BytesIO) -> str:
        """
        Versión avanzada usando pdfplumber con detección por coordenadas.
        Más preciso pero más lento.
        """
        import pdfplumber

        try:
            with pdfplumber.open(pdf_bytes) as pdf:
                if hasattr(pdf, 'is_encrypted') and pdf.is_encrypted:
                    raise PasswordProtectedError(
                        "El PDF está protegido con contraseña."
                    )

                self._page_count = len(pdf.pages)
                
                # Primero, extraer todas las páginas para análisis
                pages_text = []
                page_heights = []
                
                for page in pdf.pages:
                    page_text = page.extract_text() or ""
                    pages_text.append(page_text)
                    page_heights.append(page.height)

                # Detectar encabezados/pies basados en posición (coordenadas)
                # Esta es una versión mejorada que usa el bounding box
                clean_pages = []
                
                for i, page in enumerate(pdf.pages):
                    # Extraer objetos de texto con sus coordenadas
                    text_objects = page.extract_text_words(
                        x_tolerance=3,
                        y_tolerance=3,
                    )
                    
                    if not text_objects:
                        clean_pages.append(pages_text[i])
                        continue
                    
                    # Agrupar por posición vertical (y)
                    # Los encabezados suelen estar en el top 10% de la página
                    # Los pies en el bottom 10%
                    top_margin = page.height * 0.12  # 12% superior
                    bottom_margin = page.height * 0.12  # 12% inferior
                    
                    # Agrupar texto por línea (misma coordenada y)
                    lines = {}
                    for obj in text_objects:
                        y = round(obj['y0'])
                        if y not in lines:
                            lines[y] = []
                        lines[y].append(obj['text'])
                    
                    # Ordenar líneas por posición y
                    sorted_lines = []
                    for y in sorted(lines.keys()):
                        # Unir palabras de la misma línea
                        line_text = ' '.join(lines[y])
                        sorted_lines.append((y, line_text))
                    
                    # Identificar líneas en márgenes superior e inferior
                    clean_lines = []
                    for y, text in sorted_lines:
                        is_header = y < top_margin
                        is_footer = y > (page.height - bottom_margin)
                        
                        # Si es encabezado o pie, y es corto y repetitivo, omitir
                        if is_header or is_footer:
                            # Si es demasiado largo, podría ser contenido importante
                            if len(text) < 100:  # Umbral para encabezados
                                # Verificar si parece número de página
                                if re.match(r'^\s*\d+\s*$', text):
                                    continue
                                # Verificar si parece fecha o copyright
                                if re.search(r'\d{4}|copyright|©', text, re.IGNORECASE):
                                    continue
                                # Mantener si parece contenido relevante
                                if len(text) > 20 and not re.match(r'^[\d\s\-.:,]+$', text):
                                    clean_lines.append(text)
                            else:
                                clean_lines.append(text)
                        else:
                            clean_lines.append(text)
                    
                    clean_pages.append('\n'.join(clean_lines))

                return "\n\n".join(clean_pages)

        except PasswordProtectedError:
            raise
        except Exception as e:
            raise CorruptedFileError(f"Error procesando PDF: {str(e)}")

    def get_page_count(self, document) -> Optional[int]:
        """Devuelve el número de páginas detectado durante la extracción."""
        if hasattr(self, '_page_count') and self._page_count > 0:
            return self._page_count

        # Intentar obtener sin extraer todo el texto
        try:
            from PyPDF2 import PdfReader
            import io
            reader = PdfReader(io.BytesIO(document.content))
            return len(reader.pages)
        except Exception:
            return None

    def set_custom_patterns(self, patterns: List[str]):
        """Permite agregar patrones personalizados de encabezados/pies."""
        self._header_footer_patterns.extend(patterns)

    def set_repetition_threshold(self, threshold: float):
        """Ajusta el umbral de repetición (0.0 - 1.0)."""
        self.REPETITION_THRESHOLD = max(0.0, min(1.0, threshold))