from pydantic_settings import BaseSettings, SettingsConfigDict


class Settings(BaseSettings):
    model_config = SettingsConfigDict(env_file=".env", extra="ignore")

    database_url: str = "postgresql+psycopg://postgres:postgres@postgres:5432/retirement-planner"
    jwt_secret: str = "change-me-in-.env"
    jwt_algorithm: str = "HS256"
    access_token_expire_minutes: int = 60 * 24 * 7  # 1 week

    # Comma-separated list of allowed browser origins. The production origin is the
    # Cloudflare Tunnel hostname; the localhost entries are for `npm run dev` (Vite
    # on 5173) talking to a locally-run backend, since that's cross-origin.
    cors_origins: str = "https://retirement.damsm.com,http://localhost:5173,http://localhost:6005"

    @property
    def cors_origins_list(self) -> list[str]:
        return [origin.strip() for origin in self.cors_origins.split(",") if origin.strip()]


settings = Settings()
