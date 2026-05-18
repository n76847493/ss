"""Deposit flow: pick asset → pick network → mint fresh address."""
from __future__ import annotations

from aiogram import F, Router
from aiogram.filters import Command
from aiogram.fsm.context import FSMContext
from aiogram.types import CallbackQuery, Message

from ...db.models import Asset, Chain
from ...db.session import session_scope
from ...services.registry import get_network
from ...services.wallet import (
    chain_supports_online,
    get_or_create_user,
    issue_deposit_address,
)
from ..keyboards import assets_kb, main_menu, networks_for_asset_kb
from ..states import DepositFlow

router = Router(name="deposit")


@router.message(Command("deposit"))
@router.message(F.text == "📥 Пополнить")
async def deposit_start(msg: Message, state: FSMContext) -> None:
    await state.set_state(DepositFlow.choose_asset)
    await msg.answer("Выберите актив для пополнения:", reply_markup=assets_kb("dep"))


@router.callback_query(F.data == "dep:cancel")
async def deposit_cancel(cb: CallbackQuery, state: FSMContext) -> None:
    await state.clear()
    await cb.message.edit_text("Отменено.")
    await cb.answer()


@router.callback_query(F.data == "dep:back_asset")
async def deposit_back_asset(cb: CallbackQuery, state: FSMContext) -> None:
    await state.set_state(DepositFlow.choose_asset)
    await cb.message.edit_text("Выберите актив для пополнения:", reply_markup=assets_kb("dep"))
    await cb.answer()


@router.callback_query(F.data.startswith("dep:asset:"))
async def deposit_pick_asset(cb: CallbackQuery, state: FSMContext) -> None:
    asset = Asset(cb.data.split(":")[-1])
    await state.update_data(asset=asset.value)
    await state.set_state(DepositFlow.choose_network)
    await cb.message.edit_text(
        f"Выберите сеть для {asset.value}:",
        reply_markup=networks_for_asset_kb("dep", asset),
    )
    await cb.answer()


@router.callback_query(F.data.startswith("dep:net:"))
async def deposit_pick_net(cb: CallbackQuery, state: FSMContext) -> None:
    _, _, chain, asset = cb.data.split(":")
    chain_e = Chain(chain)
    asset_e = Asset(asset)
    network = get_network(chain_e, asset_e)
    if network is None:
        await cb.answer("сеть не поддерживается", show_alert=True)
        return

    async with session_scope() as s:
        user = await get_or_create_user(
            s,
            telegram_id=cb.from_user.id,
            username=cb.from_user.username,
            first_name=cb.from_user.first_name,
        )
        addr = await issue_deposit_address(s, user, chain_e, asset_e)
        address = addr.address

    online = chain_supports_online(chain_e)
    note = ""
    if not online:
        note = (
            "\n\n⚠️ В этой среде RPC для данной сети не сконфигурирован — "
            "адрес сгенерирован детерминированно, но автоматическое зачисление "
            "пополнений будет невозможно до настройки `*_RPC_URL` в `.env`."
        )

    text = (
        f"<b>Адрес пополнения</b>\n\n"
        f"Сеть: <b>{network.label}</b>\n"
        f"Актив: <b>{asset_e.value}</b>\n"
        f"Мин. подтверждений: {network.min_confirmations}\n\n"
        f"<code>{address}</code>\n\n"
        f"<a href=\"{network.explorer_address.format(a=address)}\">Открыть в эксплорере</a>\n\n"
        f"Это новый одноразовый адрес — он привязан к вашему счёту, на него можно "
        f"отправлять только {asset_e.value} в указанной сети. "
        f"Любая другая сеть/токен → средства будут потеряны."
        f"{note}"
    )
    await state.clear()
    await cb.message.edit_text(text, disable_web_page_preview=True)
    await cb.message.answer("Готово.", reply_markup=main_menu())
    await cb.answer()
