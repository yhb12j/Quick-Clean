"""
Точка входа бота сообщества ВКонтакте «Чисто и Быстро».
Запускает бота (Long Poll) и регистрирует обработчики
сообщений и callback-кнопок (message_event).

Библиотека: vkbottle 4.11+
"""

import json
import logging
import sys

from vkbottle import Bot
from vkbottle.modules import logger
from vkbottle.tools.mini_types.bot import MessageEventMin

from config import MANAGER_PHONE, TOKEN
from keyboards import (
    main_menu_keyboard,
    manager_keyboard,
    price_keyboard,
    service_card_keyboard,
    services_keyboard,
)
from services import get_service_by_id, load_services, service_label

# vkbottle пишет свои логи в stderr, из-за чего PowerShell
# показывает их как ошибки (NativeCommandError). Перенаправляем в stdout.
# Заодно ставим уровень INFO (по умолчанию WARNING — стартовые записи не пишутся).
logging.getLogger("vkbottle").setLevel(logging.INFO)
for _handler in logging.getLogger("vkbottle").handlers:
    if isinstance(_handler, logging.StreamHandler):
        _handler.stream = sys.stdout

# На Windows консоль по умолчанию в cp1251 — переключаем на UTF-8,
# чтобы эмодзи и кириллица в логах не вызывали UnicodeEncodeError
if sys.stdout.encoding and sys.stdout.encoding.lower() != "utf-8":
    sys.stdout.reconfigure(encoding="utf-8", errors="replace")
    sys.stderr.reconfigure(encoding="utf-8", errors="replace")

# Файловый логгер: пишем историю работы бота в bot.log (UTF-8),
# чтобы логи не зависели от настроек и редиректов консоли
_file_handler = logging.FileHandler("bot.log", encoding="utf-8")
_file_handler.setFormatter(
    logging.Formatter("%(asctime)s | %(levelname)-8s | %(name)s | %(message)s")
)
logging.getLogger("vkbottle").addHandler(_file_handler)

# Создаём экземпляр бота с токеном из .env
bot = Bot(TOKEN)

# Приветственный текст (главное меню)
WELCOME_TEXT = (
    "Добро пожаловать в клининг-центр **Чисто и Быстро**!\n"
    "Выберите интересующий раздел."
)

# Команды, при которых бот показывает главное меню
START_COMMANDS = {"начать", "привет", "start", "/start"}


# --- Вспомогательные функции ------------------------------------------------


def build_price_text(services: list[dict]) -> str:
    """Формирует текст прайс-листа циклом из каталога услуг."""
    lines = []
    for service in services:
        lines.append(f"{service_label(service)} — {service['price']}")
    return "**# Прайс-лист**\n\n" + "\n".join(lines)


def build_service_text(service: dict) -> str:
    """Формирует текст карточки услуги строго по формату ТЗ."""
    return (
        f"**{service['name']}**\n\n"
        f"{service['description']}\n\n"
        f"**Стоимость:** {service['price']}"
    )


def build_reply(payload: dict) -> tuple[str, str]:
    """Формирует текст сообщения и JSON клавиатуры для callback-команды.

    Чистая функция: работает только с payload и каталогом услуг,
    поэтому ошибки сети/API здесь невозможны.
    """
    command = payload.get("cmd")

    if command == "menu_services":
        # Раздел «Услуги»: список кнопок из JSON в 2 столбца
        return "Выбери услугу:", services_keyboard(load_services()).get_json()

    if command == "service":
        # Карточка конкретной услуги
        service = get_service_by_id(payload.get("id", ""))
        if service:
            text = build_service_text(service)
        else:
            text = "😔 К сожалению, эта услуга не найдена."
        return text, service_card_keyboard().get_json()

    if command == "menu_price":
        # Раздел «Прайс-лист»: список всех услуг и цен
        return build_price_text(load_services()), price_keyboard().get_json()

    if command == "menu_manager":
        # Раздел «Связаться с менеджером»
        text = (
            "Наш менеджер ответит вам в ближайшее время.\n\n"
            "**Телефон:**\n"
            f"{MANAGER_PHONE}\n\n"
            "Или напишите в сообщения сообщества."
        )
        return text, manager_keyboard().get_json()

    # Главное меню (команда "to_main" и любые неизвестные payload)
    return WELCOME_TEXT, main_menu_keyboard().get_json()


# --- Обработчики сообщений --------------------------------------------------


@bot.on.message(text=["Начать", "Привет", "start", "/start"])
async def cmd_start(message):
    """Стартовые команды — приветствие и главное меню."""
    await message.answer(WELCOME_TEXT, keyboard=main_menu_keyboard().get_json())


@bot.on.message()
async def fallback(message):
    """Любое другое сообщение: команды в другом регистре — главное меню,
    иначе — подсказка воспользоваться кнопками."""
    if message.text and message.text.strip().lower() in START_COMMANDS:
        await message.answer(WELCOME_TEXT, keyboard=main_menu_keyboard().get_json())
        return
    await message.answer(
        "Пожалуйста, воспользуйтесь кнопками меню 👇",
        keyboard=main_menu_keyboard().get_json(),
    )


# --- Обработчик callback-кнопок ---------------------------------------------


@bot.on.raw_event("message_event", dataclass=MessageEventMin)
async def on_button_press(event: MessageEventMin):
    """Обработчик нажатий на inline-кнопки (callback).

    Вместо редактирования старого сообщения на месте бот:
    1) подтверждает нажатие (гасит анимацию загрузки кнопки);
    2) снимает inline-клавиатуру со старого сообщения;
    3) отправляет новое меню/карточку ОТДЕЛЬНЫМ новым сообщением,
       чтобы история переписки уходила вверх.

    Обязательный try-except гасит анимацию загрузки даже при ошибке:
    иначе VK держит индикатор ~15 секунд и показывает «кнопка зависла».
    """

    # 1) Сразу подтверждаем нажатие через sendMessageEventAnswer —
    #    кнопка перестаёт «крутиться», пользователь видит ответ мгновенно
    try:
        await event.send_empty_answer()
    except Exception:
        logger.warning("Не удалось подтвердить нажатие callback-кнопки")

    try:
        payload = event.payload if isinstance(event.payload, dict) else json.loads(event.payload or "{}")
        text, keyboard = build_reply(payload)

        # 2) Убираем активные inline-кнопки со старого сообщения,
        #    чтобы по ним нельзя было кликнуть повторно.
        #    keyboard="" — именно так VK интерпретирует удаление клавиатуры;
        #    текст старого сообщения оставляем как есть (message не передаём).
        try:
            await bot.api.messages.edit(
                peer_id=event.peer_id,
                conversation_message_id=event.conversation_message_id,
                keyboard="",
            )
        except Exception:
            logger.warning("Не удалось убрать клавиатуру со старого сообщения")

        # 3) Отправляем ответ отдельным НОВЫМ сообщением — история уходит вверх
        await bot.api.messages.send(
            peer_id=event.peer_id,
            message=text,
            keyboard=keyboard,
            random_id=0,
        )
    except Exception:
        logger.exception("Ошибка при обработке callback-кнопки")
        # Гасим анимацию загрузки даже при ошибке — сообщение об ошибке
        try:
            await bot.api.messages.send(
                peer_id=event.peer_id,
                message="😔 Произошла ошибка. Попробуйте ещё раз.",
                random_id=0,
            )
        except Exception:
            logger.exception("Не удалось отправить сообщение об ошибке")


# Запуск бота (Long Poll). Точка входа приложения.
if __name__ == "__main__":
    bot.run()
