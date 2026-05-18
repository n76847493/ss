"""Internal off-chain transfer flow."""
from __future__ import annotations

from decimal import Decimal, InvalidOperation

from aiogram import F, Router
from aiogram.filters import Command
from aiogram.fsm.context import FSMContext
from aiogram.types import CallbackQuery, Message

from ...db.models import Asset, Chain
from ...db.session import session_scope
from ...services.registry import get_network
from ...services.transfer import internal_transfer
from ...services.wallet import get_balance, get_or_create_user
from ..keyboards import assets_kb, confirm_kb, main_menu, networks_for_asset_kb
from ..states import TransferFlow

router = Router(name="transfer")


@router.message(Command("transfer"))
@router.message(F.text == "🔁 Перевод")
async def transfer_start(msg: Message, state: FSMContext) -> None:
    await state.set_state(TransferFlow.choose_asset)
    await msg.answer(
        "Внутренний перевод между пользователями бота (off-chain, без комиссии сети).\n"
        "Выберите актив:",
        reply_markup=assets_kb("tr"),
    )


@router.callback_query(F.data == "tr:cancel")
async def transfer_cancel(cb: CallbackQuery, state: FSMContext) -> None:
    await state.clear()
    await cb.message.edit_text("Отменено.")
    await cb.answer()


@router.callback_query(F.data == "tr:back_asset")
async def transfer_back_asset(cb: CallbackQuery, state: FSMContext) -> None:
    await state.set_state(TransferFlow.choose_asset)
    await cb.message.edit_text("Выберите актив:", reply_markup=assets_kb("tr"))
    await cb.answer()


@router.callback_query(F.data.startswith("tr:asset:"))
async def transfer_pick_asset(cb: CallbackQuery, state: FSMContext) -> None:
    asset = Asset(cb.data.split(":")[-1])
    await state.update_data(asset=asset.value)
    await state.set_state(TransferFlow.choose_network)
    await cb.message.edit_text("Выберите сеть актива (виртуально):",
                               reply_markup=networks_for_asset_kb("tr", asset))
    await cb.answer()


@router.callback_query(F.data.startswith("tr:net:"))
async def transfer_pick_net(cb: CallbackQuery, state: FSMContext) -> None:
    _, _, chain, asset = cb.data.split(":")
    await state.update_data(chain=chain, asset=asset)
    await state.set_state(TransferFlow.enter_recipient)
    await cb.message.edit_text("Введите получателя — @username или Telegram ID:")
    await cb.answer()


@router.message(TransferFlow.enter_recipient)
async def transfer_recipient(msg: Message, state: FSMContext) -> None:
    rec = (msg.text or "").strip()
    if not rec:
        return
    await state.update_data(recipient=rec)
    await state.set_state(TransferFlow.enter_amount)
    data = await state.get_data()
    async with session_scope() as s:
        user = await get_or_create_user(s, telegram_id=msg.from_user.id)
        bal = await get_balance(s, user, Chain(data["chain"]), Asset(data["asset"]))
        available = (bal.amount or Decimal(0)) - (bal.locked or Decimal(0))
    await msg.answer(f"Доступно: <b>{available:.8f} {data['asset']}</b>\nВведите сумму:")


@router.message(TransferFlow.enter_amount)
async def transfer_amount(msg: Message, state: FSMContext) -> None:
    try:
        amount = Decimal((msg.text or "").strip().replace(",", "."))
        if amount <= 0:
            raise InvalidOperation()
    except InvalidOperation:
        await msg.answer("Сумма не понята. Положительное число, например 10.5.")
        return
    await state.update_data(amount=str(amount))
    data = await state.get_data()
    network = get_network(Chain(data["chain"]), Asset(data["asset"]))
    text = (
        "<b>Подтверждение перевода</b>\n\n"
        f"Получатель: <code>{data['recipient']}</code>\n"
        f"Сеть: <b>{network.label if network else data['chain']}</b>\n"
        f"Актив: <b>{data['asset']}</b>\n"
        f"Сумма: <b>{data['amount']} {data['asset']}</b>\n"
    )
    await state.set_state(TransferFlow.confirm)
    await msg.answer(text, reply_markup=confirm_kb("tr"))


@router.callback_query(TransferFlow.confirm, F.data == "tr:confirm")
async def transfer_confirm(cb: CallbackQuery, state: FSMContext) -> None:
    data = await state.get_data()
    async with session_scope() as s:
        user = await get_or_create_user(s, telegram_id=cb.from_user.id)
        try:
            await internal_transfer(
                s,
                sender=user,
                recipient_username_or_id=data["recipient"],
                chain=Chain(data["chain"]),
                asset=Asset(data["asset"]),
                amount=Decimal(data["amount"]),
            )
        except ValueError as e:
            await cb.message.edit_text(f"❌ {e}")
            await state.clear()
            await cb.answer()
            return
    await cb.message.edit_text("Перевод выполнен.")
    await cb.message.answer("Готово.", reply_markup=main_menu())
    await state.clear()
    await cb.answer()
