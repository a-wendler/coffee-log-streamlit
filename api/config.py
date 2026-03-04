"""API configuration from environment variables."""

from pydantic_settings import BaseSettings, SettingsConfigDict


class Settings(BaseSettings):
    """Application settings loaded from environment."""

    model_config = SettingsConfigDict(
        env_file=".env",
        env_file_encoding="utf-8",
        case_sensitive=False,
    )

    # Database
    database_url: str = "mysql+pymysql://user:pass@localhost:3306/coffee"

    # JWT
    jwt_secret: str = "change-me-in-production"
    jwt_algorithm: str = "HS256"
    jwt_expire_minutes: int = 60 * 24  # 24 hours

    # Coffee prices (Decimal as string for env)
    kaffee_preis_mitglied: str = "0.25"
    kaffee_preis_gast: str = "1.0"

    # SMTP
    smtp_port: int = 587
    smtp_server: str = ""
    smtp_login: str = ""
    smtp_password: str = ""
    smtp_sender: str = ""
    smtp_reply: str = ""
    streamlit_app_url: str = "https://lsbkaffee.streamlit.app"
    admin_rechnung: str = ""
    admin_technik: str = ""
    zahlungsoptionen: str = ""

    def get_database_url(self) -> str:
        """Return database URL for SQLAlchemy."""
        return self.database_url


settings = Settings()
