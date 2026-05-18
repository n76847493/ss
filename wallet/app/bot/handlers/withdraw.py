"""Withdrawal flow."""
from __future__ import annotations

from decimal import Decimal, InvalidOperation

from aiogram import F, Router
from aiogram.filters import Command
from aiogram.fsm.context import FSMContext
from aiogram.types import CallbackQuery, Message

from ...db.models import Asset, Chain
from ...db.session import session_scope
from ...services.limits import LimitError, check_withdrawal
from ...services.registry import get_network
from ...services.twofa import verify_code
from ...services.wallet import (
    get_balance,
    get_or_create_user,
    request_withdrawal,
)
from ..keyboards import assets_kb, confirm_kb, main_menu, networks_for_asset_kb
from ..states import WithdrawFlow

router = Router(name="withdraw")


@router.message(Command("withdraw"))
@router.message(F.text == "📤 Вывести")
async def withdraw_start(msg: Message, state: FSMContext) -> None:
    await state.set_state(WithdrawFlow.choose_asset)
    await msg.answer("Выберите актив для вывода:", reply_markup=assets_kb("wd"))


@router.callback_query(F.data == "wd:cancel")
async def withdraw_cancel(cb: CallbackQuery, state: FSMContext) -> None:
    await state.clear()
    await cb.message.edit_text("Отменено.")
    await cb.answer()


@router.callback_query(F.data == "wd:back_asset")
async def withdraw_back_asset(cb: CallbackQuery, state: FSMContext) -> None:
    await state.set_state(WithdrawFlow.choose_asset)
    await cb.message.edit_text("Выберите актив для вывода:", reply_markup=assets_kb("wd"))
    await cb.answer()


@router.callback_query(F.data.startswith("wd:asset:"))
async def withdraw_pick_asset(cb: CallbackQuery, state: FSMContext) -> None:
    asset = Asset(cb.data.split(":")[-1])
    await state.update_data(asset=asset.value)
    await state.set_state(WithdrawFlow.choose_network)
    await cb.message.edit_text(
        f"Сеть для вывода {asset.value}:",
        reply_markup=networks_for_asset_kb("wd", asset),
    )
    await cb.answer()


@router.callback_query(F.data.startswith("wd:net:"))
async def withdraw_pick_net(cb: CallbackQuery, state: FSMContext) -> None:
    _, _, chain, asset = cb.data.split(":")
    await state.update_data(chain=chain, asset=asset)
    await state.set_state(WithdrawFlow.enter_address)
    await cb.message.edit_text(
        f"Введите адрес получателя в сети <b>{chain}</b> для <b>{asset}</b>:"
    )
    await cb.answer()


@router.message(WithdrawFlow.enter_address)
async def withdraw_enter_address(msg: Message, state: FSMContext) -> None:
    address = (msg.text or "").strip()
    if len(address) < 10:
        await msg.answer("Адрес выглядит подозрительно коротко. Введите ещё раз.")
        return
    await state.update_data(address=address)
    await state.set_state(WithdrawFlow.enter_amount)
    data = await state.get_data()
    async with session_scope() as s:
        user = await get_or_create_user(s, telegram_id=msg.from_user.id)
        bal = await get_balance(s, user, Chain(data["chain"]), Asset(data["asset"]))
        available = (bal.amount or Decimal(0)) - (bal.locked or Decimal(0))
    await msg.answer(
        f"Доступно: <b>{available:.8f} {data['asset']}</b>\nВведите сумму:"
    )


@router.message(WithdrawFlow.enter_amount)
async def withdraw_enter_amount(msg: Message, state: FSMContext) -> None:
    try:
        amount = Decimal((msg.text or "").strip().replace(",", "."))
        if amount <= 0:
            raise InvalidOperation()
    except InvalidOperation:
        await msg.answer("Не понял сумму. Введите положительное число.")
        return
    data = await state.get_data()

    async with session_scope() as s:
        user = await get_or_create_user(s, telegram_id=msg.from_user.id)
        try:
            info = await check_withdrawal(
                s, user,
                chain=data["chain"], asset=data["asset"], amount=amount,
            )
        except LimitError as e:
            await msg.answer(f"❌ {e}")
            await state.clear()
            return

    await state.update_data(amount=str(amount), needs_2fa=info["needs_2fa"], usd=str(info["usd_value"]))

    if info["needs_2fa"] and user.totp_enabled:
        await state.set_state(WithdrawFlow.enter_2fa)
        await msg.answer("Введите 6-значный код 2FA:")
        return

    await _show_confirm(msg, state)


@router.message(WithdrawFlow.enter_2fa)
async def withdraw_enter_2fa(msg: Message, state: FSMContext) -> None:
    code = (msg.text or "").strip()
    async with session_scope() as s:
        user = await get_or_create_user(s, telegram_id=msg.from_user.id)
        if not verify_code(user, code):
            await msg.answer("Неверный код. Попробуйте ещё раз.")
            return
    await _show_confirm(msg, state)


async def _show_confirm(msg: Message, state: FSMContext) -> None:
    data = await state.get_data()
    network = get_network(Chain(data["chain"]), Asset(data["asset"]))
    text = (
        "<b>Подтверждение вывода</b>\n\n"
        f"Сеть: <b>{network.label if network else data['chain']}</b>\n"
        f"Актив: <b>{data['asset']}</b>\n"
        f"Сумма: <b>{data['amount']} {data['asset']}</b> (≈ ${data['usd']})\n"
        f"Адрес: <code>{data['address']}</code>\n\n"
        "Эта операция необратима после подтверждения. Продолжаем?"
    )
    await state.set_state(WithdrawFlow.confirm)
    await msg.answer(text, reply_markup=confirm_kb("wd"))


@router.callback_query(WithdrawFlow.confirm, F.data == "wd:confirm")
async def withdraw_confirm(cb: CallbackQuery, state: FSMContext) -> None:
    data = await state.get_data()
    async with session_scope() as s:
        user = await get_or_create_user(s, telegram_id=cb.from_user.id)
        try:
            req = await request_withdrawal(
                s, user,
                chain=Chain(data["chain"]),
                asset=Asset(data["asset"]),
                amount=Decimal(data["amount"]),
                address=data["address"],
            )
        except ValueError as e:
            await cb.message.edit_text(f"❌ {e}")
            await state.clear()
            await cb.answer()
            return
        req_id = req.id
    await cb.message.edit_text(
        f"Запрос на вывод #{req_id} принят. Воркер обработает его в течение нескольких минут — "
        "при недоступных RPC администратор увидит запрос в админ-панели и подтвердит вручную.",
        reply_markup=None,
    )
    await cb.message.answer("Готово.", reply_markup=main_menu())
    await state.clear()
    await cb.answer()
