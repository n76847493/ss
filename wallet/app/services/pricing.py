"""Lightweight USD price oracle using CoinGecko."""
from __future__ import annotations

import asyncio
import time
from decimal import Decimal

import httpx

from ..config import get_settings

_CACHE: dict[str, tuple[float, Decimal]] = {}
_CACHE_TTL = 60

_COIN_IDS = {
    "BTC": "bitcoin",
    "USDT": "tether",
    "USDC": "usd-coin",
    "TON": "the-open-network",
}

_lock = asyncio.Lock()


async def fetch_price_usd(asset: str) -> Decimal:
    cached = _CACHE.get(asset)
    if cached and time.time() - cached[0] < _CACHE_TTL:
        return cached[1]
    async with _lock:
        cached = _CACHE.get(asset)
        if cached and time.time() - cached[0] < _CACHE_TTL:
            return cached[1]
        coin_id = _COIN_IDS.get(asset)
        if coin_id is None:
            return Decimal(0)
        s = get_settings()
        params = {"ids": coin_id, "vs_currencies": "usd"}
        headers = {}
        if s.coingecko_api_key:
            headers["x-cg-pro-api-key"] = s.coingecko_api_key
        try:
            async with httpx.AsyncClient(timeout=10.0) as client:
                r = await client.get(
                    "https://api.coingecko.com/api/v3/simple/price",
                    params=params,
                    headers=headers,
                )
                r.raise_for_status()
                price = Decimal(str(r.json()[coin_id]["usd"]))
        except Exception:
            # graceful fallback for offline / rate-limit environments
            fallback = {"USDT": Decimal("1.0"), "USDC": Decimal("1.0")}
            price = fallback.get(asset, Decimal(0))
        _CACHE[asset] = (time.time(), price)
        return price


async def to_usd(asset: str, amount: Decimal) -> Decimal:
    price = await fetch_price_usd(asset)
    return amount * price
