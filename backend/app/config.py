from pydantic_settings import BaseSettings


class Settings(BaseSettings):
    database_url: str = "postgresql+asyncpg://neo:neo_password@localhost:5432/neo_hotel"
    jwt_secret: str = "change-me-to-a-random-secret-key"
    jwt_access_token_expire_minutes: int = 30
    jwt_refresh_token_expire_days: int = 7
    jwt_algorithm: str = "HS256"
    wifi_password: str = "NeoHotel2026"
    breakfast_info: str = "早餐時間 07:00-10:00，地點：1F 餐廳"

    model_config = {"env_file": ".env", "extra": "ignore"}


settings = Settings()
