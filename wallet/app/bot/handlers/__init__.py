"""Aiogram handler routers."""
from __future__ import annotations

from aiogram import Router

from . import deposit, history, start, statement, transfer, withdraw
from . import settings as settings_h


def build_root_router() -> Router:
    r = Router()
    r.include_router(start.router)
    r.include_router(deposit.router)
    r.include_router(withdraw.router)
    r.include_router(transfer.router)
    r.include_router(history.router)
    r.include_router(statement.router)
    r.include_router(settings_h.router)
    return r
