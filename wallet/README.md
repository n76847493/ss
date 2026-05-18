# Custodial Telegram Wallet Bot

Production-leaning skeleton of a custodial cryptocurrency wallet exposed as a
Telegram bot, supporting:

| Asset | Networks                                                          |
|-------|-------------------------------------------------------------------|
| BTC   | Bitcoin mainnet (Esplora API for reads, Bitcoin Core RPC for sends) |
| USDT  | ERC-20 (Ethereum) · BEP-20 (BSC) · Polygon · TRC-20 (Tron) · Jetton (TON) |
| USDC  | ERC-20 · BEP-20 · Polygon · TRC-20 · SPL (Solana)                 |
| TON   | The Open Network                                                  |

The project is **explicitly NOT a mixer**. Every address remains publicly
traceable on its respective chain; per-deposit address rotation is a
standard exchange/UX pattern, not an anonymization tool.

---

## Features

* **HD wallet (BIP32/44/84):** a single 24-word operator mnemonic is
  encrypted with `cryptography.Fernet` and stored as the
  `MASTER_SEED_ENCRYPTED` env var. Deposit addresses are derived
  deterministically — `m/84'/0'/0'/0/{idx}` for BTC, `m/44'/60'/0'/0/{idx}`
  for EVM, `m/44'/195'/0'/0/{idx}` for TRON, `m/44'/607'/0'/0/{idx}` for
  TON, `m/44'/501'/{idx}'/0'` for Solana.
* **One-time receive addresses:** every `/deposit` mints a fresh derivation
  index for the user/asset/chain.
* **Off-chain internal transfers:** users can move balances to other bot
  users instantly without paying network fees.
* **On-chain withdrawals:** direct from the operator hot wallet, with
  optional admin approval for amounts above the daily/2FA threshold.
* **History + statements:** filterable transaction log, PDF and CSV export
  for arbitrary time ranges.
* **2FA (TOTP):** users can enable Google Authenticator / Authy. Triggered
  automatically for withdrawals above `WITHDRAW_REQUIRE_2FA_OVER_USD`.
* **Limits / anti-fraud:** per-tx and 24h USD caps with real-time CoinGecko
  pricing.
* **Admin panel:** FastAPI + Jinja templates over HTTP Basic Auth. Shows
  users, balances, transactions, withdrawal queue, audit log; lets the
  operator approve or cancel pending withdrawals.
* **Background worker:** APScheduler periodically scans deposit addresses
  and processes the withdrawal queue.

## Architecture

```
┌──────────────┐    ┌──────────────┐    ┌──────────────┐
│ Telegram bot │    │   Worker     │    │  Admin UI    │
│  (aiogram)   │    │ (APScheduler)│    │  (FastAPI)   │
└──────┬───────┘    └──────┬───────┘    └──────┬───────┘
       │                   │                   │
       └─────────┬─────────┴─────────┬─────────┘
                 │                   │
            ┌────▼────┐         ┌────▼────┐
            │Postgres │         │  Redis  │
            └─────────┘         └─────────┘
                 ▲                   ▲
                 │                   │
            ┌────┴────────────────────┴────┐
            │  Chain adapters (BTC, EVM,   │
            │  TRON, TON, Solana). Each    │
            │  uses configured RPC; falls  │
            │  back to Offline mode when   │
            │  RPC env vars are blank.     │
            └──────────────────────────────┘
```

Internal balance ledger (`balances` table) is the source of truth for what
the user owns. The on-chain funds in the operator wallet back this ledger;
the ratio is monitored from the admin panel.

## Deployment

### 0. Prerequisites

* Docker + Docker Compose v2
* A bot token from `@BotFather`
* (Recommended for production) RPC endpoints for each chain you want to
  enable. Without RPC you still get address generation and the off-chain
  internal-transfer flow, but automated deposit detection and withdrawal
  broadcast are disabled.

### 1. Clone and configure

```bash
git clone <this-repo>
cd wallet
cp .env.example .env
```

### 2. Generate operator seed + encryption key

```bash
docker compose run --rm bot python -m app.crypto.seed gen
```

This prints a **Fernet key** and a **24-word mnemonic**. Treat the mnemonic
the same way an exchange would treat its cold-wallet root — store it on
two paper backups in different physical locations, *never* commit it.

* Put the Fernet key into `MASTER_KEY` in `.env`.
* Encrypt the mnemonic with that key:

```bash
MNEMONIC="<paste 24 words here>" \
docker compose run --rm bot python -m app.crypto.seed encrypt
```

* Put the resulting ciphertext into `MASTER_SEED_ENCRYPTED` in `.env`.
* For real production traffic the recommended setup is to store the
  mnemonic in an HSM/KMS (AWS KMS, GCP KMS, YubiHSM, …) and have the bot
  fetch it at boot via short-lived credentials. The Fernet-encrypted env
  var is appropriate for staging and small operations.

### 3. Fill in the rest of `.env`

* `BOT_TOKEN` — from BotFather
* `ADMIN_TELEGRAM_IDS` — your Telegram numeric ID(s)
* `ADMIN_USERNAME` / `ADMIN_PASSWORD` — for the admin panel (basic auth)
* `*_RPC_URL` and API keys for the chains you want online (any subset).
  Recommended providers: Alchemy / Infura / QuickNode for EVM,
  Tatum / GetBlock / TronGrid for Tron, TonCenter for TON, Helius / public
  RPC for Solana. Leaving an RPC blank disables network ops for that
  chain (deposit addresses still get derived).
* `COLD_ADDR_*` — addresses of your cold wallets; once the hot balance
  exceeds `COLD_THRESHOLD_USD`, the operator should move surplus there.

### 4. Bring everything up

```bash
docker compose up -d
docker compose logs -f bot worker admin
```

* The bot will start polling Telegram.
* The worker runs the deposit scanner every 60 s and the withdrawal
  processor every 30 s.
* The admin panel will be exposed on `127.0.0.1:8080`. Put it behind a
  reverse proxy with TLS (nginx / Caddy / Traefik) when deploying
  remotely — never expose it on a public IP without TLS + basic auth +
  IP allowlist.

### 5. Database migrations

The `migrate` service runs `alembic upgrade head` once at startup. To
apply migrations manually:

```bash
docker compose run --rm bot alembic upgrade head
```

### 6. Sanity check

```bash
# Bot:
docker compose exec bot python -c "from app.config import get_settings; print(get_settings().bot_token[:8] + '...')"

# Address derivation works:
docker compose exec bot python -c "from app.crypto.hd import derive_btc; print(derive_btc(0).address)"

# DB schema:
docker compose exec db psql -U wallet -d wallet -c "\dt"
```

Open the bot in Telegram, hit `/start`, request a deposit address.

## Running tests

```bash
pip install -e ".[dev]"
pytest -q
```

The test suite covers HD derivation against the canonical
`abandon … about` mnemonic, statement (PDF/CSV) generation, and TOTP
verification.

## Operating notes

* **Hot/cold split:** the worker uses derivation index `0` of each chain
  as the operator hot wallet. Surplus must be manually moved to the
  configured `COLD_ADDR_*` once the dashboard shows the hot wallet over
  the configured `COLD_THRESHOLD_USD`. (Automating cold sweeps is a
  policy decision — we deliberately leave that to the operator rather
  than ship an opinionated automatic mover.)
* **Withdrawals:** small withdrawals are auto-broadcast by the worker
  through the appropriate chain adapter. For larger ones the admin panel
  exposes Approve / Cancel buttons; once approved, the worker broadcasts
  on the next tick. BTC withdrawals require a Bitcoin Core RPC URL —
  Esplora is read-only.
* **Compliance:** depending on your jurisdiction operating a custodial
  cryptocurrency service is regulated (money transmitter / VASP / e-money
  licence). Before going to production make sure you have AML / KYC
  policies in place, sanctions screening (OFAC / EU / UN lists),
  travel-rule support if required, and a periodic on-chain attestation
  of the hot+cold balance vs the off-chain ledger.

## Layout

```
wallet/
├── app/
│   ├── admin/         # FastAPI admin panel + templates
│   ├── bot/           # aiogram bot, handlers, FSM states
│   ├── crypto/        # HD derivation + per-chain adapters
│   ├── db/            # SQLAlchemy models + async session
│   ├── services/      # wallet, transfer, history, statement, twofa, limits, pricing
│   └── worker/        # APScheduler-based deposit + withdrawal workers
├── alembic/           # Migrations
├── tests/             # pytest
├── docker-compose.yml
├── Dockerfile
├── pyproject.toml
└── README.md
```
