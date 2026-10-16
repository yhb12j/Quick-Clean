"""
Генерация inline-клавиатур (callback-кнопок) для навигации по боту.

Payload-команды:
    {"cmd": "menu_services"} — раздел «Услуги»
    {"cmd": "menu_price"}    — раздел «Прайс-лист»
    {"cmd": "menu_manager"}  — раздел «Связаться с менеджером»
    {"cmd": "service", "id": "<id услуги>"} — карточка услуги
    {"cmd": "to_main"}       — возврат в главное меню
"""

from vkbottle import Callback, Keyboard, KeyboardButtonColor

from services import service_label


def main_menu_keyboard() -> Keyboard:
    """Главное меню: Услуги, Прайс-лист (в один ряд), менеджер (зелёная кнопка)."""
    kb = Keyboard(inline=True)
    kb.add(Callback("📋 Услуги", payload={"cmd": "menu_services"}))
    kb.add(Callback("💰 Прайс-лист", payload={"cmd": "menu_price"}))
    kb.row()
    kb.add(
        Callback("☎️ Связаться с менеджером", payload={"cmd": "menu_manager"}),
        color=KeyboardButtonColor.POSITIVE,  # зелёная кнопка
    )
    return kb


def services_keyboard(services: list[dict]) -> Keyboard:
    """Список услуг из JSON: 2 в столбец + кнопка «Главное меню» на всю ширину."""
    kb = Keyboard(inline=True)
    for index in range(0, len(services), 2):
        if index > 0:
            kb.row()
        for service in services[index:index + 2]:
            kb.add(
                Callback(
                    service_label(service),
                    payload={"cmd": "service", "id": service["id"]},
                )
            )
    kb.row()
    kb.add(Callback("🏠 Главное меню", payload={"cmd": "to_main"}))
    return kb


def service_card_keyboard() -> Keyboard:
    """Клавиатура под карточкой услуги: «Назад» (к списку) + «Главное меню»."""
    kb = Keyboard(inline=True)
    kb.add(Callback("⬅️ Назад", payload={"cmd": "menu_services"}))
    kb.add(Callback("🏠 Главное меню", payload={"cmd": "to_main"}))
    return kb


def price_keyboard() -> Keyboard:
    """Клавиатура под прайс-листом: единственная кнопка «Главное меню»."""
    kb = Keyboard(inline=True)
    kb.add(Callback("🏠 Главное меню", payload={"cmd": "to_main"}))
    return kb


def manager_keyboard() -> Keyboard:
    """Клавиатура под контактами менеджера: снова главное меню."""
    return main_menu_keyboard()
