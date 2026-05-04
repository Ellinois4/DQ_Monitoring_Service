from pydantic_settings import BaseSettings, SettingsConfigDict


class Settings(BaseSettings):
    app_name: str = "DQ Monitoring Service"
    database_url: str = "postgresql+psycopg://dq_user:dq_password@postgres:5432/dq_service"
    smtp_host: str = "mailhog"
    smtp_port: int = 1025
    smtp_from: str = "dq-monitor@example.local"
    alert_base_url: str = "http://localhost:3000"

    model_config = SettingsConfigDict(env_file=".env", case_sensitive=False)


settings = Settings()
