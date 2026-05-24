from __future__ import annotations

import logging
import time
from datetime import datetime, timedelta, timezone
from zoneinfo import ZoneInfo, ZoneInfoNotFoundError

from sqlalchemy import select
from sqlalchemy.orm import joinedload

from . import models
from .db import SessionLocal, ensure_schedule_columns
from .runner import execute_check_run

logging.basicConfig(level=logging.INFO, format="%(asctime)s %(levelname)s %(message)s")
logger = logging.getLogger(__name__)

POLL_INTERVAL_SECONDS = 30
DEFAULT_TIMEZONE = "Europe/Moscow"


def _safe_timezone(name: str | None) -> ZoneInfo:
    try:
        return ZoneInfo(name or DEFAULT_TIMEZONE)
    except ZoneInfoNotFoundError:
        logger.warning("Unknown timezone %s, fallback to %s", name, DEFAULT_TIMEZONE)
        return ZoneInfo(DEFAULT_TIMEZONE)


def _last_run_as_local(config: models.CheckConfig, tz: ZoneInfo) -> datetime | None:
    if config.last_run_at is None:
        return None
    # В БД время хранится без timezone, но создаётся через datetime.utcnow().
    # Поэтому интерпретируем last_run_at как UTC и переводим в локальную зону расписания.
    return config.last_run_at.replace(tzinfo=timezone.utc).astimezone(tz)


def _planned_datetime_today(config: models.CheckConfig, now_local: datetime) -> datetime | None:
    if config.schedule_time is None:
        return None
    return datetime.combine(now_local.date(), config.schedule_time, tzinfo=now_local.tzinfo)


def should_run(config: models.CheckConfig, now_utc: datetime | None = None) -> bool:
    if not config.is_enabled:
        return False

    schedule_type = (config.schedule_type or "manual").lower()
    now_utc = now_utc or datetime.now(timezone.utc)

    if schedule_type == "manual":
        return False

    if schedule_type == "interval":
        if not config.schedule_interval_minutes or config.schedule_interval_minutes <= 0:
            return False
        if config.last_run_at is None:
            return True
        next_run = config.last_run_at.replace(tzinfo=timezone.utc) + timedelta(minutes=config.schedule_interval_minutes)
        return now_utc >= next_run

    tz = _safe_timezone(config.schedule_timezone)
    now_local = now_utc.astimezone(tz)
    planned_local = _planned_datetime_today(config, now_local)
    if planned_local is None or now_local < planned_local:
        return False

    if schedule_type == "daily":
        pass
    elif schedule_type == "weekly":
        # ISO weekday: Monday = 1, Sunday = 7.
        if config.schedule_day_of_week is None or now_local.isoweekday() != config.schedule_day_of_week:
            return False
    elif schedule_type == "monthly":
        if config.schedule_day_of_month is None or now_local.day != config.schedule_day_of_month:
            return False
    else:
        return False

    last_run_local = _last_run_as_local(config, tz)
    return last_run_local is None or last_run_local < planned_local


def run_scheduler_loop() -> None:
    ensure_schedule_columns()
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
                .where(models.CheckConfig.schedule_type != "manual")
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
