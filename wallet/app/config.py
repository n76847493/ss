"""Application configuration loaded from environment variables."""
from __future__ import annotations

from functools import lru_cache

from pydantic import Field
from pydantic_settings import BaseSettings, SettingsConfigDict


class Settings(BaseSettings):
    model_config = SettingsConfigDict(
        env_file=".env",
        env_file_encoding="utf-8",
        case_sensitive=False,
        extra="ignore",
    )

    # Telegram
    bot_token: str = Field(default="")
    admin_telegram_ids: str = Field(default="")

    # Admin web
    admin_username: str = Field(default="admin")
    admin_password: str = Field(default="change-me")
    admin_host: str = Field(default="0.0.0.0")
    admin_port: int = Field(default=8080)

    # DB / Redis
    database_url: str = Field(default="sqlite+aiosqlite:///./wallet.db")
    database_url_sync: str = Field(default="sqlite:///./wallet.db")
    redis_url: str = Field(default="redis://localhost:6379/0")

    # Crypto
    master_key: str = Field(default="")
    master_seed_encrypted: str = Field(default="")

    # Sweep / cold
    sweep_threshold_usd: float = Field(default=25)
    cold_threshold_usd: float = Field(default=10000)
    cold_addr_btc: str = ""
    cold_addr_eth: str = ""
    cold_addr_bsc: str = ""
    cold_addr_polygon: str = ""
    cold_addr_tron: str = ""
    cold_addr_ton: str = ""
    cold_addr_sol: str = ""

    # Withdraw limits
    withdraw_daily_limit_usd: float = 5000
    withdraw_per_tx_limit_usd: float = 2000
    withdraw_require_2fa_over_usd: float = 100

    # Chain RPC
    btc_rpc_url: str = ""
    btc_network: str = "mainnet"
    btc_esplora_url: str = "https://blockstream.info/api"

    eth_rpc_url: str = ""
    eth_usdt_contract: str = "0xdAC17F958D2ee523a2206206994597C13D831ec7"
    eth_usdc_contract: str = "0xA0b86991c6218b36c1d19D4a2e9Eb0cE3606eB48"

    bsc_rpc_url: str = ""
    bsc_usdt_contract: str = "0x55d398326f99059fF775485246999027B3197955"
    bsc_usdc_contract: str = "0x8AC76a51cc950d9822D68b83fE1Ad97B32Cd580d"

    polygon_rpc_url: str = ""
    polygon_usdt_contract: str = "0xc2132D05D31c914a87C6611C10748AEb04B58e8F"
    polygon_usdc_contract: str = "0x3c499c542cEF5E3811e1192ce70d8cC03d5c3359"

    tron_api_url: str = "https://api.trongrid.io"
    tron_api_key: str = ""
    tron_usdt_contract: str = "TR7NHqjeKQxGTCi8q8ZY4pL8otSzgjLj6t"
    tron_usdc_contract: str = "TEkxiTehnzSmSe2XqrBj4w3RF1F5dnp5j7"

    ton_api_url: str = "https://toncenter.com/api/v2"
    ton_api_key: str = ""
    ton_usdt_jetton: str = "EQCxE6mUtQJKFnGfaROTKOt1lZbDiiX1kCixRv7Nw2Id_sDs"

    sol_rpc_url: str = "https://api.mainnet-beta.solana.com"
    sol_usdc_mint: str = "EPjFWdd5AufqSSqeM2qN1xzybapC8G4wEGGkZwyTDt1v"

    price_provider: str = "coingecko"
    coingecko_api_key: str = ""

    log_level: str = "INFO"

    @property
    def admin_telegram_id_list(self) -> list[int]:
        out: list[int] = []
        for chunk in (self.admin_telegram_ids or "").split(","):
            chunk = chunk.strip()
            if not chunk:
                continue
            try:
                out.append(int(chunk))
            except ValueError:
                continue
        return out


@lru_cache
def get_settings() -> Settings:
    return Settings()
