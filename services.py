"""
Работа с каталогом клининговых услуг:
чтение services.json, поиск по id, иконки и подписи услуг.
"""

import json
from pathlib import Path

# Путь к файлу с каталогом услуг (лежит рядом с bot.py)
SERVICES_PATH = Path(__file__).parent / "services.json"

# Эмодзи-иконки для каждой услуги (используются в кнопках и прайс-листе)
SERVICE_ICONS: dict[str, str] = {
    "dry_carpet": "🧺",
    "dry_sofa": "🛋️",
    "window_wash": "🪟",
    "general_flat": "✨",
    "ironing_basket": "👔",
    "kitchen_deep": "🍳",
}

# Иконка по умолчанию, если у услуги нет своего эмодзи
DEFAULT_ICON = "🔹"


def load_services() -> list[dict]:
    """Загружает и возвращает список всех услуг из services.json.

    Поддерживаются оба формата файла: плоский список объектов
    и объект вида {"services": [...]}.
    """
    with SERVICES_PATH.open("r", encoding="utf-8") as file:
        data = json.load(file)
    if isinstance(data, dict):
        return data.get("services", [])
    return data


def get_service_by_id(service_id: str) -> dict | None:
    """Возвращает услугу по её идентификатору или None, если она не найдена."""
    for service in load_services():
        if service.get("id") == service_id:
            return service
    return None


def get_service_icon(service: dict) -> str:
    """Возвращает эмодзи-иконку услуги."""
    return SERVICE_ICONS.get(service.get("id", ""), DEFAULT_ICON)


def service_label(service: dict) -> str:
    """Подпись услуги для кнопки/прайса: '🧺 Химчистка ковра'."""
    return f"{get_service_icon(service)} {service['name']}"
