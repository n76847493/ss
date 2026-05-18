"""Background worker — runs APScheduler with deposit + withdrawal jobs."""
from __future__ import annotations

import asyncio

from apscheduler.schedulers.asyncio import AsyncIOScheduler

from ..logging_setup import configure_logging, get_logger
from .deposit_scanner import scan_once
from .withdrawal_processor import process_once

log = get_logger("worker")


async def amain() -> None:
    configure_logging()
    sched = AsyncIOScheduler(timezone="UTC")
    sched.add_job(scan_once, "interval", seconds=60, id="scan", max_instances=1, coalesce=True)
    sched.add_job(process_once, "interval", seconds=30, id="withdraw", max_instances=1, coalesce=True)
    sched.start()
    log.info("worker.started")
    while True:
        await asyncio.sleep(3600)


def main() -> None:
    asyncio.run(amain())


if __name__ == "__main__":
    main()
