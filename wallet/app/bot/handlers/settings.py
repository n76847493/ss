"""User settings: 2FA management, ID display."""
from __future__ import annotations

from aiogram import F, Router
from aiogram.filters import Command
from aiogram.fsm.context import FSMContext
from aiogram.types import BufferedInputFile, CallbackQuery, Message

from ...db.session import session_scope
from ...services.twofa import (
    disable_totp,
    make_qr_png,
    setup_totp,
    totp_uri,
    verify_and_enable,
)
from ...services.wallet import get_or_create_user
from ..keyboards import main_menu, settings_kb
from ..states import TOTPFlow

router = Router(name="settings")


@router.message(Command("settings"))
@router.message(F.text == "⚙️ Настройки")
async def settings_open(msg: Message) -> None:
    async with session_scope() as s:
        user = await get_or_create_user(s, telegram_id=msg.from_user.id, username=msg.from_user.username)
        totp = user.totp_enabled
    await msg.answer(
        "<b>Настройки</b>\n2FA защищает крупные выводы (порог настраивается оператором).",
        reply_markup=settings_kb(totp),
    )


@router.callback_query(F.data == "set:cancel")
async def settings_cancel(cb: CallbackQuery) -> None:
    await cb.message.edit_text("OK.")
    await cb.answer()


@router.callback_query(F.data == "set:id")
async def settings_id(cb: CallbackQuery) -> None:
    await cb.message.answer(
        f"Ваш Telegram ID: <code>{cb.from_user.id}</code>\n"
        f"Username: <code>@{cb.from_user.username or '-'}</code>",
        reply_markup=main_menu(),
    )
    await cb.answer()


@router.callback_query(F.data == "set:totp")
async def settings_totp(cb: CallbackQuery, state: FSMContext) -> None:
    async with session_scope() as s:
        user = await get_or_create_user(s, telegram_id=cb.from_user.id, username=cb.from_user.username)
        if user.totp_enabled:
            await disable_totp(s, user)
            await cb.message.answer("2FA отключена.", reply_markup=main_menu())
            await cb.answer()
            return
        secret = await setup_totp(s, user)
        user.totp_secret = secret  # ensure committed
        uri = totp_uri(user)

    qr = make_qr_png(uri)
    await cb.message.answer_photo(
        BufferedInputFile(qr, filename="qr.png"),
        caption=(
            "Отсканируйте QR-код в Google Authenticator / Authy / 1Password.\n"
            f"Секрет (резерв): <code>{secret}</code>\n\n"
            "Затем пришлите 6-значный код для подтверждения."
        ),
    )
    await state.set_state(TOTPFlow.confirm)
    await cb.answer()


@router.message(TOTPFlow.confirm)
async def totp_confirm(msg: Message, state: FSMContext) -> None:
    code = (msg.text or "").strip()
    async with session_scope() as s:
        user = await get_or_create_user(s, telegram_id=msg.from_user.id)
        ok = await verify_and_enable(s, user, code)
    if ok:
        await msg.answer("✅ 2FA включена.", reply_markup=main_menu())
        await state.clear()
    else:
        await msg.answer("❌ Неверный код, попробуйте ещё раз или /settings для выхода.")
