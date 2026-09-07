import logging
from pathlib import Path

logging.disable(logging.CRITICAL)

from src.core.models import Document, FileType
from src.processors.format_agent import FormatAgent, FormatAgentConfig
from src.utils.config import load_config
from src.utils.exporter import DocumentExporter

root = next(path for path in Path.cwd().iterdir() if path.is_dir() and path.name.upper().startswith("ART"))
source = root / "ARTICULO 1.pdf"
config = load_config()
api_key = config.get("providers", {}).get("gemini", {}).get("api_key", "")
model = config.get("providers", {}).get("gemini", {}).get("model", "gemini-3.1-flash-lite")
if not api_key:
    raise RuntimeError("No hay clave Gemini configurada")
out = Path("test_results") / "format_agent_article1_gemini"
out.mkdir(parents=True, exist_ok=True)
document = Document(source.stem, source.name, FileType.PDF, source.stat().st_size, source.read_bytes())
agent = FormatAgent(FormatAgentConfig(mode="gemini", model=model, requests_per_minute=4, max_words_per_request=2800), api_key=api_key)
processed = agent.process(document)
path = DocumentExporter(out).export_to_pdf(processed, out)
print(f"PDF={path}")
print(f"SECTIONS={len(processed.sections)}")
print(f"REFERENCES={sum(1 for section in processed.sections if section.section_type.value == 'references')}")
print(f"CHARS={len(processed.full_original_text)}")
