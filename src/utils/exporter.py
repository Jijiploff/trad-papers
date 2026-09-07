# exporter.py - Versión con exportación a PDF usando reportlab

"""
Módulo de exportación. Genera archivos traducidos en múltiples formatos:
- TXT: texto plano
- DOCX: formato Word con estilo académico
- PDF: formato PDF con estilo académico
- LaTeX: preservando estructura original
- ZIP: paquete consolidado de múltiples archivos
"""
import os
import zipfile
import tempfile
from pathlib import Path
from typing import List, Optional, Dict, Any
from datetime import datetime

from src.core.models import Document, FileType
from src.utils.logger import get_logger

logger = get_logger(__name__)


class DocumentExporter:
    """Maneja la exportación de documentos traducidos a varios formatos."""

    def __init__(self, export_dir: str = "exports"):
        self.export_dir = Path(export_dir)
        self.export_dir.mkdir(parents=True, exist_ok=True)

    def _generate_filename(self, document: Document, suffix: str = "", ext: str = "txt") -> str:
        """Genera un nombre de archivo seguro para exportación."""
        base = Path(document.filename).stem
        base = "".join(c if c.isalnum() or c in '-_ ' else '_' for c in base)
        base = base.strip().replace(' ', '_')
        timestamp = datetime.now().strftime("%Y%m%d_%H%M%S")
        if suffix:
            return f"{base}_{suffix}_{timestamp}.{ext}"
        return f"{base}_{timestamp}.{ext}"

    def export_to_txt(self, document: Document, output_dir: Optional[Path] = None, original_only: bool = False) -> Path:
        """Exporta la traducción a un archivo de texto plano."""
        output_dir = output_dir or self.export_dir
        filename = self._generate_filename(document, suffix="traducido", ext="txt")
        output_path = output_dir / filename

        lines = []
        lines.append(f"Título original: {document.filename}")
        lines.append(f"Traducido el: {datetime.now().strftime('%Y-%m-%d %H:%M:%S')}")
        lines.append(f"Proveedor: {document.provider_used.value if document.provider_used else 'N/A'}")
        lines.append("=" * 80)
        lines.append("")

        for section in document.sections:
            if section.title:
                lines.append(f"=== {section.title.upper()} ===")
                lines.append("")
            if section.translated_text and not original_only:
                lines.append(section.translated_text)
            else:
                lines.append(section.original_text)
            lines.append("")
            lines.append("")

        with open(output_path, 'w', encoding='utf-8') as f:
            f.write("\n".join(lines))

        logger.info(f"Exportado TXT: {output_path}")
        return output_path

    def export_to_pdf(self, document: Document, output_dir: Optional[Path] = None, original_only: bool = False) -> Path:
        """
        Exporta la traducción a PDF con formato académico.
        Usa reportlab para generar PDF nativo sin dependencias externas.
        """
        try:
            from reportlab.lib.pagesizes import letter
            from reportlab.lib.styles import getSampleStyleSheet, ParagraphStyle
            from reportlab.lib.units import inch
            from reportlab.lib.enums import TA_CENTER, TA_LEFT, TA_JUSTIFY
            from reportlab.platypus import SimpleDocTemplate, Paragraph, Spacer, PageBreak, KeepTogether, Table, TableStyle
            from reportlab.lib import colors
            from reportlab.pdfbase import pdfmetrics
            from reportlab.pdfbase.ttfonts import TTFont
            from reportlab.lib.fonts import addMapping
        except ImportError:
            # Fallback: Intentar convertir DOCX a PDF con docx2pdf
            logger.warning("reportlab no instalado. Intentando convertir DOCX a PDF...")
            return self._export_pdf_via_docx(document, output_dir)

        output_dir = output_dir or self.export_dir
        filename = self._generate_filename(document, suffix="traducido", ext="pdf")
        output_path = output_dir / filename

        # Crear el PDF
        doc = SimpleDocTemplate(
            str(output_path),
            pagesize=letter,
            rightMargin=72,
            leftMargin=72,
            topMargin=72,
            bottomMargin=72,
        )

        styles = getSampleStyleSheet()
        
        # Crear estilos personalizados
        title_style = ParagraphStyle(
            'CustomTitle',
            parent=styles['Title'],
            fontSize=16,
            alignment=TA_CENTER,
            spaceAfter=12,
            fontName='Helvetica-Bold',
        )
        
        heading_style = ParagraphStyle(
            'CustomHeading',
            parent=styles['Heading1'],
            fontSize=14,
            alignment=TA_LEFT,
            spaceAfter=6,
            spaceBefore=12,
            fontName='Helvetica-Bold',
        )
        
        body_style = ParagraphStyle(
            'CustomBody',
            parent=styles['Normal'],
            fontSize=11,
            alignment=TA_JUSTIFY,
            spaceAfter=6,
            fontName='Helvetica',
        )
        
        meta_style = ParagraphStyle(
            'MetaStyle',
            parent=styles['Normal'],
            fontSize=9,
            alignment=TA_CENTER,
            spaceAfter=6,
            fontName='Helvetica-Oblique',
            textColor='gray',
        )

        story = []

        # Portada
        story.append(Paragraph(f"<b>{Path(document.filename).stem}</b>", title_style))
        story.append(Spacer(1, 0.25 * inch))
        if original_only:
            document_label = "Documento preprocesado con MinerU"
        else:
            document_label = "Documento Traducido Automáticamente"
        story.append(Paragraph(document_label, meta_style))
        story.append(Spacer(1, 0.1 * inch))
        story.append(Paragraph(f"Fecha: {datetime.now().strftime('%d de %B de %Y')}", meta_style))
        story.append(Spacer(1, 0.1 * inch))
        engine = "MINERU" if original_only else (
            document.provider_used.value.upper() if document.provider_used else "N/A"
        )
        story.append(Paragraph(f"Motor: {engine}", meta_style))
        story.append(PageBreak())

        layout_elements = document.metadata.get("layout_elements", [])
        if layout_elements:
            for element in layout_elements:
                self._append_layout_element(
                    story, element, heading_style, body_style, colors, Table, TableStyle,
                    original_only=original_only,
                )
            doc.build(story)
            logger.info(f"Exportado PDF estructurado: {output_path}")
            return output_path

        # Contenido
        for section in document.sections:
            if not section.translated_text and not section.original_text:
                continue

            text = section.translated_text if section.translated_text else section.original_text

            # Título de sección
            if section.title:
                story.append(Paragraph(f"<b>{section.title}</b>", heading_style))
                story.append(Spacer(1, 0.1 * inch))

            # Párrafos del contenido
            paragraphs = text.split('\n\n')
            for para_text in paragraphs:
                para_text = para_text.strip()
                if not para_text:
                    continue
                # Escapar caracteres especiales para reportlab
                para_text = para_text.replace('&', '&amp;').replace('<', '&lt;').replace('>', '&gt;')
                story.append(Paragraph(para_text, body_style))
                story.append(Spacer(1, 0.05 * inch))

            story.append(Spacer(1, 0.2 * inch))

        # Construir el PDF
        doc.build(story)
        logger.info(f"Exportado PDF: {output_path}")
        return output_path

    @staticmethod
    def _append_layout_element(story, element, heading_style, body_style, colors, Table, TableStyle, original_only=False):
        """Renderiza un elemento sin convertir su estructura en texto corrido."""
        from reportlab.platypus import Paragraph, Spacer

        element_type = element.get("type", "paragraph")
        content = (
            element.get("content", "")
            if original_only
            else element.get("translated_content") or element.get("content", "")
        )
        if not content.strip():
            return

        from xml.sax.saxutils import escape

        if element_type == "section_title":
            story.append(Paragraph(escape(content), heading_style))
            story.append(Spacer(1, 6))
            return

        if element_type == "table":
            rows = []
            for line in content.splitlines():
                if set(line.replace("|", "").strip()) <= {"-", ":", " "}:
                    continue
                cells = [cell.strip() for cell in line.strip().strip("|").split("|")]
                rows.append([Paragraph(escape(cell), body_style) for cell in cells])
            if rows:
                table = Table(rows, repeatRows=1, hAlign="LEFT")
                table.setStyle(TableStyle([
                    ("GRID", (0, 0), (-1, -1), 0.4, colors.grey),
                    ("BACKGROUND", (0, 0), (-1, 0), colors.whitesmoke),
                    ("VALIGN", (0, 0), (-1, -1), "TOP"),
                    ("LEFTPADDING", (0, 0), (-1, -1), 5),
                    ("RIGHTPADDING", (0, 0), (-1, -1), 5),
                ]))
                story.append(table)
                story.append(Spacer(1, 10))
            return

        if element_type == "equation":
            story.append(Paragraph(f"<font name='Courier'>{escape(content).replace(chr(10), '<br/>')}</font>", body_style))
            story.append(Spacer(1, 8))
            return

        if element_type == "figure":
            story.append(Paragraph(f"<b>[Figura preservada]</b> {escape(content)}", body_style))
            story.append(Spacer(1, 10))
            return

        if element_type == "reference":
            story.append(Paragraph(escape(content), body_style))
            story.append(Spacer(1, 4))
            return

        story.append(Paragraph(escape(content).replace("\n", "<br/>"), body_style))
        story.append(Spacer(1, 6))

    def _export_pdf_via_docx(self, document: Document, output_dir: Optional[Path] = None) -> Path:
        """
        Método alternativo: Exporta a DOCX y luego convierte a PDF usando docx2pdf.
        Requiere: pip install docx2pdf (necesita Microsoft Word o LibreOffice)
        """
        try:
            # Primero exportar a DOCX
            docx_path = self.export_to_docx(document, output_dir)
            
            # Convertir a PDF usando docx2pdf
            from docx2pdf import convert
            pdf_path = docx_path.with_suffix('.pdf')
            convert(str(docx_path), str(pdf_path))
            
            logger.info(f"Exportado PDF (vía DOCX): {pdf_path}")
            return pdf_path
            
        except ImportError:
            raise ImportError(
                "Para exportar a PDF necesitas instalar:\n"
                "  - Opción 1 (ligera): pip install reportlab\n"
                "  - Opción 2 (con Word): pip install docx2pdf"
            )
        except Exception as e:
            logger.error(f"Error convirtiendo a PDF: {e}")
            # Fallback: guardar como DOCX y advertir
            logger.warning("No se pudo generar PDF. Se exportó como DOCX en su lugar.")
            return docx_path

    def export_to_docx(self, document: Document, output_dir: Optional[Path] = None, original_only: bool = False) -> Path:
        """
        Exporta la traducción a DOCX con formato académico estándar.
        Incluye: portada, encabezados, cuerpo con estilos, citas preservadas.
        """
        try:
            from docx import Document as DocxDocument
            from docx.shared import Pt, Inches, RGBColor
            from docx.enum.text import WD_ALIGN_PARAGRAPH
            from docx.oxml.ns import qn
        except ImportError:
            raise ImportError("python-docx es requerido para exportar a DOCX. Instálalo con: pip install python-docx")

        output_dir = output_dir or self.export_dir
        filename = self._generate_filename(document, suffix="traducido", ext="docx")
        output_path = output_dir / filename

        doc = DocxDocument()

        # Configurar estilos base
        style = doc.styles['Normal']
        style.font.name = 'Times New Roman'
        style.font.size = Pt(12)
        style.paragraph_format.line_spacing = 1.5
        style.paragraph_format.space_after = Pt(6)

        # Márgenes
        for section in doc.sections:
            section.top_margin = Inches(1)
            section.bottom_margin = Inches(1)
            section.left_margin = Inches(1.25)
            section.right_margin = Inches(1.25)

        # Título del documento
        title = doc.add_heading(Path(document.filename).stem, level=0)
        title.alignment = WD_ALIGN_PARAGRAPH.CENTER
        for run in title.runs:
            run.font.name = 'Times New Roman'
            run.font.size = Pt(16)
            run.bold = True

        # Metadatos
        meta_para = doc.add_paragraph()
        meta_para.alignment = WD_ALIGN_PARAGRAPH.CENTER
        meta_run = meta_para.add_run(
            f"\nDocumento traducido automáticamente\n"
            f"Fecha: {datetime.now().strftime('%d de %B de %Y')}\n"
            f"Motor de traducción: {document.provider_used.value.upper() if document.provider_used else 'N/A'}"
        )
        meta_run.font.name = 'Times New Roman'
        meta_run.font.size = Pt(10)
        meta_run.italic = True
        meta_run.font.color.rgb = RGBColor(100, 100, 100)

        doc.add_page_break()

        # Contenido por secciones
        for section in document.sections:
            if not section.translated_text and not section.original_text:
                continue

            text = (
                section.original_text
                if original_only
                else section.translated_text if section.translated_text else section.original_text
            )

            # Determinar nivel de encabezado
            section_type = section.section_type.value
            heading_map = {
                'title': 0,
                'abstract': 1,
                'introduction': 1,
                'methodology': 1,
                'results': 1,
                'discussion': 1,
                'conclusions': 1,
                'references': 1,
                'acknowledgments': 1,
                'appendix': 1,
                'other': 2,
            }
            level = heading_map.get(section_type, 2)

            if section.title:
                heading = doc.add_heading(section.title, level=level)
                for run in heading.runs:
                    run.font.name = 'Times New Roman'

            # Párrafos del contenido
            paragraphs = text.split('\n\n')
            for para_text in paragraphs:
                para_text = para_text.strip()
                if not para_text:
                    continue
                p = doc.add_paragraph()
                p.paragraph_format.first_line_indent = Inches(0.5)
                run = p.add_run(para_text)
                run.font.name = 'Times New Roman'
                run.font.size = Pt(12)

        doc.save(str(output_path))
        logger.info(f"Exportado DOCX: {output_path}")
        return output_path

    def export_to_latex(self, document: Document, output_dir: Optional[Path] = None, original_only: bool = False) -> Path:
        """Exporta la traducción preservando formato LaTeX cuando corresponde."""
        output_dir = output_dir or self.export_dir
        filename = self._generate_filename(document, suffix="traducido", ext="tex")
        output_path = output_dir / filename

        lines = []
        lines.append("% LaTeX document - Translated by Paper Translator")
        lines.append(f"% Original: {document.filename}")
        lines.append(f"% Date: {datetime.now().strftime('%Y-%m-%d')}")
        lines.append("")
        lines.append("\\documentclass[12pt,a4paper]{article}")
        lines.append("\\usepackage[spanish]{babel}")
        lines.append("\\usepackage[utf8]{inputenc}")
        lines.append("\\usepackage[T1]{fontenc}")
        lines.append("\\usepackage{amsmath,amssymb}")
        lines.append("\\usepackage{graphicx}")
        lines.append("\\usepackage{hyperref}")
        lines.append("")
        lines.append("\\title{" + Path(document.filename).stem + "}")
        lines.append("\\author{Traducción automática}")
        lines.append("\\date{\\today}")
        lines.append("")
        lines.append("\\begin{document}")
        lines.append("\\maketitle")
        lines.append("")

        section_env_map = {
            'abstract': 'abstract',
            'introduction': 'section',
            'methodology': 'section',
            'results': 'section',
            'discussion': 'section',
            'conclusions': 'section',
            'references': 'section',
            'acknowledgments': 'section',
            'appendix': 'section',
            'other': 'subsection',
            'title': 'title',
        }

        for section in document.sections:
            text = (
                section.original_text
                if original_only
                else section.translated_text if section.translated_text else section.original_text
            )
            if not text.strip():
                continue

            stype = section.section_type.value
            env = section_env_map.get(stype, 'section')

            if stype == 'title':
                continue  # Ya incluido en \title

            if stype == 'abstract':
                lines.append("\\begin{abstract}")
                lines.append(text)
                lines.append("\\end{abstract}")
            else:
                lines.append(f"\\{env}{{{section.title or stype.capitalize()}}}")
                lines.append(text)
            lines.append("")

        lines.append("\\end{document}")

        with open(output_path, 'w', encoding='utf-8') as f:
            f.write("\n".join(lines))

        logger.info(f"Exportado LaTeX: {output_path}")
        return output_path

    def export_original_format(self, document: Document, output_dir: Optional[Path] = None) -> Path:
        """
        Exporta en el formato más apropiado según el tipo de archivo original.
        Ahora incluye PDF como opción para documentos de texto.
        """
        if document.file_type == FileType.PDF:
            return self.export_to_pdf(document, output_dir)  # ✅ Ahora exporta PDF
        elif document.file_type == FileType.DOCX:
            return self.export_to_docx(document, output_dir)
        elif document.file_type == FileType.TXT:
            return self.export_to_txt(document, output_dir)
        elif document.file_type == FileType.LATEX:
            return self.export_to_latex(document, output_dir)
        else:
            return self.export_to_txt(document, output_dir)

    def export_all_formats(
        self, 
        document: Document, 
        output_dir: Optional[Path] = None,
        formats: List[str] = ["txt", "docx", "pdf"],
        original_only: bool = False,
    ) -> List[Path]:
        """
        Exporta el documento en múltiples formatos a la vez.
        
        Args:
            document: Documento a exportar
            output_dir: Directorio de salida
            formats: Lista de formatos a exportar: "txt", "docx", "pdf", "latex"
        
        Returns:
            Lista de rutas de los archivos exportados
        """
        output_dir = output_dir or self.export_dir
        exported = []
        
        format_map = {
            "txt": self.export_to_txt,
            "docx": self.export_to_docx,
            "pdf": self.export_to_pdf,
            "latex": self.export_to_latex,
        }
        
        for fmt in formats:
            fmt = fmt.lower().strip()
            if fmt in format_map:
                try:
                    path = format_map[fmt](document, output_dir, original_only=original_only)
                    exported.append(path)
                except Exception as e:
                    logger.error(f"Error exportando a {fmt}: {e}")
            else:
                logger.warning(f"Formato no soportado: {fmt}")
        
        return exported

    def create_zip_bundle(self, exported_paths: List[Path], zip_name: Optional[str] = None) -> Path:
        """Crea un archivo ZIP con todos los documentos exportados."""
        if not zip_name:
            timestamp = datetime.now().strftime("%Y%m%d_%H%M%S")
            zip_name = f"traducciones_{timestamp}.zip"

        zip_path = self.export_dir / zip_name

        with zipfile.ZipFile(zip_path, 'w', zipfile.ZIP_DEFLATED) as zf:
            for path in exported_paths:
                if path.exists():
                    zf.write(str(path), arcname=path.name)

        logger.info(f"ZIP creado: {zip_path} ({len(exported_paths)} archivos)")
        return zip_path