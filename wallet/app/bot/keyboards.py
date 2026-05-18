"""Reusable keyboards / button layouts for the bot."""
from __future__ import annotations

from aiogram.types import (
    InlineKeyboardButton,
    InlineKeyboardMarkup,
    KeyboardButton,
    ReplyKeyboardMarkup,
)

from ..db.models import Asset
from ..services.registry import SUPPORTED_ASSETS, list_networks_for_asset


def main_menu() -> ReplyKeyboardMarkup:
    return ReplyKeyboardMarkup(
        keyboard=[
            [KeyboardButton(text="💰 Баланс"), KeyboardButton(text="📥 Пополнить")],
            [KeyboardButton(text="📤 Вывести"), KeyboardButton(text="🔁 Перевод")],
            [KeyboardButton(text="📜 История"), KeyboardButton(text="🧾 Выписка")],
            [KeyboardButton(text="⚙️ Настройки")],
        ],
        resize_keyboard=True,
    )


def assets_kb(prefix: str) -> InlineKeyboardMarkup:
    rows = []
    row: list[InlineKeyboardButton] = []
    for a in SUPPORTED_ASSETS:
        row.append(InlineKeyboardButton(text=a.value, callback_data=f"{prefix}:asset:{a.value}"))
        if len(row) == 2:
            rows.append(row)
            row = []
    if row:
        rows.append(row)
    rows.append([InlineKeyboardButton(text="« Назад", callback_data=f"{prefix}:cancel")])
    return InlineKeyboardMarkup(inline_keyboard=rows)


def networks_for_asset_kb(prefix: str, asset: Asset) -> InlineKeyboardMarkup:
    rows = []
    for n in list_networks_for_asset(asset):
        rows.append(
            [
                InlineKeyboardButton(
                    text=n.label,
                    callback_data=f"{prefix}:net:{n.chain.value}:{n.asset.value}",
                )
            ]
        )
    rows.append([InlineKeyboardButton(text="« Назад", callback_data=f"{prefix}:back_asset")])
    return InlineKeyboardMarkup(inline_keyboard=rows)


def confirm_kb(prefix: str) -> InlineKeyboardMarkup:
    return InlineKeyboardMarkup(
        inline_keyboard=[
            [
                InlineKeyboardButton(text="✅ Подтвердить", callback_data=f"{prefix}:confirm"),
                InlineKeyboardButton(text="✖ Отмена", callback_data=f"{prefix}:cancel"),
            ]
        ]
    )


def history_filters_kb() -> InlineKeyboardMarkup:
    rows = [
        [
            InlineKeyboardButton(text="Все типы", callback_data="hist:type:any"),
            InlineKeyboardButton(text="Депозиты", callback_data="hist:type:DEPOSIT"),
            InlineKeyboardButton(text="Выводы", callback_data="hist:type:WITHDRAW"),
        ],
        [
            InlineKeyboardButton(text="Все активы", callback_data="hist:asset:any"),
            InlineKeyboardButton(text="BTC", callback_data="hist:asset:BTC"),
            InlineKeyboardButton(text="USDT", callback_data="hist:asset:USDT"),
        ],
        [
            InlineKeyboardButton(text="USDC", callback_data="hist:asset:USDC"),
            InlineKeyboardButton(text="TON", callback_data="hist:asset:TON"),
        ],
        [
            InlineKeyboardButton(text="7 дней", callback_data="hist:period:7"),
            InlineKeyboardButton(text="30 дней", callback_data="hist:period:30"),
            InlineKeyboardButton(text="90 дней", callback_data="hist:period:90"),
            InlineKeyboardButton(text="Все", callback_data="hist:period:all"),
        ],
    ]
    return InlineKeyboardMarkup(inline_keyboard=rows)


def statement_kb() -> InlineKeyboardMarkup:
    return InlineKeyboardMarkup(
        inline_keyboard=[
            [
                InlineKeyboardButton(text="PDF 30д", callback_data="stmt:pdf:30"),
                InlineKeyboardButton(text="PDF 90д", callback_data="stmt:pdf:90"),
                InlineKeyboardButton(text="PDF за всё", callback_data="stmt:pdf:all"),
            ],
            [
                InlineKeyboardButton(text="CSV 30д", callback_data="stmt:csv:30"),
                InlineKeyboardButton(text="CSV 90д", callback_data="stmt:csv:90"),
                InlineKeyboardButton(text="CSV за всё", callback_data="stmt:csv:all"),
            ],
        ]
    )


def settings_kb(totp_enabled: bool) -> InlineKeyboardMarkup:
    rows = [
        [
            InlineKeyboardButton(
                text=("🔐 Отключить 2FA" if totp_enabled else "🔐 Включить 2FA"),
                callback_data="set:totp",
            )
        ],
        [InlineKeyboardButton(text="🆔 Мой ID", callback_data="set:id")],
        [InlineKeyboardButton(text="« Назад", callback_data="set:cancel")],
    ]
    return InlineKeyboardMarkup(inline_keyboard=rows)
