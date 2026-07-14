"""Local retrieval over the bundled Brihat Parashara Hora Shastra PDFs.

The corpus stays on the user's machine.  Text is extracted only in memory, on
the first query, so there is no remote embedding service or data upload.
"""

from __future__ import annotations

from collections import Counter
from dataclasses import dataclass
from functools import lru_cache
import math
from pathlib import Path
import re
from typing import Iterable

REFERENCE_DIR = Path(__file__).resolve().parents[1] / "data" / "references"
MAX_QUERY_TERMS = 18
CHUNK_SIZE = 1_250
CHUNK_OVERLAP = 180


@dataclass(frozen=True)
class SourceChunk:
    source: str
    page: int
    text: str
    terms: Counter[str]


def retrieve_bphs_context(question: str, limit: int = 3) -> list[dict[str, object]]:
    """Return the best matching BPHS passages with human-readable citations."""
    query_terms = _expand_query(_tokens(question))
    if not query_terms:
        return []

    query_counts = Counter(query_terms[:MAX_QUERY_TERMS])
    corpus = _load_corpus()
    document_frequency = Counter(term for chunk in corpus for term in chunk.terms)
    scored: list[tuple[float, SourceChunk]] = []
    for chunk in corpus:
        overlap = sum(
            min(count, chunk.terms[term]) * (1 + math.log((len(corpus) + 1) / (document_frequency[term] + 1)))
            for term, count in query_counts.items()
        )
        if not overlap:
            continue
        phrase_bonus = sum(1 for term in query_counts if term in chunk.text.casefold())
        score = overlap * 3 + phrase_bonus + min(len(chunk.text), CHUNK_SIZE) / 10_000
        scored.append((score, chunk))

    scored.sort(key=lambda item: item[0], reverse=True)
    selected: list[dict[str, object]] = []
    seen: set[tuple[str, int]] = set()
    for _, chunk in scored:
        key = (chunk.source, chunk.page)
        if key in seen:
            continue
        seen.add(key)
        selected.append(
            {
                "source": chunk.source,
                "page": chunk.page,
                "citation": f"{chunk.source}, p. {chunk.page}",
                "excerpt": _clean_excerpt(chunk.text),
            }
        )
        if len(selected) >= limit:
            break
    return selected


def format_retrieval_context(matches: Iterable[dict[str, object]]) -> str:
    """Create a compact, citation-preserving context block for a local model."""
    sections = []
    for match in matches:
        sections.append(f"[{match['citation']}]\n{match['excerpt']}")
    return "\n\n".join(sections)


@lru_cache(maxsize=1)
def _load_corpus() -> tuple[SourceChunk, ...]:
    try:
        from pypdf import PdfReader
    except ImportError:
        return _load_corpus_from_raw_pdf_bytes()

    files = (
        ("Bhrigu Samhita Tmrao", REFERENCE_DIR / "bhrigu-samhita-tmrao.pdf"),
        ("BPHS (R. Santhanam, complete edition)", REFERENCE_DIR / "bphs-complete-r-santhanam.pdf"),
        ("BPHS Volume 2 (R. Santhanam)", REFERENCE_DIR / "bphs-volume-2-r-santhanam.pdf"),
    )
    chunks: list[SourceChunk] = []
    for title, path in files:
        if not path.exists():
            continue
        reader = PdfReader(path)
        for page_number, page in enumerate(reader.pages, start=1):
            text = _normalise(page.extract_text() or "")
            if _is_contents_page(text):
                continue
            for part in _chunk_text(text):
                terms = Counter(_tokens(part))
                if terms:
                    chunks.append(SourceChunk(title, page_number, part, terms))
    return tuple(chunks)


def _load_corpus_from_raw_pdf_bytes() -> tuple[SourceChunk, ...]:
    """Fallback when no PDF parser is installed.

    This does not perform full text extraction; it only indexes any readable
    Latin text embedded in the file bytes. It is intentionally conservative so
    we do not invent passages when no parser is available.
    """
    chunks: list[SourceChunk] = []
    for title, path in (
        ("Bhrigu Samhita Tmrao", REFERENCE_DIR / "bhrigu-samhita-tmrao.pdf"),
        ("BPHS (R. Santhanam, complete edition)", REFERENCE_DIR / "bphs-complete-r-santhanam.pdf"),
        ("BPHS Volume 2 (R. Santhanam)", REFERENCE_DIR / "bphs-volume-2-r-santhanam.pdf"),
    ):
        if not path.exists():
            continue
        raw = path.read_bytes()
        text = _normalise(_extract_ascii_text(raw))
        if not text:
            continue
        for part in _chunk_text(text):
            terms = Counter(_tokens(part))
            if terms:
                chunks.append(SourceChunk(title, 1, part, terms))
    return tuple(chunks)


def _chunk_text(text: str) -> Iterable[str]:
    if not text:
        return []
    if len(text) <= CHUNK_SIZE:
        return [text]
    return [text[start : start + CHUNK_SIZE] for start in range(0, len(text), CHUNK_SIZE - CHUNK_OVERLAP)]


def _normalise(text: str) -> str:
    return re.sub(r"\s+", " ", text).strip()


def _tokens(text: str) -> list[str]:
    return [term for term in re.findall(r"[a-zA-Z]{3,}", text.casefold()) if term not in _STOPWORDS]


def _clean_excerpt(text: str) -> str:
    return text[:700].rstrip(" ,;:") + ("..." if len(text) > 700 else "")


def _extract_ascii_text(blob: bytes, min_run: int = 4) -> str:
    runs: list[str] = []
    current: list[str] = []
    for byte in blob:
        char = chr(byte)
        if 32 <= byte <= 126:
            current.append(char)
        else:
            if len(current) >= min_run:
                runs.append("".join(current))
            current = []
    if len(current) >= min_run:
        runs.append("".join(current))
    return " ".join(runs)


def _expand_query(terms: list[str]) -> list[str]:
    expanded = list(terms)
    for term in terms:
        expanded.extend(_RELATED_TERMS.get(term, ()))
    return expanded


def _is_contents_page(text: str) -> bool:
    upper = text.upper()
    return "CONTENTS" in upper or (upper.count("EFFECTS OF THE") >= 5 and len(text) < 4_000)


_STOPWORDS = {
    "about", "according", "and", "are", "as", "ask", "but", "can", "chart", "for", "from",
    "how", "into", "its", "of", "or", "the", "this", "that", "their", "then", "what", "with",
    "will", "would", "your",
}

_RELATED_TERMS = {
    "marriage": ("seventh", "spouse", "wife", "husband", "married", "wedlock"),
    "spouse": ("marriage", "seventh", "wife", "husband"),
    "career": ("profession", "occupation", "tenth", "work", "karma"),
    "job": ("profession", "occupation", "tenth", "work"),
    "health": ("disease", "illness", "sixth", "body", "vitality"),
    "dasha": ("period", "vimshottari", "antardasha", "planet"),
    "dashas": ("period", "vimshottari", "antardasha", "planet"),
    "wealth": ("money", "income", "wealthy", "second", "eleventh"),
    "children": ("progeny", "child", "fifth", "son", "daughter"),
}
