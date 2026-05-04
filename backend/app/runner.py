from __future__ import annotations

from datetime import datetime

from sqlalchemy import select
from sqlalchemy.orm import Session, joinedload

from . import checks, models, schemas
from .notifications import send_email_alert


def get_check_config(db: Session, check_config_id: int) -> models.CheckConfig | None:
    return db.scalar(
        select(models.CheckConfig)
        .options(
            joinedload(models.CheckConfig.dataset),
            joinedload(models.CheckConfig.attribute),
            joinedload(models.CheckConfig.check_type),
            joinedload(models.CheckConfig.notification_rule),
        )
        .where(models.CheckConfig.check_config_id == check_config_id)
    )


def should_send_notification(config: models.CheckConfig, result: models.CheckResult) -> bool:
    if not config.notification_rule:
        return False
    rule = config.notification_rule
    if rule.critical_only and config.severity != "critical":
        return False
    return rule.notify_on_status == "always" or result.status == rule.notify_on_status


def build_notification(config: models.CheckConfig, run: models.CheckRun, result: models.CheckResult) -> tuple[str, str]:
    subject = f"[DQ] {config.check_name}: {result.status.upper()}"
    body = (
        f"Check: {config.check_name}\n"
        f"Dataset: {config.dataset.schema_name}.{config.dataset.table_name}\n"
        f"Check type: {config.check_type.code}\n"
        f"Severity: {config.severity}\n"
        f"Status: {result.status}\n"
        f"Checked rows: {result.checked_rows}\n"
        f"Failed rows: {result.failed_rows}\n"
        f"Failed percent: {result.failed_percent}%\n"
        f"Run ID: {run.run_id}\n"
        f"Finished at: {run.finished_at}\n"
    )
    if result.sample_payload and result.sample_payload.get("rows"):
        body += f"\nSample rows: {result.sample_payload['rows']}\n"
    return subject, body


def execute_check_run(db: Session, config: models.CheckConfig, trigger_mode: str = "manual") -> schemas.RunResponse:
    run = models.CheckRun(
        check_config_id=config.check_config_id,
        status="running",
        trigger_mode=trigger_mode,
        started_at=datetime.utcnow(),
    )
    db.add(run)
    db.commit()
    db.refresh(run)

    try:
        executed_sql, checked_rows, failed_rows, failed_percent, samples = checks.execute_check(db, config)
        run.status = "completed"
        run.finished_at = datetime.utcnow()
        run.executed_sql = executed_sql
        config.last_run_at = run.finished_at

        result = models.CheckResult(
            run_id=run.run_id,
            checked_rows=checked_rows,
            failed_rows=failed_rows,
            failed_percent=failed_percent,
            status="failed" if failed_percent > float(config.threshold_percent) else "passed",
            sample_payload={"rows": samples},
        )
        db.add(result)
        db.commit()
        db.refresh(run)
        db.refresh(result)
        db.refresh(config)

        if should_send_notification(config, result):
            subject, body = build_notification(config, run, result)
            send_email_alert(config.notification_rule.email_to, subject, body)

        return schemas.RunResponse(
            run=schemas.CheckRunRead.model_validate(run),
            result=schemas.CheckResultRead.model_validate(result),
        )
    except Exception as exc:  # noqa: BLE001
        db.rollback()
        run.status = "error"
        run.finished_at = datetime.utcnow()
        run.error_message = str(exc)
        config.last_run_at = run.finished_at
        db.add(run)
        db.add(config)
        db.commit()
        db.refresh(run)
        return schemas.RunResponse(run=schemas.CheckRunRead.model_validate(run), result=None)
