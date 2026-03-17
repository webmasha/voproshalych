"""Web page and PDF parser."""

import logging
from dataclasses import dataclass

import httpx
from bs4 import BeautifulSoup
from pypdf import PdfReader

logger = logging.getLogger(__name__)


@dataclass
class ParsedDocument:
    """Parsed document data."""

    url: str
    title: str
    text_content: str


class WebPageParser:
    """Parser for extracting content from web pages and PDFs."""

    async def parse(self, url: str) -> ParsedDocument:
        """Parse a web page or PDF and extract content.

        Args:
            url: URL of the page or PDF to parse

        Returns:
            ParsedDocument with extracted content

        Raises:
            httpx.HTTPStatusError: If the request fails
        """
        if url.lower().endswith(".pdf"):
            return await self._parse_pdf(url)
        return await self._parse_html(url)

    async def _parse_html(self, url: str) -> ParsedDocument:
        """Parse an HTML page."""
        headers = {
            "User-Agent": "Mozilla/5.0 (compatible; VoproshalychBot/1.0; +https://voproshalych.ru)",
        }

        async with httpx.AsyncClient(timeout=30.0, follow_redirects=True) as client:
            response = await client.get(url, headers=headers)
            response.raise_for_status()

        soup = BeautifulSoup(response.text, "html.parser")

        for script in soup(["script", "style"]):
            script.decompose()

        title = ""
        title_tag = soup.find("title")
        if title_tag:
            title = title_tag.get_text(strip=True)

        content = soup.get_text(separator="\n", strip=True)

        lines = (line.strip() for line in content.splitlines())
        chunks = (phrase.strip() for line in lines for phrase in line.split("  "))
        text_content = "\n".join(chunk for chunk in chunks if chunk)

        logger.info(f"Parsed HTML from {url}: title='{title[:50]}...'")

        return ParsedDocument(
            url=url,
            title=title,
            text_content=text_content,
        )

    async def _parse_pdf(self, url: str) -> ParsedDocument:
        """Parse a PDF file."""
        headers = {
            "User-Agent": "Mozilla/5.0 (compatible; VoproshalychBot/1.0; +https://voproshalych.ru)",
        }

        async with httpx.AsyncClient(timeout=60.0, follow_redirects=True) as client:
            response = await client.get(url, headers=headers)
            response.raise_for_status()

        from io import BytesIO

        pdf_file = BytesIO(response.content)
        reader = PdfReader(pdf_file)

        title = ""
        if reader.metadata and reader.metadata.get("/Title"):
            title = reader.metadata.get("/Title")

        text_content = ""
        for page_num, page in enumerate(reader.pages):
            page_text = page.extract_text()
            if page_text:
                text_content += page_text + "\n\n"

        text_content = text_content.strip()

        logger.info(
            f"Parsed PDF from {url}: title='{title}', pages={len(reader.pages)}"
        )

        return ParsedDocument(
            url=url,
            title=title or url.split("/")[-1],
            text_content=text_content,
        )
