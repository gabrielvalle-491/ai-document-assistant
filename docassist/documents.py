"""Load documents and split them into searchable chunks that remember where they came from."""

from __future__ import annotations

import io
import re
from dataclasses import dataclass
from pathlib import Path

from pypdf import PdfReader

SUPPORTED = (".pdf", ".txt", ".md")
TERMINAL = (".", "!", "?", ":")


@dataclass
class Chunk:
    text: str
    source: str
    page: int | None
    chunk_id: int

    @property
    def citation(self) -> str:
        return f"{self.source}, p. {self.page}" if self.page else self.source


def read_pages(name: str, data: bytes) -> list[tuple[int | None, str]]:
    """Return (page_number, text) pairs. Plain-text files are a single page without number."""
    suffix = Path(name).suffix.lower()
    if suffix == ".pdf":
        reader = PdfReader(io.BytesIO(data))
        return [(i + 1, page.extract_text() or "") for i, page in enumerate(reader.pages)]
    if suffix in (".txt", ".md"):
        return [(None, data.decode("utf-8", errors="replace"))]
    raise ValueError(f"Unsupported file type: {suffix} (supported: {', '.join(SUPPORTED)})")


def text_units(text: str) -> list[str]:
    """Turn raw page text into clean units: headings and complete sentences.

    PDF extraction breaks sentences at every visual line wrap. Wrapped lines are joined back
    into paragraphs; short lines without final punctuation are kept as headings.
    """
    units: list[str] = []
    paragraph: list[str] = []
    lines = [re.sub(r"[ \t]+", " ", raw).strip() for raw in text.splitlines()]
    lines = [line for line in lines if line]
    for i, line in enumerate(lines):
        following = lines[i + 1] if i + 1 < len(lines) else ""
        continues = bool(following) and following[0].islower()  # wrapped sentence goes on
        if not paragraph and len(line) <= 60 and not line.endswith(TERMINAL + (",", ";")) and not continues:
            units.append(line)  # heading
            continue
        paragraph.append(line)
        if line.endswith(TERMINAL):
            units += [s.strip() for s in re.split(r"(?<=[.!?])\s+", " ".join(paragraph)) if s.strip()]
            paragraph = []
    if paragraph:
        units.append(" ".join(paragraph))
    return units


def split_text(text: str, max_chars: int = 600, overlap_units: int = 1) -> list[str]:
    """Group units into chunks under `max_chars`; the last unit is repeated as overlap.

    Units are joined with newlines so headings and sentences stay separable later.
    """
    chunks: list[str] = []
    current: list[str] = []
    for unit in text_units(text):
        if current and len("\n".join(current)) + len(unit) + 1 > max_chars:
            chunks.append("\n".join(current))
            current = current[-overlap_units:] if overlap_units else []
        current.append(unit)
    if current:
        chunks.append("\n".join(current))
    return chunks


def load_documents(files: list[tuple[str, bytes]], max_chars: int = 600) -> list[Chunk]:
    """`files` is a list of (file_name, raw_bytes) — works for uploads and for files on disk."""
    chunks: list[Chunk] = []
    for name, data in files:
        for page, text in read_pages(name, data):
            for piece in split_text(text, max_chars=max_chars):
                chunks.append(Chunk(text=piece, source=name, page=page, chunk_id=len(chunks)))
    return chunks


def load_folder(folder: str | Path) -> list[Chunk]:
    paths = sorted(p for p in Path(folder).iterdir() if p.suffix.lower() in SUPPORTED)
    return load_documents([(p.name, p.read_bytes()) for p in paths])
