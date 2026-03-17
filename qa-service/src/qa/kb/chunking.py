"""Text chunking for Knowledge Base."""

import logging
import re
from dataclasses import dataclass
from typing import Generator

logger = logging.getLogger(__name__)


@dataclass
class Chunk:
    """A text chunk from a document."""

    text: str
    source_url: str
    title: str
    chunk_index: int


class TextChunker:
    """Split text into overlapping chunks."""

    def __init__(
        self,
        chunk_size: int = 1000,
        chunk_overlap: int = 200,
        min_chunk_size: int = 100,
    ):
        """Initialize the chunker.

        Args:
            chunk_size: Maximum size of each chunk in characters
            chunk_overlap: Overlap between chunks in characters
            min_chunk_size: Minimum chunk size to keep
        """
        self.chunk_size = chunk_size
        self.chunk_overlap = chunk_overlap
        self.min_chunk_size = min_chunk_size

    def chunk_text(
        self,
        text: str,
        source_url: str,
        title: str = "",
    ) -> Generator[Chunk, None, None]:
        """Split text into overlapping chunks.

        Args:
            text: Text to split
            source_url: URL of the source document
            title: Title of the document

        Yields:
            Chunk objects
        """
        text = text.strip()
        if not text:
            logger.warning(f"Empty text for {source_url}")
            return

        paragraphs = self._split_into_paragraphs(text)
        chunks: list[str] = []
        current_chunk = ""

        for paragraph in paragraphs:
            paragraph = paragraph.strip()
            if not paragraph:
                continue

            if len(current_chunk) + len(paragraph) + 1 <= self.chunk_size:
                if current_chunk:
                    current_chunk += "\n\n" + paragraph
                else:
                    current_chunk = paragraph
            else:
                if current_chunk:
                    chunks.append(current_chunk)
                    overlap_start = max(0, len(current_chunk) - self.chunk_overlap)
                    current_chunk = current_chunk[overlap_start:] + "\n\n" + paragraph
                else:
                    chunks.append(paragraph)
                    current_chunk = ""

        if current_chunk:
            chunks.append(current_chunk)

        for i, chunk_text in enumerate(chunks):
            if len(chunk_text) >= self.min_chunk_size:
                yield Chunk(
                    text=chunk_text,
                    source_url=source_url,
                    title=title or source_url,
                    chunk_index=i,
                )

        logger.info(f"Created {len(chunks)} chunks from {source_url}")

    def _split_into_paragraphs(self, text: str) -> list[str]:
        """Split text into paragraphs.

        Args:
            text: Text to split

        Returns:
            List of paragraphs
        """
        text = re.sub(r"\n{3,}", "\n\n", text)
        paragraphs = text.split("\n\n")
        return [p.strip() for p in paragraphs if p.strip()]
