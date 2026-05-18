"""FSM states for multi-step bot flows."""
from __future__ import annotations

from aiogram.fsm.state import State, StatesGroup


class WithdrawFlow(StatesGroup):
    choose_asset = State()
    choose_network = State()
    enter_address = State()
    enter_amount = State()
    enter_2fa = State()
    confirm = State()


class TransferFlow(StatesGroup):
    choose_asset = State()
    choose_network = State()
    enter_recipient = State()
    enter_amount = State()
    confirm = State()


class DepositFlow(StatesGroup):
    choose_asset = State()
    choose_network = State()


class TOTPFlow(StatesGroup):
    show_qr = State()
    confirm = State()


class HistoryFlow(StatesGroup):
    filtering = State()


class StatementFlow(StatesGroup):
    idle = State()
