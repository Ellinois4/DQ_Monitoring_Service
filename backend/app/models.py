from datetime import datetime
from typing import Optional

from sqlalchemy import Boolean, DateTime, ForeignKey, Integer, Numeric, String, Text, JSON
from sqlalchemy.orm import DeclarativeBase, Mapped, mapped_column, relationship


class Base(DeclarativeBase):
    pass


class DataSource(Base):
    __tablename__ = "dq_datasource"

    datasource_id: Mapped[int] = mapped_column(Integer, primary_key=True)
    name: Mapped[str] = mapped_column(String(100), nullable=False, unique=True)
    db_type: Mapped[str] = mapped_column(String(50), nullable=False, default="postgresql")
    description: Mapped[Optional[str]] = mapped_column(Text)
    is_active: Mapped[bool] = mapped_column(Boolean, default=True)

    datasets: Mapped[list["Dataset"]] = relationship(back_populates="datasource")


class Dataset(Base):
    __tablename__ = "dq_dataset"

    dataset_id: Mapped[int] = mapped_column(Integer, primary_key=True)
    datasource_id: Mapped[int] = mapped_column(ForeignKey("dq_datasource.datasource_id"), nullable=False)
    schema_name: Mapped[str] = mapped_column(String(100), nullable=False)
    table_name: Mapped[str] = mapped_column(String(100), nullable=False)
    display_name: Mapped[str] = mapped_column(String(150), nullable=False)
    owner_name: Mapped[Optional[str]] = mapped_column(String(150))
    criticality: Mapped[str] = mapped_column(String(20), default="medium")
    freshness_column: Mapped[Optional[str]] = mapped_column(String(100))
    created_at: Mapped[datetime] = mapped_column(DateTime, default=datetime.utcnow)

    datasource: Mapped[DataSource] = relationship(back_populates="datasets")
    attributes: Mapped[list["Attribute"]] = relationship(back_populates="dataset")
    check_configs: Mapped[list["CheckConfig"]] = relationship(back_populates="dataset")


class Attribute(Base):
    __tablename__ = "dq_attribute"

    attribute_id: Mapped[int] = mapped_column(Integer, primary_key=True)
    dataset_id: Mapped[int] = mapped_column(ForeignKey("dq_dataset.dataset_id"), nullable=False)
    column_name: Mapped[str] = mapped_column(String(100), nullable=False)
    data_type: Mapped[str] = mapped_column(String(100), nullable=False)
    is_nullable: Mapped[bool] = mapped_column(Boolean, default=True)

    dataset: Mapped[Dataset] = relationship(back_populates="attributes")


class CheckType(Base):
    __tablename__ = "dq_check_type"

    check_type_id: Mapped[int] = mapped_column(Integer, primary_key=True)
    code: Mapped[str] = mapped_column(String(100), unique=True, nullable=False)
    name: Mapped[str] = mapped_column(String(150), nullable=False)
    dimension_name: Mapped[str] = mapped_column(String(100), nullable=False)
    level_scope: Mapped[str] = mapped_column(String(20), nullable=False)
    description: Mapped[Optional[str]] = mapped_column(Text)
    param_schema: Mapped[Optional[dict]] = mapped_column(JSON)

    check_configs: Mapped[list["CheckConfig"]] = relationship(back_populates="check_type")


class NotificationRule(Base):
    __tablename__ = "dq_notification_rule"

    notification_rule_id: Mapped[int] = mapped_column(Integer, primary_key=True)
    email_to: Mapped[str] = mapped_column(String(255), nullable=False)
    phone_number: Mapped[Optional[str]] = mapped_column(String(50))
    notify_on_status: Mapped[str] = mapped_column(String(20), default="failed")
    critical_only: Mapped[bool] = mapped_column(Boolean, default=False)

    check_configs: Mapped[list["CheckConfig"]] = relationship(back_populates="notification_rule")


class CheckConfig(Base):
    __tablename__ = "dq_check_config"

    check_config_id: Mapped[int] = mapped_column(Integer, primary_key=True)
    dataset_id: Mapped[int] = mapped_column(ForeignKey("dq_dataset.dataset_id"), nullable=False)
    attribute_id: Mapped[Optional[int]] = mapped_column(ForeignKey("dq_attribute.attribute_id"))
    check_type_id: Mapped[int] = mapped_column(ForeignKey("dq_check_type.check_type_id"), nullable=False)
    notification_rule_id: Mapped[Optional[int]] = mapped_column(ForeignKey("dq_notification_rule.notification_rule_id"))
    check_name: Mapped[str] = mapped_column(String(150), nullable=False)
    severity: Mapped[str] = mapped_column(String(20), default="warning")
    threshold_percent: Mapped[float] = mapped_column(Numeric(10, 4), default=0)
    filter_clause: Mapped[Optional[dict]] = mapped_column(JSON)
    params: Mapped[Optional[dict]] = mapped_column(JSON)
    is_enabled: Mapped[bool] = mapped_column(Boolean, default=True)
    created_at: Mapped[datetime] = mapped_column(DateTime, default=datetime.utcnow)
    schedule_interval_minutes: Mapped[Optional[int]] = mapped_column(Integer)
    last_run_at: Mapped[Optional[datetime]] = mapped_column(DateTime)

    dataset: Mapped[Dataset] = relationship(back_populates="check_configs")
    attribute: Mapped[Optional[Attribute]] = relationship()
    check_type: Mapped[CheckType] = relationship(back_populates="check_configs")
    notification_rule: Mapped[Optional[NotificationRule]] = relationship(back_populates="check_configs")
    runs: Mapped[list["CheckRun"]] = relationship(back_populates="check_config")


class CheckRun(Base):
    __tablename__ = "dq_check_run"

    run_id: Mapped[int] = mapped_column(Integer, primary_key=True)
    check_config_id: Mapped[int] = mapped_column(ForeignKey("dq_check_config.check_config_id"), nullable=False)
    started_at: Mapped[datetime] = mapped_column(DateTime, default=datetime.utcnow)
    finished_at: Mapped[Optional[datetime]] = mapped_column(DateTime)
    status: Mapped[str] = mapped_column(String(20), nullable=False, default="running")
    executed_sql: Mapped[Optional[str]] = mapped_column(Text)
    error_message: Mapped[Optional[str]] = mapped_column(Text)
    trigger_mode: Mapped[str] = mapped_column(String(20), nullable=False, default="manual")

    check_config: Mapped[CheckConfig] = relationship(back_populates="runs")
    result: Mapped[Optional["CheckResult"]] = relationship(back_populates="run", uselist=False)


class CheckResult(Base):
    __tablename__ = "dq_check_result"

    result_id: Mapped[int] = mapped_column(Integer, primary_key=True)
    run_id: Mapped[int] = mapped_column(ForeignKey("dq_check_run.run_id"), nullable=False, unique=True)
    checked_rows: Mapped[int] = mapped_column(Integer, nullable=False)
    failed_rows: Mapped[int] = mapped_column(Integer, nullable=False)
    failed_percent: Mapped[float] = mapped_column(Numeric(10, 4), nullable=False)
    status: Mapped[str] = mapped_column(String(20), nullable=False)
    sample_payload: Mapped[Optional[dict]] = mapped_column(JSON)
    created_at: Mapped[datetime] = mapped_column(DateTime, default=datetime.utcnow)

    run: Mapped[CheckRun] = relationship(back_populates="result")
