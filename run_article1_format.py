import logging
from pathlib import Path

logging.disable(logging.CRITICAL)

from src.core.models import Document, FileType
from src.processors.format_agent import FormatAgent, FormatAgentConfig
from src.utils.exporter import DocumentExporter

root = next(path for path in Path.cwd().iterdir() if path.is_dir() and path.name.upper().startswith("ART"))
source = root / "ARTICULO 1.pdf"
out = Path("test_results") / "format_agent_article1_local"
out.mkdir(parents=True, exist_ok=True)
document = Document(source.stem, source.name, FileType.PDF, source.stat().st_size, source.read_bytes())
processed = FormatAgent(FormatAgentConfig(mode="local")).process(document)
path = DocumentExporter(out).export_to_pdf(processed, out)
print(f"PDF={path}")
print(f"SECTIONS={len(processed.sections)}")
print(f"REFERENCES={sum(1 for section in processed.sections if section.section_type == section.section_type.REFERENCES)}")
print(f"CHARS={len(processed.full_original_text)}")
