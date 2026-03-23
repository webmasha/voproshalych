"""Скрипт для заполнения Базы Знаний из источников.

Запускается вручную. Инкрементально обрабатывает документы:
парсит 1 PDF → чанки → эмбеддинги батчами → сохраняет в БД.

Аргументы:
    --clear   Очистить таблицы перед заполнением (по умолчанию)
    --resume  Продолжить с последнего места (без очистки)
"""

import argparse
import asyncio
import json
import logging
import os
import re
import uuid
from dataclasses import dataclass, field
from urllib.parse import unquote

from sqlalchemy import create_engine, text

from qa.kb.chunking import Chunk, TextChunker
from qa.kb.config import get_kb_config
from qa.kb.embedding import get_embeddings_batch
from qa.kb.parsers import ConfluenceParser, SvedenParser, UtmnParser

logging.basicConfig(
    level=logging.INFO,
    format="%(asctime)s - %(name)s - %(levelname)s - %(message)s",
)
logger = logging.getLogger(__name__)

MAX_TITLE_LENGTH = 255
MAX_URL_LENGTH = 2048


def sanitize_title(title: str) -> str:
    title = unquote(title)
    title = re.sub(r"[\x00-\x1f\x7f]", "", title)
    if len(title) > MAX_TITLE_LENGTH:
        title = title[:MAX_TITLE_LENGTH]
    return title


def sanitize_url(url: str) -> str:
    if len(url) > MAX_URL_LENGTH:
        url = url[:MAX_URL_LENGTH]
    return url


@dataclass
class Config:
    confluence_pages: list[str] = field(
        default_factory=lambda: [
            "https://confluence.utmn.ru/pages/viewpage.action?pageId=8037875",
            "https://confluence.utmn.ru/pages/viewpage.action?pageId=121897057",
        ]
    )
    sveden_url: str = "https://sveden.utmn.ru/sveden/document/"

    utmn_pages: list[str] = field(
        default_factory=lambda: [
            "https://www.utmn.ru/obrazovanie/normativnye-dokumenty/normativnye-dokumenty-tyumgu/otkrytie-op-vo/",
            "https://www.utmn.ru/obrazovanie/normativnye-dokumenty/normativnye-dokumenty-tyumgu/op-vo/",
            "https://www.utmn.ru/obrazovanie/normativnye-dokumenty/normativnye-dokumenty-tyumgu/op-vo-iot/",
            "https://www.utmn.ru/obrazovanie/normativnye-dokumenty/normativnye-dokumenty-tyumgu/gia/",
            "https://www.utmn.ru/obrazovanie/normativnye-dokumenty/normativnye-dokumenty-tyumgu/kontingent/",
            "https://www.utmn.ru/obrazovanie/normativnye-dokumenty/normativnye-dokumenty-tyumgu/praktika/",
            "https://www.utmn.ru/obrazovanie/normativnye-dokumenty/normativnye-dokumenty-tyumgu/uregulirovanie-sporov/",
            "https://www.utmn.ru/obrazovanie/normativnye-dokumenty/normativnye-dokumenty-tyumgu/rezhim-zanyatiy/",
            "https://www.utmn.ru/obrazovanie/normativnye-dokumenty/normativnye-dokumenty-tyumgu/vyshestoyashchikh-organizatsiy/",
            "https://www.utmn.ru/o-tyumgu/organizatsionnaya-skhema-tyumgu/finance/ubnu/dokumenty/",
            "https://www.utmn.ru/o-tyumgu/organizatsionnaya-skhema-tyumgu/finance/economicplan/dokumenty/",
            "https://www.utmn.ru/obrazovanie/oplata-za-obuchenie/stoimost-obucheniya/",
            "https://www.utmn.ru/studentam/obshchezhitiya/studencheskie-obshchezhitiya/stoimost-i-oplata/",
            "https://www.utmn.ru/o-tyumgu/kontaktnaya-informatsiya/",
            "https://www.utmn.ru/aspirantam/aspirantura/dokumenty/",
            "https://www.utmn.ru/obrazovanie/inklyuzivnoe-obrazovanie/dokumenty/",
            "https://www.utmn.ru/o-tyumgu/organizatsionnaya-skhema-tyumgu/upravlenie-po-rabote-s-personalom/struktura/sluzhba-dokumentatsionnogo-obespecheniya/dokumenty-po-deloproizvodstvu/",
            "https://www.utmn.ru/o-tyumgu/organizatsionnaya-skhema-tyumgu/tsentr-informatsionnykh-tekhnologiy/dokumenty/",
            "https://www.utmn.ru/studentam/obshchezhitiya/studencheskie-obshchezhitiya/normativnye-dokumenty/",
            "https://www.utmn.ru/obrazovanie/oplata-za-obuchenie/obraztsy-dogovorov-ob-oplate/",
            "https://www.utmn.ru/o-tyumgu/organizatsionnaya-skhema-tyumgu/kontraktnaya-sluzhba/lokalnye-akty/",
            "https://www.utmn.ru/o-tyumgu/ofitsialnye-dokumenty/prikazy/",
            "https://www.utmn.ru/o-tyumgu/ofitsialnye-dokumenty/federalnye-dokumenty/",
        ]
    )


@dataclass
class Document:
    url: str
    title: str
    text_content: str
    source_type: str


@dataclass
class ChunkWithMeta:
    chunk: Chunk
    source_type: str
    document_title: str


def get_db_engine():
    import socket

    try:
        socket.gethostbyname("postgres")
        docker_host = "postgres"
    except socket.gaierror:
        docker_host = "localhost"

    env_host = os.getenv("POSTGRES_HOST", "")

    if env_host in ("", "localhost"):
        host = docker_host
    else:
        host = env_host

    db = os.getenv("POSTGRES_DB", "voproshalych")
    user = os.getenv("POSTGRES_USER", "voproshalych")
    password = os.getenv("POSTGRES_PASSWORD", "voproshalych")
    port = os.getenv("POSTGRES_PORT", "5432")

    db_url = f"postgresql://{user}:{password}@{host}:{port}/{db}"
    logger.info(f"Подключение к БД: {host}:{port}/{db}")
    return create_engine(db_url)


def load_existing_urls(engine) -> set[str]:
    with engine.connect() as conn:
        result = conn.execute(text("SELECT DISTINCT source_url FROM chunks"))
        urls = {row[0] for row in result}
    logger.info(f"В БД уже есть {len(urls)} URL документов")
    return urls


def clear_tables(engine) -> None:
    logger.info("Очистка таблиц chunks и embeddings...")

    with engine.connect() as conn:
        conn.execute(text("TRUNCATE TABLE embeddings CASCADE"))
        conn.execute(text("TRUNCATE TABLE chunks RESTART IDENTITY CASCADE"))
        conn.commit()

    logger.info("Таблицы очищены")


def save_chunks_batch(
    engine,
    chunks_with_meta: list[ChunkWithMeta],
    embeddings: list[list[float]],
) -> int:
    count = len(chunks_with_meta)
    logger.info(f"  → Сохранение {count} чанков в БД...")

    with engine.connect() as conn:
        for item, embedding in zip(chunks_with_meta, embeddings):
            try:
                chunk_id = uuid.uuid4()
                conn.execute(
                    text("""
                        INSERT INTO chunks (id, text, source_url, source_type, title)
                        VALUES (:id, :text, :source_url, :source_type, :title)
                    """),
                    {
                        "id": str(chunk_id),
                        "text": item.chunk.text,
                        "source_url": sanitize_url(item.chunk.source_url),
                        "source_type": item.source_type,
                        "title": sanitize_title(item.document_title),
                    },
                )
                conn.execute(
                    text("""
                        INSERT INTO embeddings (chunk_id, embedding)
                        VALUES (:chunk_id, :embedding)
                    """),
                    {
                        "chunk_id": str(chunk_id),
                        "embedding": json.dumps(embedding),
                    },
                )
            except Exception as e:
                logger.error(
                    f"  → Ошибка сохранения чанка '{item.document_title}': {e}"
                )
                conn.rollback()
                continue
        conn.commit()

    logger.info(f"  → Сохранено {count} чанков")
    return count


def chunk_document(
    doc: Document,
    chunker: TextChunker,
) -> list[ChunkWithMeta]:
    chunks = list(
        chunker.chunk_text(
            text=doc.text_content,
            source_url=doc.url,
            title=doc.title,
        )
    )
    return [
        ChunkWithMeta(chunk=c, source_type=doc.source_type, document_title=doc.title)
        for c in chunks
    ]


def process_document(
    engine,
    chunker: TextChunker,
    doc: Document,
    doc_idx: int,
) -> int:
    """Обработать один документ: чанки → эмбеддинги → сохранение в БД."""

    chunks = chunk_document(doc, chunker)

    if not chunks:
        logger.warning(f"[{doc_idx}] Документ '{doc.title}' без чанков")
        return 0

    EMBEDDING_BATCH = 5
    total_saved = 0

    for start in range(0, len(chunks), EMBEDDING_BATCH):
        batch = chunks[start : start + EMBEDDING_BATCH]
        texts = [item.chunk.text for item in batch]
        logger.info(f"  → Эмбеддинги для {len(batch)} чанков...")
        embeddings = get_embeddings_batch(texts)
        saved = save_chunks_batch(engine, batch, embeddings)
        total_saved += saved

    logger.info(f"[{doc_idx}] Сохранён: '{doc.title}' — {total_saved} чанков")
    return total_saved


async def run_source(
    engine,
    chunker: TextChunker,
    source_name: str,
    get_docs_func,
    existing_urls: set[str],
) -> tuple[int, int]:
    """Обработать все документы из источника инкрементально."""

    logger.info(f"\n{'=' * 50}")
    logger.info(f"Источник: {source_name}")
    logger.info(f"{'=' * 50}")

    total_docs = 0
    total_chunks = 0
    skipped = 0

    async for doc in get_docs_func():
        if doc.url in existing_urls:
            logger.info(f"[{total_docs + 1}] Пропуск (уже в БД): '{doc.title}'")
            skipped += 1
            total_docs += 1
            continue

        total_docs += 1
        logger.info(f"[{total_docs}] Парсинг: '{doc.title}' (тип: {doc.source_type})")

        saved = process_document(engine, chunker, doc, total_docs)
        total_chunks += saved

    logger.info(
        f"Источник {source_name}: {total_docs} документов ({skipped} пропущено), {total_chunks} чанков"
    )
    return total_docs, total_chunks


async def iterate_confluence(config: Config, existing_urls: set[str]):
    parser = ConfluenceParser()

    for page_url in config.confluence_pages:
        if page_url in existing_urls:
            logger.info(f"Пропуск страницы (уже в БД): {page_url}")
            continue

        page_id = parser._extract_page_id(page_url)
        if not page_id:
            logger.error(f"Не удалось извлечь page_id из URL: {page_url}")
            continue

        logger.info(f"Получение вложений со страницы {page_id}...")
        attachments = await parser._get_attachments(page_id)
        logger.info(f"Найдено {len(attachments)} вложений на странице {page_id}")

        allowed_count = sum(
            1 for a in attachments if parser._is_allowed_pdf(a.get("title", ""))
        )
        logger.info(f"Разрешённых PDF для парсинга: {allowed_count}")

        for idx, attachment in enumerate(attachments, 1):
            title = attachment.get("title", "")
            is_allowed = parser._is_allowed_pdf(title)
            media_type = attachment.get("metadata", {}).get(
                "mediaType", ""
            ) or attachment.get("extensions", {}).get("mediaType", "")
            is_pdf = "pdf" in str(media_type).lower() or title.lower().endswith(".pdf")
            logger.info(
                f"  [{idx}] '{title}' — allowed={is_allowed}, pdf={is_pdf}, type={media_type}"
            )

            if not is_allowed:
                continue

            download_url = attachment["_links"]["download"]
            if not download_url.startswith("http"):
                download_url = parser._host + download_url

            if not is_pdf:
                continue

            logger.info(f"[{idx}] Парсинг PDF: '{title}'")

            doc = await parser._parse_pdf(download_url, title, page_url)
            if doc:
                yield Document(
                    url=doc.url,
                    title=doc.title,
                    text_content=doc.text_content,
                    source_type="confluence",
                )
            else:
                logger.warning(f"[{idx}] Не удалось распарсить: '{title}'")


async def iterate_sveden(config: Config, existing_urls: set[str]):
    parser = SvedenParser()
    logger.info(f"Поиск PDF ссылок: {config.sveden_url}")
    pdf_urls = await parser._find_pdf_links(config.sveden_url)
    logger.info(f"Sveden: найдено {len(pdf_urls)} PDF ссылок")

    for idx, pdf_url in enumerate(pdf_urls, 1):
        if pdf_url in existing_urls:
            logger.info(f"[{idx}/{len(pdf_urls)}] Пропуск (уже в БД): {pdf_url}")
            continue

        logger.info(f"[{idx}/{len(pdf_urls)}] Парсинг PDF: {pdf_url}")

        doc = await parser._parse_pdf(pdf_url)
        if doc:
            yield Document(
                url=doc.url,
                title=doc.title,
                text_content=doc.text_content,
                source_type="sveden",
            )
        else:
            logger.warning(f"[{idx}] Не удалось распарсить: {pdf_url}")


async def iterate_utmn(config: Config, existing_urls: set[str]):
    parser = UtmnParser()
    total_pages = len(config.utmn_pages)
    logger.info(f"Парсинг {total_pages} страниц ТюмГУ...")

    for page_idx, page_url in enumerate(config.utmn_pages, 1):
        logger.info(f"  [{page_idx}/{total_pages}] Страница: {page_url}")
        pdf_urls = await parser._find_pdf_links(page_url)
        logger.info(f"    Найдено {len(pdf_urls)} PDF ссылок")

        for pdf_url in pdf_urls:
            if pdf_url in existing_urls:
                logger.info(f"    Пропуск (уже в БД): {pdf_url}")
                continue

            doc = await parser._parse_pdf(pdf_url)
            if doc:
                yield Document(
                    url=doc.url,
                    title=doc.title,
                    text_content=doc.text_content,
                    source_type="utmn",
                )


async def main(clear_tables_flag: bool) -> None:
    logger.info("Начало заполнения Базы Знаний...")

    engine = get_db_engine()
    kb_config = get_kb_config()

    chunker = TextChunker(
        chunk_size=kb_config.chunk_size,
        chunk_overlap=kb_config.chunk_overlap,
        min_chunk_size=kb_config.min_chunk_size,
    )

    if clear_tables_flag:
        clear_tables(engine)
        existing_urls: set[str] = set()
    else:
        existing_urls = load_existing_urls(engine)

    config = Config()

    total_docs = 0
    total_chunks = 0

    conf_docs, conf_chunks = await run_source(
        engine,
        chunker,
        "Confluence",
        lambda: iterate_confluence(config, existing_urls),
        existing_urls,
    )
    total_docs += conf_docs
    total_chunks += conf_chunks

    sved_docs, sved_chunks = await run_source(
        engine,
        chunker,
        "Sveden",
        lambda: iterate_sveden(config, existing_urls),
        existing_urls,
    )
    total_docs += sved_docs
    total_chunks += sved_chunks

    utmn_docs, utmn_chunks = await run_source(
        engine,
        chunker,
        "Utmn",
        lambda: iterate_utmn(config, existing_urls),
        existing_urls,
    )
    total_docs += utmn_docs
    total_chunks += utmn_chunks

    logger.info("")
    logger.info("=" * 50)
    logger.info(f"Заполнение завершено!")
    logger.info(f"Всего документов: {total_docs}")
    logger.info(f"Всего чанков сохранено: {total_chunks}")
    logger.info("=" * 50)


if __name__ == "__main__":
    parser = argparse.ArgumentParser(description="Заполнение Базы Знаний из источников")
    group = parser.add_mutually_exclusive_group()
    group.add_argument(
        "--clear",
        action="store_true",
        default=True,
        help="Очистить таблицы перед заполнением (по умолчанию)",
    )
    group.add_argument(
        "--resume",
        action="store_false",
        dest="clear",
        help="Продолжить с последнего места (без очистки)",
    )
    args = parser.parse_args()

    asyncio.run(main(args.clear))
