#!/usr/bin/env python3
"""Скрипт для загрузки документов в Базу Знаний.

Запускать после запуска Docker:
    docker compose up -d

Запуск:
    python scripts/fill_kb.py
"""

import asyncio
import logging
import sys

import httpx

logging.basicConfig(
    level=logging.INFO,
    format="%(asctime)s - %(levelname)s - %(message)s",
)
logger = logging.getLogger(__name__)

DOCUMENTS = [
    # Официальные документы utmn.ru
    "https://www.utmn.ru/o-tyumgu/ofitsialnye-dokumenty/ustav-i-litsenzii/",
    "https://www.utmn.ru/o-tyumgu/ofitsialnye-dokumenty/litsenziya/",
    "https://www.utmn.ru/o-tyumgu/ofitsialnye-dokumenty/svidetelstvo-o-gosudarstvennoy-akkreditatsii/",
    "https://www.utmn.ru/o-tyumgu/ofitsialnye-dokumenty/vypiska-iz-egryul/",
    "https://www.utmn.ru/o-tyumgu/ofitsialnye-dokumenty/pravila-vnutrennego-rasporyadka/",
    "https://www.utmn.ru/o-tyumgu/ofitsialnye-dokumenty/kollektivnyy-dogovor/",
    "https://www.utmn.ru/o-tyumgu/ofitsialnye-dokumenty/oplata-truda/",
    "https://www.utmn.ru/o-tyumgu/organizatsionnaya-skhema-tyumgu/upravlenie-po-rabote-s-personalom/struktura/sluzhba-dokumentatsionnogo-obespecheniya/obrashcheniya-grazhdan/",
    "https://www.utmn.ru/o-tyumgu/ofitsialnye-dokumenty/normativnye-dokumenty-tyumgu-polozheniya-o-strukturnykh-podrazdeleniyakh/",
    "https://www.utmn.ru/o-tyumgu/ofitsialnye-dokumenty/o-personalnykh-dannykh/",
    # Образовательная деятельность
    "https://www.utmn.ru/obrazovanie/normativnye-dokumenty/normativnye-dokumenty-tyumgu/otkrytie-op-vo/",
    "https://www.utmn.ru/obrazovanie/normativnye-dokumenty/normativnye-dokumenty-tyumgu/op-vo/",
    "https://www.utmn.ru/obrazovanie/normativnye-dokumenty/normativnye-dokumenty-tyumgu/op-vo-iot/",
    "https://www.utmn.ru/obrazovanie/normativnye-dokumenty/normativnye-dokumenty-tyumgu/gia/",
    "https://www.utmn.ru/obrazovanie/normativnye-dokumenty/normativnye-dokumenty-tyumgu/kontingent/",
    "https://www.utmn.ru/obrazovanie/normativnye-dokumenty/normativnye-dokumenty-tyumgu/tekushchiy-kontrol-i-promezhutochnaya-attestatsiya/",
    "https://www.utmn.ru/obrazovanie/normativnye-dokumenty/normativnye-dokumenty-tyumgu/praktika/",
    "https://www.utmn.ru/obrazovanie/normativnye-dokumenty/normativnye-dokumenty-tyumgu/uregulirovanie-sporov/",
    "https://www.utmn.ru/obrazovanie/normativnye-dokumenty/normativnye-dokumenty-tyumgu/rezhim-zanyatiy/",
    # Финансы
    "https://www.utmn.ru/o-tyumgu/organizatsionnaya-skhema-tyumgu/finance/ubnu/dokumenty/",
    "https://www.utmn.ru/o-tyumgu/organizatsionnaya-skhema-tyumgu/finance/economicplan/dokumenty/",
    "https://www.utmn.ru/obrazovanie/oplata-za-obuchenie/stoimost-obucheniya/",
    "https://www.utmn.ru/studentam/obshchezhitiya/studencheskie-obshchezhitiya/stoimost-i-oplata/#prikazy",
    "https://www.utmn.ru/o-tyumgu/kontaktnaya-informatsiya/",
    # Прочее
    "https://www.utmn.ru/aspirantam/aspirantura/dokumenty/",
    "https://www.utmn.ru/obrazovanie/inklyuzivnoe-obrazovanie/dokumenty/",
    "https://www.utmn.ru/o-tyumgu/organizatsionnaya-skhema-tyumgu/upravlenie-po-rabote-s-personalom/struktura/sluzhba-dokumentatsionnogo-obespecheniya/dokumenty-po-deloproizvodstvu/",
    "https://www.utmn.ru/o-tyumgu/organizatsionnaya-skhema-tyumgu/tsentr-informatsionnykh-tekhnologiy/dokumenty/",
    "https://www.utmn.ru/studentam/obshchezhitiya/studencheskie-obshchezhitiya/normativnye-dokumenty/",
    "https://www.utmn.ru/obrazovanie/oplata-za-obuchenie/obraztsy-dogovorov-ob-oplate/",
    "https://www.utmn.ru/o-tyumgu/organizatsionnaya-skhema-tyumgu/kontraktnaya-sluzhba/lokalnye-akty/",
    "https://www.utmn.ru/o-tyumgu/ofitsialnye-dokumenty/prikazy/",
    "https://www.utmn.ru/o-tyumgu/ofitsialnye-dokumenty/federalnye-dokumenty/",
    # PDF с Confluence
    "https://confluence.utmn.ru/pages/viewpage.action?pageId=8037875&preview=/8037875/8037877/terms.4be25f01.pdf",
    "https://confluence.utmn.ru/pages/viewpage.action?pageId=8037875&preview=/8037875/8037878/%D0%9F%D0%BE%D0%BB%D0%B8%D1%82%D0%B8%D0%BA%D0%B0%20%D0%BE%D0%B1%D0%B5%D1%81%D0%BF%D0%B5%D1%87%D0%B5%D0%BD%D0%B8%D1%8F%20%D0%B8%D0%BD%D1%84%D0%BE%D1%80%D0%BC%D0%B0%D1%86%D0%B8%D0%BE%D0%BD%D0%BD%D0%BE%D0%B9%20%D0%B1%D0%B5%D0%B7%D0%BE%D0%BF%D0%B0%D1%81%D0%BD%D0%BE%D1%81%D1%82%D0%B8%20%D0%A2%D1%8E%D0%BC%D0%93%D0%A3.pdf",
    "https://confluence.utmn.ru/pages/viewpage.action?pageId=8037875&preview=/8037875/15565326/247_1.pdf",
    "https://confluence.utmn.ru/pages/viewpage.action?pageId=8037875&preview=/8037875/8037880/%D0%9F%D0%BE%D0%BB%D0%BE%D0%B6%D0%B5%D0%BD%D0%B8%D0%B5%20%D0%BE%20%D0%B1%D0%B5%D0%B7%D0%BE%D0%BF%D0%B0%D1%81%D0%BD%D0%BE%D1%81%D1%82%D0%B8%20%D0%B0%D0%B2%D1%82%D0%BE%D0%BC%D0%B0%D1%82%D0%B8%D0%B7%D0%B8%D1%80%D0%BE%D0%B2%D0%B0%D0%BD%D0%BD%D0%BE%D0%B3%D0%BE%20%D1%80%D0%B0%D0%B1%D0%BE%D1%87%D0%B5%D0%B3%D0%BE%20%D0%BC%D0%B5%D1%81%D1%82%D0%B0.pdf",
    "https://confluence.utmn.ru/pages/viewpage.action?pageId=8037875&preview=/8037875/8037881/%D0%9F%D0%BE%D0%BB%D0%BE%D0%B6%D0%B5%D0%BD%D0%B8%D0%B5%20%D0%BE%20%D0%BF%D0%BE%D1%80%D1%8F%D0%B4%D0%BA%D0%B5%20%D0%BF%D1%80%D0%B5%D0%B4%D0%BE%D1%81%D1%82%D0%B0%D0%B2%D0%BB%D0%B5%D0%BD%D0%B8%D1%8F%20%D1%83%D0%B4%D0%B0%D0%BB%D0%B5%D0%BD%D0%BD%D0%BE%D0%B3%D0%BE%20%D0%B4%D0%BE%D1%81%D1%82%D1%80%D1%83%D0%BF%D0%B0.PDF",
    "https://confluence.utmn.ru/pages/viewpage.action?pageId=8037875&preview=/121897057/121897066/514-1.pdf",
    "https://confluence.utmn.ru/pages/viewpage.action?pageId=8037875&preview=/8037875/150223784/540-1.pdf",
]

QA_SERVICE_URL = "http://localhost:8004"


async def upload_document(url: str, client: httpx.AsyncClient) -> dict | None:
    """Загрузить документ в БЗ."""
    try:
        response = await client.post(
            f"{QA_SERVICE_URL}/kb/documents",
            json={"url": url},
            timeout=120.0,
        )
        response.raise_for_status()
        return response.json()
    except Exception as e:
        logger.error(f"Failed to upload {url}: {e}")
        return None


async def main():
    """Загрузить все документы в Базу Знаний."""
    logger.info(f"Загрузка {len(DOCUMENTS)} документов в Базу Знаний...")

    async with httpx.AsyncClient() as client:
        # Проверить доступность сервиса
        try:
            response = await client.get(f"{QA_SERVICE_URL}/health")
            response.raise_for_status()
            logger.info("QA Service доступен")
        except Exception as e:
            logger.error(f"QA Service недоступен: {e}")
            sys.exit(1)

        success_count = 0
        fail_count = 0

        for i, url in enumerate(DOCUMENTS, 1):
            logger.info(f"[{i}/{len(DOCUMENTS)}] Загрузка: {url}")
            result = await upload_document(url, client)
            if result:
                success_count += 1
                logger.info(f"  ✓ Загружено: {result.get('chunks_count', '?')} чанков")
            else:
                fail_count += 1

    logger.info(f"Готово! Успешно: {success_count}, Ошибки: {fail_count}")


if __name__ == "__main__":
    asyncio.run(main())
