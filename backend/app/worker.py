from __future__ import annotations

import logging
import time
from datetime import datetime, timedelta

from sqlalchemy import select
from sqlalchemy.orm import joinedload

from .db import SessionLocal
from . import models
from .runner import execute_check_run

logging.basicConfig(level=logging.INFO, format="%(asctime)s %(levelname)s %(message)s")
logger = logging.getLogger(__name__)

POLL_INTERVAL_SECONDS = 30


def should_run(config: models.CheckConfig) -> bool:
    if not config.is_enabled or not config.schedule_interval_minutes:
        return False
    if config.last_run_at is None:
        return True
    next_run = config.last_run_at + timedelta(minutes=config.schedule_interval_minutes)
    return datetime.utcnow() >= next_run


def run_scheduler_loop() -> None:
    logger.info("DQ worker started")
    while True:
        db = SessionLocal()
        try:
            configs = db.scalars(
                select(models.CheckConfig)
                .options(
                    joinedload(models.CheckConfig.dataset),
                    joinedload(models.CheckConfig.attribute),
                    joinedload(models.CheckConfig.check_type),
                    joinedload(models.CheckConfig.notification_rule),
                )
                .where(models.CheckConfig.is_enabled.is_(True))
            ).all()
            due_configs = [config for config in configs if should_run(config)]
            if due_configs:
                logger.info("Found %s due checks", len(due_configs))
            for config in due_configs:
                logger.info("Running scheduled check %s (%s)", config.check_config_id, config.check_name)
                execute_check_run(db, config, trigger_mode="scheduled")
        except Exception as exc:  # noqa: BLE001
            logger.exception("Worker iteration failed: %s", exc)
            db.rollback()
        finally:
            db.close()
        time.sleep(POLL_INTERVAL_SECONDS)


if __name__ == "__main__":
    run_scheduler_loop()
