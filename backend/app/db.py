from sqlalchemy import create_engine, text
from sqlalchemy.orm import sessionmaker

from .config import settings

engine = create_engine(settings.database_url, future=True)
SessionLocal = sessionmaker(bind=engine, autoflush=False, autocommit=False, future=True)


def ensure_schedule_columns() -> None:
    """Adds schedule columns for existing local databases without data loss.

    init.sql creates these columns for a clean database. This helper is needed when
    a developer updates the project but keeps an old Docker volume.
    """
    statements = [
        "ALTER TABLE dq_check_config ADD COLUMN IF NOT EXISTS schedule_type VARCHAR(30) NOT NULL DEFAULT 'manual'",
        "ALTER TABLE dq_check_config ADD COLUMN IF NOT EXISTS schedule_time TIME",
        "ALTER TABLE dq_check_config ADD COLUMN IF NOT EXISTS schedule_day_of_week INTEGER",
        "ALTER TABLE dq_check_config ADD COLUMN IF NOT EXISTS schedule_day_of_month INTEGER",
        "ALTER TABLE dq_check_config ADD COLUMN IF NOT EXISTS schedule_timezone VARCHAR(50) NOT NULL DEFAULT 'Europe/Moscow'",
        "UPDATE dq_check_config SET schedule_type = CASE WHEN schedule_interval_minutes IS NULL THEN 'manual' ELSE 'interval' END WHERE schedule_type IS NULL OR schedule_type = 'manual' AND schedule_interval_minutes IS NOT NULL",
    ]
    with engine.begin() as conn:
        for statement in statements:
            conn.execute(text(statement))


def get_db():
    db = SessionLocal()
    try:
        yield db
    finally:
        db.close()
