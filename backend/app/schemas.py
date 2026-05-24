from datetime import datetime, time
from typing import Any, Optional

from pydantic import BaseModel, ConfigDict, Field


class DataSourceRead(BaseModel):
    model_config = ConfigDict(from_attributes=True)
    datasource_id: int
    name: str
    db_type: str
    description: Optional[str] = None
    is_active: bool


class DatasetRead(BaseModel):
    model_config = ConfigDict(from_attributes=True)
    dataset_id: int
    datasource_id: int
    schema_name: str
    table_name: str
    display_name: str
    owner_name: Optional[str] = None
    criticality: str
    freshness_column: Optional[str] = None


class AttributeRead(BaseModel):
    model_config = ConfigDict(from_attributes=True)
    attribute_id: int
    dataset_id: int
    column_name: str
    data_type: str
    is_nullable: bool


class CheckTypeRead(BaseModel):
    model_config = ConfigDict(from_attributes=True)
    check_type_id: int
    code: str
    name: str
    dimension_name: str
    level_scope: str
    description: Optional[str] = None
    param_schema: Optional[dict[str, Any]] = None


class NotificationRuleCreate(BaseModel):
    # В demo-режиме MailHog часто использует локальные адреса вида owner@example.local.
    # Поэтому здесь intentionally используется str, а не EmailStr, чтобы не падать
    # на специальных локальных доменах.
    email_to: str
    phone_number: Optional[str] = None
    notify_on_status: str = Field(default="failed")
    critical_only: bool = False


class NotificationRuleRead(NotificationRuleCreate):
    model_config = ConfigDict(from_attributes=True)
    notification_rule_id: int


class CheckConfigCreate(BaseModel):
    dataset_id: int
    attribute_id: Optional[int] = None
    check_type_id: int
    notification_rule_id: Optional[int] = None
    check_name: str
    severity: str = Field(default="warning")
    threshold_percent: float = 0
    filter_clause: Optional[dict[str, Any]] = None
    params: Optional[dict[str, Any]] = None
    is_enabled: bool = True
    schedule_type: str = "manual"
    schedule_interval_minutes: Optional[int] = None
    schedule_time: Optional[time] = None
    schedule_day_of_week: Optional[int] = None
    schedule_day_of_month: Optional[int] = None
    schedule_timezone: str = "Europe/Moscow"


class CheckConfigRead(CheckConfigCreate):
    model_config = ConfigDict(from_attributes=True)
    check_config_id: int
    created_at: datetime
    schedule_type: str = "manual"
    schedule_interval_minutes: Optional[int] = None
    schedule_time: Optional[time] = None
    schedule_day_of_week: Optional[int] = None
    schedule_day_of_month: Optional[int] = None
    schedule_timezone: str = "Europe/Moscow"
    last_run_at: Optional[datetime] = None


class CheckRunRead(BaseModel):
    model_config = ConfigDict(from_attributes=True)
    run_id: int
    check_config_id: int
    started_at: datetime
    finished_at: Optional[datetime] = None
    status: str
    executed_sql: Optional[str] = None
    error_message: Optional[str] = None
    trigger_mode: str


class CheckResultRead(BaseModel):
    model_config = ConfigDict(from_attributes=True)
    result_id: int
    run_id: int
    checked_rows: int
    failed_rows: int
    failed_percent: float
    status: str
    sample_payload: Optional[Any] = None
    created_at: datetime
    executed_sql: Optional[str] = None
    schedule_interval_minutes: Optional[int] = None
    last_run_at: Optional[datetime] = None


class CheckConfigStatusRead(BaseModel):
    check_config_id: int
    dataset_id: int
    attribute_id: Optional[int] = None
    check_type_id: int
    notification_rule_id: Optional[int] = None
    check_name: str
    severity: str
    threshold_percent: float
    filter_clause: Optional[dict[str, Any]] = None
    params: Optional[dict[str, Any]] = None
    is_enabled: bool
    created_at: datetime
    schedule_type: str = "manual"
    schedule_interval_minutes: Optional[int] = None
    schedule_time: Optional[time] = None
    schedule_day_of_week: Optional[int] = None
    schedule_day_of_month: Optional[int] = None
    schedule_timezone: str = "Europe/Moscow"
    last_run_at: Optional[datetime] = None
    dataset_name: str
    schema_name: str
    table_name: str
    attribute_name: Optional[str] = None
    check_type_code: str
    check_type_name: str
    dimension_name: str
    level_scope: str
    last_run_id: Optional[int] = None
    last_finished_at: Optional[datetime] = None
    last_result_status: str = "not_run"
    last_failed_rows: Optional[int] = None
    last_failed_percent: Optional[float] = None
    last_executed_sql: Optional[str] = None


class CheckConfigEnabledUpdate(BaseModel):
    is_enabled: bool


class TableCheckSummary(BaseModel):
    dataset_id: int
    total_checks: int
    active_checks: int
    failed_checks: int
    passed_checks: int
    not_run_checks: int


class RunResponse(BaseModel):
    run: CheckRunRead
    result: Optional[CheckResultRead] = None


class DashboardSummary(BaseModel):
    active_checks: int
    failed_last_run: int
    critical_checks: int
    total_runs: int


class DashboardSeriesPoint(BaseModel):
    run_id: int
    check_name: str
    failed_percent: float
    status: str
    finished_at: Optional[datetime] = None


class DashboardResponse(BaseModel):
    summary: DashboardSummary
    latest_runs: list[DashboardSeriesPoint]


class DashboardTrendPoint(BaseModel):
    day: str
    passed: int
    failed: int


class DashboardCheckHealth(BaseModel):
    check_name: str
    latest_status: str
    latest_failed_percent: float
    severity: str
    last_run_at: Optional[datetime] = None


class DashboardResponseV2(DashboardResponse):
    trend: list[DashboardTrendPoint]
    check_health: list[DashboardCheckHealth]
