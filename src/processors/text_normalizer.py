"""Normalización de texto extraído de documentos académicos."""
import re


_SECTION_LINE = re.compile(
    r"^(?:\d+(?:\.\d+)*\s*\.?\s*)?"
    r"(?:abstract|summary|introduction|background|methods?|methodology|"
    r"results?|discussion|conclusions?|references|bibliography|appendix|"
    r"acknowledg(?:e)?ments?)$",
    re.IGNORECASE,
)
_STRUCTURAL_LINE = re.compile(
    r"^(?:#{1,6}\s|\[(?:table|figure|tabla|figura)(?:\s+\d+)?\]|"
    r"(?:table|figure|tabla|figura)\s+\d+\b|\\(?:begin|end|section|subsection))",
    re.IGNORECASE,
)


def _is_structural_line(line: str) -> bool:
    stripped = line.strip()
    if not stripped:
        return True
    if _SECTION_LINE.match(stripped) or _STRUCTURAL_LINE.match(stripped):
        return True
    return len(stripped) <= 90 and stripped.endswith((':',))


def _normalize_paragraph(lines: list[str]) -> str:
    text = "\n".join(line.strip() for line in lines if line.strip())
    if not text:
        return ""

    legitimate_prefixes = {
        "cross", "state", "well", "self", "real", "time", "cost",
        "evidence", "decision",
    }

    def join_hyphenated(match: re.Match) -> str:
        prefix = match.group("prefix")
        hyphen = match.group("hyphen")
        return prefix + ("-" if prefix.lower() in legitimate_prefixes else "") + match.group("suffix")

    text = re.sub(
        r"(?P<prefix>[\wáéíóúüñ]+)(?P<hyphen>-|\u2010|\u2011|\u00ad)"
        r"\s*\n\s*(?P<suffix>[a-záéíóúüñ])",
        join_hyphenated,
        text,
        flags=re.IGNORECASE,
    )
    output: list[str] = []
    current = ""
    for line in text.splitlines():
        line = re.sub(r"\s+", " ", line).strip()
        if not line:
            continue
        if not current:
            current = line
        elif _is_structural_line(line) or _is_structural_line(current):
            output.append(current)
            current = line
        else:
            current = f"{current} {line}"
    if current:
        output.append(current)

    return "\n".join(output)


def normalize_extracted_text(text: str) -> str:
    """Recompone párrafos y palabras partidas sin alterar guiones legítimos."""
    if not text:
        return ""

    text = text.replace("\r\n", "\n").replace("\r", "\n")
    text = text.replace("\u00a0", " ").replace("\u200b", "")
    text = re.sub(r"\(cid:\d+\)", "", text)
    text = re.sub(r"[ \t]+\n", "\n", text)
    text = re.sub(r"\n[ \t]+", "\n", text)

    paragraphs = re.split(r"\n\s*\n+", text)
    normalized = [_normalize_paragraph(paragraph.split("\n")) for paragraph in paragraphs]
    normalized = [paragraph for paragraph in normalized if paragraph]
    return "\n\n".join(normalized).strip()