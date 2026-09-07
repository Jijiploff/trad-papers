import logging
from pathlib import Path

logging.disable(logging.CRITICAL)

from src.core.models import Document, FileType
from src.processors.format_agent import FormatAgent, FormatAgentConfig
from src.utils.config import load_config
from src.utils.exporter import DocumentExporter

root = next(path for path in Path.cwd().iterdir() if path.is_dir() and path.name.upper().startswith("ART"))
out = Path("test_results") / "format_agent_10_gemini"
out.mkdir(parents=True, exist_ok=True)
config = load_config()
gemini = config.get("providers", {}).get("gemini", {})
api_key = gemini.get("api_key", "")
if not api_key:
    raise RuntimeError("No hay clave Gemini configurada")
files = sorted((path for path in root.iterdir() if path.suffix.lower() == ".pdf"), key=lambda path: path.name)[:10]
if len(files) != 10:
    raise RuntimeError(f"Se esperaban 10 PDFs y se encontraron {len(files)}")
agent_config = FormatAgentConfig(
    mode="gemini",
    model=gemini.get("model", "gemini-3.1-flash-lite"),
    requests_per_minute=4,
    max_words_per_request=2800,
)
exporter = DocumentExporter(out)
for index, source in enumerate(files, 1):
    document = Document(source.stem, source.name, FileType.PDF, source.stat().st_size, source.read_bytes())
    processed = FormatAgent(agent_config, api_key=api_key).process(document)
    generated = exporter.export_to_pdf(processed, out)
    target = out / f"{index:02d}_{source.stem.replace(' ', '_')}_gemini_preprocesado.pdf"
    generated.replace(target)
    print(f"OK {index:02d} {source.name} sections={len(processed.sections)} chars={len(processed.full_original_text)} refs={sum(1 for section in processed.sections if section.section_type.value == 'references')}", flush=True)
created = sorted(out.glob("*.pdf"))
if len(created) != 10:
    raise RuntimeError(f"Se generaron {len(created)} PDFs; se esperaban 10")
print(f"PDFS_GENERADOS={len(created)}", flush=True)
