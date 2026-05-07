"""Entry point for the Telegram visual novel bot."""
from __future__ import annotations

import asyncio
import logging
import os
from pathlib import Path

from aiogram import Bot, Dispatcher, F, Router
from aiogram.client.default import DefaultBotProperties
from aiogram.enums import ParseMode
from aiogram.filters import Command, CommandStart
from aiogram.types import (
    CallbackQuery,
    InlineKeyboardButton,
    InlineKeyboardMarkup,
    Message,
)

from .engine import storage
from .engine.registry import get_scene, total_lines
from .engine.runner import RenderResult, apply_choice, render_step
from .story import load_all  # noqa: F401  (registers scenes)

load_all()

router = Router()


def _next_kb() -> InlineKeyboardMarkup:
    return InlineKeyboardMarkup(
        inline_keyboard=[[InlineKeyboardButton(text="Дальше ▶", callback_data="next")]]
    )


def _menu_kb() -> InlineKeyboardMarkup:
    return InlineKeyboardMarkup(
        inline_keyboard=[
            [InlineKeyboardButton(text="▶ Продолжить", callback_data="next")],
            [
                InlineKeyboardButton(text="💾 Сохранить", callback_data="save_menu"),
                InlineKeyboardButton(text="📂 Загрузить", callback_data="load_menu"),
            ],
            [InlineKeyboardButton(text="🔁 Заново", callback_data="restart_confirm")],
        ]
    )


def _choices_kb(choices) -> InlineKeyboardMarkup:
    rows = [
        [InlineKeyboardButton(text=c.text, callback_data=f"choice:{i}")]
        for i, c in enumerate(choices)
    ]
    return InlineKeyboardMarkup(inline_keyboard=rows)


def _save_menu_kb(user_id: int) -> InlineKeyboardMarkup:
    saves = storage.list_saves(user_id)
    saved_slots = {s["slot"]: s for s in saves}
    rows = []
    for slot in range(1, 6):
        if slot in saved_slots:
            label = saved_slots[slot]["label"][:30]
            rows.append([InlineKeyboardButton(
                text=f"Слот {slot}: {label} (перезаписать)",
                callback_data=f"save_slot:{slot}",
            )])
        else:
            rows.append([InlineKeyboardButton(
                text=f"Слот {slot}: пусто",
                callback_data=f"save_slot:{slot}",
            )])
    rows.append([InlineKeyboardButton(text="◀ Назад", callback_data="next")])
    return InlineKeyboardMarkup(inline_keyboard=rows)


def _load_menu_kb(user_id: int) -> InlineKeyboardMarkup:
    saves = storage.list_saves(user_id)
    rows = []
    if not saves:
        rows.append([InlineKeyboardButton(text="(нет сохранений)", callback_data="noop")])
    else:
        for s in saves:
            rows.append([InlineKeyboardButton(
                text=f"Слот {s['slot']}: {s['label'][:40]}",
                callback_data=f"load_slot:{s['slot']}",
            )])
            rows.append([InlineKeyboardButton(
                text=f"❌ Удалить слот {s['slot']}",
                callback_data=f"del_slot:{s['slot']}",
            )])
    rows.append([InlineKeyboardButton(text="◀ Назад", callback_data="next")])
    return InlineKeyboardMarkup(inline_keyboard=rows)


def _restart_kb() -> InlineKeyboardMarkup:
    return InlineKeyboardMarkup(inline_keyboard=[
        [InlineKeyboardButton(text="Да, начать заново", callback_data="restart_yes")],
        [InlineKeyboardButton(text="Отмена", callback_data="next")],
    ])


def _safe_label(player: dict) -> str:
    scene_id = player["current_scene"]
    try:
        title = get_scene(scene_id).title
    except KeyError:
        title = scene_id
    return title


@router.message(CommandStart())
async def cmd_start(message: Message) -> None:
    user_id = message.from_user.id
    player = storage.get_player(user_id)
    if player is None:
        storage.upsert_player(user_id, "intro_01", 0, {})
        await message.answer(
            "<b>ГАВАНЬ</b>\n"
            "<i>Визуальная новелла</i>\n\n"
            "Лето. Ты приезжаешь на каникулы в маленький приморский "
            "городок Морянку — туда, где когда-то жил твой дед. Что тебя там ждёт?\n\n"
            "Команды: /menu — меню сохранений, /restart — начать заново.\n"
            "Нажми «Дальше», чтобы начать.",
            reply_markup=_next_kb(),
        )
    else:
        await message.answer(
            f"С возвращением. Ты остановился на сцене: <b>{_safe_label(player)}</b>.\n"
            "Нажми «Продолжить» или открой меню.",
            reply_markup=_menu_kb(),
        )


@router.message(Command("menu"))
async def cmd_menu(message: Message) -> None:
    await message.answer("Меню:", reply_markup=_menu_kb())


@router.message(Command("restart"))
async def cmd_restart(message: Message) -> None:
    await message.answer(
        "Точно начать заново? Текущий прогресс будет сброшен (сохранения остаются).",
        reply_markup=_restart_kb(),
    )


@router.message(Command("stats"))
async def cmd_stats(message: Message) -> None:
    user_id = message.from_user.id
    player = storage.get_player(user_id) or {"variables": {}}
    v = player["variables"]
    lines = ["<b>Отношения и флаги:</b>"]
    for key in sorted(v.keys()):
        lines.append(f"  {key}: {v[key]}")
    if len(lines) == 1:
        lines.append("  (пусто)")
    lines.append(f"\n<b>Всего строк диалога в новелле:</b> {total_lines()}")
    await message.answer("\n".join(lines))


async def _send_step(message_or_cb, user_id: int) -> None:
    player = storage.get_player(user_id)
    if player is None:
        if isinstance(message_or_cb, CallbackQuery):
            await message_or_cb.message.answer("Сначала /start")
        else:
            await message_or_cb.answer("Сначала /start")
        return

    result: RenderResult = render_step(player["current_scene"], player["current_index"])

    if result.is_end:
        text = (result.text or "") + "\n\n<b>— Конец главы —</b>\nНажми /restart, чтобы начать заново, или /menu."
        if isinstance(message_or_cb, CallbackQuery):
            await message_or_cb.message.answer(text, reply_markup=_menu_kb())
        else:
            await message_or_cb.answer(text, reply_markup=_menu_kb())
        return

    if result.choices:
        # Save state at choice
        storage.upsert_player(
            user_id, result.next_scene_id, result.next_index, player["variables"]
        )
        text = result.text or "Что ты выбираешь?"
        kb = _choices_kb(result.choices)
        if isinstance(message_or_cb, CallbackQuery):
            await message_or_cb.message.answer(text, reply_markup=kb)
        else:
            await message_or_cb.answer(text, reply_markup=kb)
        return

    # Normal continuation
    storage.upsert_player(
        user_id, result.next_scene_id, result.next_index, player["variables"]
    )
    text = result.text or "..."
    kb = _next_kb()
    if isinstance(message_or_cb, CallbackQuery):
        await message_or_cb.message.answer(text, reply_markup=kb)
    else:
        await message_or_cb.answer(text, reply_markup=kb)


@router.callback_query(F.data == "next")
async def cb_next(callback: CallbackQuery) -> None:
    await callback.answer()
    await _send_step(callback, callback.from_user.id)


@router.callback_query(F.data.startswith("choice:"))
async def cb_choice(callback: CallbackQuery) -> None:
    await callback.answer()
    user_id = callback.from_user.id
    player = storage.get_player(user_id)
    if player is None:
        await callback.message.answer("Сначала /start")
        return
    idx = int(callback.data.split(":")[1])
    next_scene, next_index, new_vars = apply_choice(
        player["current_scene"], player["current_index"], idx, player["variables"]
    )
    storage.upsert_player(user_id, next_scene, next_index, new_vars)
    await _send_step(callback, user_id)


@router.callback_query(F.data == "save_menu")
async def cb_save_menu(callback: CallbackQuery) -> None:
    await callback.answer()
    await callback.message.answer(
        "Выбери слот для сохранения:",
        reply_markup=_save_menu_kb(callback.from_user.id),
    )


@router.callback_query(F.data.startswith("save_slot:"))
async def cb_save_slot(callback: CallbackQuery) -> None:
    await callback.answer("Сохранено!")
    user_id = callback.from_user.id
    slot = int(callback.data.split(":")[1])
    player = storage.get_player(user_id)
    if player is None:
        await callback.message.answer("Сначала /start")
        return
    label = _safe_label(player)
    storage.save_slot(user_id, slot, label, player)
    await callback.message.answer(
        f"💾 Сохранено в слот {slot}: <b>{label}</b>",
        reply_markup=_menu_kb(),
    )


@router.callback_query(F.data == "load_menu")
async def cb_load_menu(callback: CallbackQuery) -> None:
    await callback.answer()
    await callback.message.answer(
        "Выбери слот для загрузки:",
        reply_markup=_load_menu_kb(callback.from_user.id),
    )


@router.callback_query(F.data.startswith("load_slot:"))
async def cb_load_slot(callback: CallbackQuery) -> None:
    await callback.answer("Загружено!")
    user_id = callback.from_user.id
    slot = int(callback.data.split(":")[1])
    save = storage.load_slot(user_id, slot)
    if save is None:
        await callback.message.answer("Слот пуст.")
        return
    storage.upsert_player(
        user_id, save["current_scene"], save["current_index"], save["variables"]
    )
    await callback.message.answer(
        f"📂 Загружено. Продолжай с момента: <b>{get_scene(save['current_scene']).title}</b>",
        reply_markup=_next_kb(),
    )


@router.callback_query(F.data.startswith("del_slot:"))
async def cb_del_slot(callback: CallbackQuery) -> None:
    await callback.answer("Удалено")
    user_id = callback.from_user.id
    slot = int(callback.data.split(":")[1])
    storage.delete_slot(user_id, slot)
    await callback.message.answer(
        f"Слот {slot} очищен.",
        reply_markup=_load_menu_kb(user_id),
    )


@router.callback_query(F.data == "restart_confirm")
async def cb_restart_confirm(callback: CallbackQuery) -> None:
    await callback.answer()
    await callback.message.answer(
        "Точно начать заново? Прогресс сбросится, сохранения останутся.",
        reply_markup=_restart_kb(),
    )


@router.callback_query(F.data == "restart_yes")
async def cb_restart_yes(callback: CallbackQuery) -> None:
    await callback.answer("Заново!")
    user_id = callback.from_user.id
    storage.reset_player(user_id)
    storage.upsert_player(user_id, "intro_01", 0, {})
    await callback.message.answer(
        "Начинаем сначала.",
        reply_markup=_next_kb(),
    )


@router.callback_query(F.data == "noop")
async def cb_noop(callback: CallbackQuery) -> None:
    await callback.answer()


async def main() -> None:
    logging.basicConfig(level=logging.INFO)
    storage.init_db()

    token = os.environ.get("TELEGRAM_BOT_TOKEN")
    if not token:
        # Try .env file
        env_path = Path(__file__).resolve().parent.parent / ".env"
        if env_path.exists():
            for raw in env_path.read_text().splitlines():
                if "=" in raw and not raw.strip().startswith("#"):
                    k, v = raw.split("=", 1)
                    if k.strip() == "TELEGRAM_BOT_TOKEN":
                        token = v.strip().strip('"').strip("'")
                        break
    if not token:
        raise SystemExit("TELEGRAM_BOT_TOKEN env var is required (or put it in .env)")

    bot = Bot(
        token=token,
        default=DefaultBotProperties(parse_mode=ParseMode.HTML),
    )
    dp = Dispatcher()
    dp.include_router(router)

    logging.info("Story has %d lines of dialogue.", total_lines())
    await dp.start_polling(bot)


if __name__ == "__main__":
    asyncio.run(main())
