from pydantic_settings import BaseSettings, SettingsConfigDict

class Settings(BaseSettings):
    SECRET_KEY: str
    ALGORITHM: str
    DATABASE_URL: str
    SMTP_PORT:int
    SMTP_USERNAME:str
    SMTP_PASSWORD:str
    SMTP_FROM_EMAIL:str
    ACCESS_TOKEN_EXPIRE_MINUTES: int
    SMTP_HOST:str
    BACKEND_URL: str
    SMTP_FROM_NAME:str
    CLOUDINARY_CLOUD_NAME:str
    CLOUDINARY_API_KEY:str
    CLOUDINARY_API_SECRET:str

    FOSSAPAY_API_URL: str = "https://api-production.fossapay.com/api/v1"
    FOSSAPAY_API_KEY: str | None = None
    FOSSAPAY_WEBHOOK_SECRET: str | None = None
    FOSSAPAY_ENABLED: bool = False
    FOSSAPAY_TIMEOUT_SECONDS: float = 30.0
    PAYMENT_PROVIDER: str = "fossapay"

    PLATFORM_FEE_BPS: int = 500
    MIN_ESCROW_KOBO: int = 100000

    model_config = SettingsConfigDict(
        env_file=".env",
        extra="ignore"
    )

settings = Settings()