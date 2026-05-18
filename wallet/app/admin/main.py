"""Operator admin panel.

A small FastAPI app with HTTP Basic auth giving the operator visibility
into users, balances, withdrawal queue and audit log. Designed to live on
a private network or behind a reverse proxy with TLS termination.
"""
from __future__ import annotations

import os
import secrets
from datetime import datetime
from decimal import Decimal
from pathlib import Path

from fastapi import Depends, FastAPI, HTTPException, Request, status
from fastapi.responses import HTMLResponse, RedirectResponse
from fastapi.security import HTTPBasic, HTTPBasicCredentials
from fastapi.templating import Jinja2Templates
from sqlalchemy import desc, func, select

from ..config import get_settings
from ..db.models import (
    Address,
    AuditLog,
    Balance,
    Transaction,
    TxStatus,
    User,
    WithdrawalRequest,
)
from ..db.session import session_scope

app = FastAPI(title="Custodial Wallet Admin")
security = HTTPBasic()

TEMPLATES_DIR = Path(__file__).parent / "templates"
templates = Jinja2Templates(directory=str(TEMPLATES_DIR))


def _check_auth(creds: HTTPBasicCredentials = Depends(security)) -> str:
    s = get_settings()
    correct_u = secrets.compare_digest(creds.username, s.admin_username)
    correct_p = secrets.compare_digest(creds.password, s.admin_password)
    if not (correct_u and correct_p):
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail="bad credentials",
            headers={"WWW-Authenticate": "Basic"},
        )
    return creds.username


@app.get("/", response_class=HTMLResponse)
async def index(request: Request, _: str = Depends(_check_auth)) -> HTMLResponse:
    async with session_scope() as s:
        users_count = (await s.execute(select(func.count(User.id)))).scalar() or 0
        addrs_count = (await s.execute(select(func.count(Address.id)))).scalar() or 0
        tx_count = (await s.execute(select(func.count(Transaction.id)))).scalar() or 0
        pending = (
            (await s.execute(
                select(func.count(WithdrawalRequest.id)).where(
                    WithdrawalRequest.status == TxStatus.PENDING
                )
            )).scalar() or 0
        )

        bal_q = await s.execute(
            select(Balance.chain, Balance.asset, func.sum(Balance.amount), func.sum(Balance.locked))
            .group_by(Balance.chain, Balance.asset)
        )
        totals = [
            {"chain": c.value, "asset": a.value, "total": amt or Decimal(0), "locked": lk or Decimal(0)}
            for c, a, amt, lk in bal_q.all()
        ]
    return templates.TemplateResponse(
        "index.html",
        {
            "request": request,
            "users": users_count,
            "addresses": addrs_count,
            "transactions": tx_count,
            "pending": pending,
            "totals": totals,
        },
    )


@app.get("/users", response_class=HTMLResponse)
async def users_page(request: Request, _: str = Depends(_check_auth)) -> HTMLResponse:
    async with session_scope() as s:
        res = await s.execute(select(User).order_by(desc(User.id)).limit(200))
        users = res.scalars().all()
    return templates.TemplateResponse("users.html", {"request": request, "users": users})


@app.get("/transactions", response_class=HTMLResponse)
async def tx_page(request: Request, _: str = Depends(_check_auth)) -> HTMLResponse:
    async with session_scope() as s:
        res = await s.execute(select(Transaction).order_by(desc(Transaction.id)).limit(200))
        txs = res.scalars().all()
    return templates.TemplateResponse("transactions.html", {"request": request, "txs": txs})


@app.get("/withdrawals", response_class=HTMLResponse)
async def withdrawals_page(request: Request, _: str = Depends(_check_auth)) -> HTMLResponse:
    async with session_scope() as s:
        res = await s.execute(
            select(WithdrawalRequest).order_by(desc(WithdrawalRequest.id)).limit(200)
        )
        reqs = res.scalars().all()
    return templates.TemplateResponse(
        "withdrawals.html", {"request": request, "reqs": reqs, "TxStatus": TxStatus}
    )


@app.post("/withdrawals/{wid}/approve")
async def approve_withdrawal(wid: int, _: str = Depends(_check_auth)) -> RedirectResponse:
    async with session_scope() as s:
        req = await s.get(WithdrawalRequest, wid)
        if req is None:
            raise HTTPException(404, "not found")
        req.admin_approved = True
        s.add(AuditLog(user_id=req.user_id, event="admin_approved_withdrawal",
                       payload=f"req_id={wid}"))
    return RedirectResponse("/withdrawals", status_code=303)


@app.post("/withdrawals/{wid}/cancel")
async def cancel_withdrawal_admin(wid: int, _: str = Depends(_check_auth)) -> RedirectResponse:
    from ..services.wallet import cancel_withdrawal

    async with session_scope() as s:
        req = await s.get(WithdrawalRequest, wid)
        if req is None:
            raise HTTPException(404, "not found")
        await cancel_withdrawal(s, req)
    return RedirectResponse("/withdrawals", status_code=303)


@app.get("/audit", response_class=HTMLResponse)
async def audit_page(request: Request, _: str = Depends(_check_auth)) -> HTMLResponse:
    async with session_scope() as s:
        res = await s.execute(select(AuditLog).order_by(desc(AuditLog.id)).limit(500))
        rows = res.scalars().all()
    return templates.TemplateResponse(
        "audit.html",
        {"request": request, "rows": rows, "now": datetime.utcnow()},
    )


def run() -> None:
    import uvicorn

    s = get_settings()
    uvicorn.run(
        "app.admin.main:app",
        host=s.admin_host,
        port=s.admin_port,
        log_level=s.log_level.lower(),
        access_log=False,
    )


if __name__ == "__main__":
    # PYTHONPATH/.env should be set by docker-compose or `python -m app.admin.main`
    os.environ.setdefault("PYTHONUNBUFFERED", "1")
    run()
