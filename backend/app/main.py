from __future__ import annotations

from typing import Any

from fastapi import Depends, FastAPI, Header, HTTPException, Query
from fastapi.middleware.cors import CORSMiddleware
from sqlalchemy import desc, func, select, text
from sqlalchemy.orm import Session

from . import models, schemas
from .db import ensure_schedule_columns, get_db
from .runner import execute_check_run, get_check_config

app = FastAPI(title="DQ Monitoring Service API")

app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)


def get_role(x_user_role: str = Header(default="user")) -> str:
    role = x_user_role.lower().strip()
    if role not in {"admin", "user"}:
        raise HTTPException(status_code=400, detail="Unsupported role. Use admin or user")
    return role


def require_admin(role: str = Depends(get_role)) -> str:
    if role != "admin":
        raise HTTPException(status_code=403, detail="Admin role is required")
    return role


def _config_status_from_row(row) -> schemas.CheckConfigStatusRead:
    return schemas.CheckConfigStatusRead(
        check_config_id=row.check_config_id,
        dataset_id=row.dataset_id,
        attribute_id=row.attribute_id,
        check_type_id=row.check_type_id,
        notification_rule_id=row.notification_rule_id,
        check_name=row.check_name,
        severity=row.severity,
        threshold_percent=float(row.threshold_percent),
        filter_clause=row.filter_clause,
        params=row.params,
        is_enabled=row.is_enabled,
        created_at=row.created_at,
        schedule_type=row.schedule_type,
        schedule_interval_minutes=row.schedule_interval_minutes,
        schedule_time=row.schedule_time,
        schedule_day_of_week=row.schedule_day_of_week,
        schedule_day_of_month=row.schedule_day_of_month,
        schedule_timezone=row.schedule_timezone,
        last_run_at=row.last_run_at,
        dataset_name=row.dataset_name,
        schema_name=row.schema_name,
        table_name=row.table_name,
        attribute_name=row.attribute_name,
        check_type_code=row.check_type_code,
        check_type_name=row.check_type_name,
        dimension_name=row.dimension_name,
        level_scope=row.level_scope,
        last_run_id=row.last_run_id,
        last_finished_at=row.last_finished_at,
        last_result_status=row.last_result_status,
        last_failed_rows=row.last_failed_rows,
        last_failed_percent=float(row.last_failed_percent) if row.last_failed_percent is not None else None,
        last_executed_sql=getattr(row, "last_executed_sql", None),
    )


@app.on_event("startup")
def startup_migrations() -> None:
    ensure_schedule_columns()


@app.get("/health")
def healthcheck() -> dict[str, str]:
    return {"status": "ok"}


@app.get("/api/me")
def me(role: str = Depends(get_role)) -> dict[str, str]:
    return {"role": role}


@app.get("/api/datasources", response_model=list[schemas.DataSourceRead])
def list_datasources(db: Session = Depends(get_db)):
    return db.scalars(select(models.DataSource).order_by(models.DataSource.datasource_id)).all()


@app.get("/api/datasets", response_model=list[schemas.DatasetRead])
def list_datasets(db: Session = Depends(get_db)):
    return db.scalars(select(models.Dataset).order_by(models.Dataset.dataset_id)).all()


@app.get("/api/datasets/{dataset_id}/attributes", response_model=list[schemas.AttributeRead])
def list_attributes(dataset_id: int, db: Session = Depends(get_db)):
    return db.scalars(
        select(models.Attribute)
        .where(models.Attribute.dataset_id == dataset_id)
        .order_by(models.Attribute.attribute_id)
    ).all()


@app.get("/api/check-types", response_model=list[schemas.CheckTypeRead])
def list_check_types(db: Session = Depends(get_db)):
    return db.scalars(select(models.CheckType).order_by(models.CheckType.dimension_name, models.CheckType.name)).all()


@app.get("/api/notification-rules", response_model=list[schemas.NotificationRuleRead])
def list_notification_rules(db: Session = Depends(get_db)):
    return db.scalars(select(models.NotificationRule).order_by(models.NotificationRule.notification_rule_id)).all()


@app.post("/api/notification-rules", response_model=schemas.NotificationRuleRead, dependencies=[Depends(require_admin)])
def create_notification_rule(payload: schemas.NotificationRuleCreate, db: Session = Depends(get_db)):
    record = models.NotificationRule(**payload.model_dump())
    db.add(record)
    db.commit()
    db.refresh(record)
    return record


@app.get("/api/check-configs", response_model=list[schemas.CheckConfigStatusRead])
def list_check_configs(
    dataset_id: int | None = Query(default=None),
    include_disabled: bool = Query(default=True),
    db: Session = Depends(get_db),
):
    sql = """
        SELECT c.check_config_id,
               c.dataset_id,
               c.attribute_id,
               c.check_type_id,
               c.notification_rule_id,
               c.check_name,
               c.severity,
               c.threshold_percent,
               c.filter_clause,
               c.params,
               c.is_enabled,
               c.created_at,
               c.schedule_type,
               c.schedule_interval_minutes,
               c.schedule_time,
               c.schedule_day_of_week,
               c.schedule_day_of_month,
               c.schedule_timezone,
               c.last_run_at,
               d.display_name AS dataset_name,
               d.schema_name,
               d.table_name,
               a.column_name AS attribute_name,
               ct.code AS check_type_code,
               ct.name AS check_type_name,
               ct.dimension_name,
               ct.level_scope,
               latest.run_id AS last_run_id,
               latest.finished_at AS last_finished_at,
               COALESCE(latest.result_status, 'not_run') AS last_result_status,
               latest.failed_rows AS last_failed_rows,
               latest.failed_percent AS last_failed_percent,
               latest.executed_sql AS last_executed_sql
        FROM dq_check_config c
        JOIN dq_dataset d ON d.dataset_id = c.dataset_id
        LEFT JOIN dq_attribute a ON a.attribute_id = c.attribute_id
        JOIN dq_check_type ct ON ct.check_type_id = c.check_type_id
        LEFT JOIN LATERAL (
            SELECT run.run_id,
                   run.finished_at,
                   run.executed_sql,
                   res.status AS result_status,
                   res.failed_rows,
                   res.failed_percent
            FROM dq_check_run run
            LEFT JOIN dq_check_result res ON res.run_id = run.run_id
            WHERE run.check_config_id = c.check_config_id
            ORDER BY run.run_id DESC
            LIMIT 1
        ) latest ON TRUE
        WHERE 1 = 1
    """
    params: dict[str, Any] = {}
    if dataset_id is not None:
        sql += " AND c.dataset_id = :dataset_id"
        params["dataset_id"] = dataset_id
    if not include_disabled:
        sql += " AND c.is_enabled IS TRUE"
    sql += " ORDER BY c.check_config_id DESC"

    rows = db.execute(text(sql), params).all()
    return [_config_status_from_row(row) for row in rows]


@app.get("/api/datasets/{dataset_id}/check-summary", response_model=schemas.TableCheckSummary)
def dataset_check_summary(dataset_id: int, db: Session = Depends(get_db)):
    rows = db.execute(text("""
        SELECT COALESCE(latest.status, 'not_run') AS status, COUNT(*) AS cnt
        FROM dq_check_config c
        LEFT JOIN LATERAL (
            SELECT res.status
            FROM dq_check_run run
            LEFT JOIN dq_check_result res ON res.run_id = run.run_id
            WHERE run.check_config_id = c.check_config_id
            ORDER BY run.run_id DESC
            LIMIT 1
        ) latest ON TRUE
        WHERE c.dataset_id = :dataset_id
        GROUP BY 1
    """), {"dataset_id": dataset_id}).all()
    counts = {row.status: int(row.cnt) for row in rows}
    active_checks = db.scalar(
        select(func.count()).select_from(models.CheckConfig)
        .where(models.CheckConfig.dataset_id == dataset_id, models.CheckConfig.is_enabled.is_(True))
    ) or 0
    return schemas.TableCheckSummary(
        dataset_id=dataset_id,
        total_checks=sum(counts.values()),
        active_checks=int(active_checks),
        failed_checks=counts.get("failed", 0),
        passed_checks=counts.get("passed", 0),
        not_run_checks=counts.get("not_run", 0),
    )




def normalize_schedule(payload: schemas.CheckConfigCreate) -> dict[str, Any]:
    data = payload.model_dump()
    schedule_type = (data.get("schedule_type") or "manual").lower().strip()
    allowed = {"manual", "interval", "daily", "weekly", "monthly"}
    if schedule_type not in allowed:
        raise HTTPException(status_code=400, detail="Unsupported schedule_type")

    data["schedule_type"] = schedule_type

    if schedule_type == "manual":
        data["schedule_interval_minutes"] = None
        data["schedule_time"] = None
        data["schedule_day_of_week"] = None
        data["schedule_day_of_month"] = None
        return data

    if schedule_type == "interval":
        interval = data.get("schedule_interval_minutes")
        if interval is None or interval <= 0:
            raise HTTPException(status_code=400, detail="schedule_interval_minutes must be positive for interval schedule")
        data["schedule_time"] = None
        data["schedule_day_of_week"] = None
        data["schedule_day_of_month"] = None
        return data

    if data.get("schedule_time") is None:
        raise HTTPException(status_code=400, detail="schedule_time is required for daily, weekly and monthly schedules")

    data["schedule_interval_minutes"] = None

    if schedule_type == "daily":
        data["schedule_day_of_week"] = None
        data["schedule_day_of_month"] = None
        return data

    if schedule_type == "weekly":
        day = data.get("schedule_day_of_week")
        if day is None or day < 1 or day > 7:
            raise HTTPException(status_code=400, detail="schedule_day_of_week must be from 1 to 7 for weekly schedule")
        data["schedule_day_of_month"] = None
        return data

    if schedule_type == "monthly":
        day = data.get("schedule_day_of_month")
        if day is None or day < 1 or day > 31:
            raise HTTPException(status_code=400, detail="schedule_day_of_month must be from 1 to 31 for monthly schedule")
        data["schedule_day_of_week"] = None
        return data

    return data


@app.post("/api/check-configs", response_model=schemas.CheckConfigRead, dependencies=[Depends(require_admin)])
def create_check_config(payload: schemas.CheckConfigCreate, db: Session = Depends(get_db)):
    dataset = db.get(models.Dataset, payload.dataset_id)
    check_type = db.get(models.CheckType, payload.check_type_id)
    if not dataset or not check_type:
        raise HTTPException(status_code=404, detail="Dataset or check type not found")
    if check_type.level_scope == "column" and not payload.attribute_id:
        raise HTTPException(status_code=400, detail="attribute_id is required for column-level checks")
    if check_type.level_scope == "table" and payload.attribute_id:
        raise HTTPException(status_code=400, detail="attribute_id should be empty for table-level checks")
    record = models.CheckConfig(**normalize_schedule(payload))
    db.add(record)
    db.commit()
    db.refresh(record)
    return record


@app.patch("/api/check-configs/{check_config_id}/enabled", response_model=schemas.CheckConfigRead, dependencies=[Depends(require_admin)])
def set_check_enabled(check_config_id: int, payload: schemas.CheckConfigEnabledUpdate, db: Session = Depends(get_db)):
    config = db.get(models.CheckConfig, check_config_id)
    if not config:
        raise HTTPException(status_code=404, detail="Check config not found")
    config.is_enabled = payload.is_enabled
    db.add(config)
    db.commit()
    db.refresh(config)
    return config


@app.post("/api/check-configs/{check_config_id}/run", response_model=schemas.RunResponse, dependencies=[Depends(require_admin)])
def run_check(check_config_id: int, db: Session = Depends(get_db)):
    config = get_check_config(db, check_config_id)
    if not config:
        raise HTTPException(status_code=404, detail="Check config not found")
    if not config.is_enabled:
        raise HTTPException(status_code=400, detail="Disabled check cannot be launched")
    return execute_check_run(db, config, trigger_mode="manual")


@app.get("/api/runs", response_model=list[schemas.CheckRunRead])
def list_runs(dataset_id: int | None = Query(default=None), db: Session = Depends(get_db)):
    stmt = select(models.CheckRun).join(models.CheckConfig).order_by(desc(models.CheckRun.run_id)).limit(100)
    if dataset_id is not None:
        stmt = stmt.where(models.CheckConfig.dataset_id == dataset_id)
    return db.scalars(stmt).all()


@app.get("/api/results/{run_id}", response_model=schemas.CheckResultRead)
def get_result(run_id: int, db: Session = Depends(get_db)):
    result = db.scalar(select(models.CheckResult).where(models.CheckResult.run_id == run_id))
    if not result:
        raise HTTPException(status_code=404, detail="Result not found")
    run = db.get(models.CheckRun, run_id)
    return {
        "result_id": result.result_id,
        "run_id": result.run_id,
        "checked_rows": result.checked_rows,
        "failed_rows": result.failed_rows,
        "failed_percent": float(result.failed_percent),
        "status": result.status,
        "sample_payload": result.sample_payload,
        "created_at": result.created_at,
        "executed_sql": run.executed_sql if run else None,
    }


@app.get("/api/dashboard", response_model=schemas.DashboardResponseV2)
def dashboard(db: Session = Depends(get_db)):
    active_checks = db.scalar(select(func.count()).select_from(models.CheckConfig).where(models.CheckConfig.is_enabled.is_(True))) or 0
    failed_last_run = db.scalar(select(func.count()).select_from(models.CheckResult).where(models.CheckResult.status == "failed")) or 0
    critical_checks = db.scalar(select(func.count()).select_from(models.CheckConfig).where(models.CheckConfig.severity == "critical")) or 0
    total_runs = db.scalar(select(func.count()).select_from(models.CheckRun)) or 0

    latest = db.execute(
        select(
            models.CheckRun.run_id,
            models.CheckConfig.check_name,
            models.CheckResult.failed_percent,
            models.CheckResult.status,
            models.CheckRun.finished_at,
        )
        .join(models.CheckConfig, models.CheckConfig.check_config_id == models.CheckRun.check_config_id)
        .join(models.CheckResult, models.CheckResult.run_id == models.CheckRun.run_id)
        .order_by(desc(models.CheckRun.run_id))
        .limit(20)
    ).all()

    latest_runs = [
        schemas.DashboardSeriesPoint(
            run_id=row.run_id,
            check_name=row.check_name,
            failed_percent=float(row.failed_percent),
            status=row.status,
            finished_at=row.finished_at,
        )
        for row in latest
    ]

    trend_rows = db.execute(text("""
        SELECT to_char(date_trunc('day', r.created_at), 'YYYY-MM-DD') AS day,
               SUM(CASE WHEN r.status = 'passed' THEN 1 ELSE 0 END) AS passed,
               SUM(CASE WHEN r.status = 'failed' THEN 1 ELSE 0 END) AS failed
        FROM dq_check_result r
        WHERE r.created_at >= NOW() - INTERVAL '14 day'
        GROUP BY 1
        ORDER BY 1
    """)).all()
    trend = [schemas.DashboardTrendPoint(day=row.day, passed=int(row.passed), failed=int(row.failed)) for row in trend_rows]

    health_rows = db.execute(text("""
        SELECT c.check_name,
               c.severity,
               c.last_run_at,
               COALESCE(res.status, 'not_run') AS latest_status,
               COALESCE(res.failed_percent, 0) AS latest_failed_percent
        FROM dq_check_config c
        LEFT JOIN LATERAL (
            SELECT r2.status, r2.failed_percent
            FROM dq_check_run run2
            JOIN dq_check_result r2 ON r2.run_id = run2.run_id
            WHERE run2.check_config_id = c.check_config_id
            ORDER BY run2.run_id DESC
            LIMIT 1
        ) res ON TRUE
        ORDER BY c.check_config_id DESC
        LIMIT 20
    """)).all()
    check_health = [
        schemas.DashboardCheckHealth(
            check_name=row.check_name,
            latest_status=row.latest_status,
            latest_failed_percent=float(row.latest_failed_percent),
            severity=row.severity,
            last_run_at=row.last_run_at,
        )
        for row in health_rows
    ]

    return schemas.DashboardResponseV2(
        summary=schemas.DashboardSummary(
            active_checks=int(active_checks),
            failed_last_run=int(failed_last_run),
            critical_checks=int(critical_checks),
            total_runs=int(total_runs),
        ),
        latest_runs=latest_runs,
        trend=trend,
        check_health=check_health,
    )
