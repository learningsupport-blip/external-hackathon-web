from functools import lru_cache

from pydantic_settings import BaseSettings, SettingsConfigDict


class Settings(BaseSettings):
    model_config = SettingsConfigDict(env_file=(".env", "../../.env"), extra="ignore")

    app_env: str = "development"
    database_url: str = "postgresql+pg8000://hackhub:hackhub@localhost:5432/hackhub"
    session_secret: str = "dev-only-change-me"
    session_cookie_name: str = "hackhub_session"
    session_ttl_days: int = 14
    web_origin: str = "http://localhost:3000"
    google_client_id: str = ""
    google_client_secret: str = ""
    google_redirect_uri: str = "http://localhost:3000/api/v1/auth/google/callback"
    google_sheet_id: str = ""
    google_sheets_credentials: str = ""
    admin_emails: str = ""
    allowed_email_domains: str = ""
    default_timezone: str = "Asia/Kolkata"
    job_tick_secret: str = ""
    resend_api_key: str = ""
    resend_from: str = "HackHub <onboarding@resend.dev>"
    gemini_api_key: str = ""
    gemini_model: str = "gemini-3.5-flash-lite"

    @property
    def is_production(self) -> bool:
        return self.app_env == "production"

    @property
    def admin_email_set(self) -> set[str]:
        return {item.strip().lower() for item in self.admin_emails.split(",") if item.strip()}

    @property
    def allowed_domain_set(self) -> set[str]:
        return {item.strip().lower() for item in self.allowed_email_domains.split(",") if item.strip()}


@lru_cache
def get_settings() -> Settings:
    return Settings()
