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

    # Obiex: fiat collection, NGN <-> USDC conversion, crypto withdrawals.
    OBiex_ENABLED: bool = False
    OBiex_API_URL: str = "https://api.obiex.finance/v1"
    OBiex_API_KEY: str | None = None
    OBiex_API_SECRET: str | None = None
    OBiex_WEBHOOK_SECRET: str | None = None
    OBiex_TIMEOUT_SECONDS: float = 30.0
    OBiex_COLLECTION_CURRENCY: str = "USDC"

    # Solana settlement layer (Model 1).
    REACH_SOLANA_RPC_URL: str = ""
    REACH_PROGRAM_ID: str = "5iCtrxFDsPQf6qyR2nfjkDgUJyuH7oxoA5Lf1qQiDfwY"
    REACH_STABLE_MINT: str = "EPjFWdd5AufqSSqeM2qN1xzybapC8G4wEGGkZwyTDt1v"
    REACH_RELAYER_SECRET_KEY: str | None = None
    REACH_RELAYER_CONFIRM_TIMEOUT: float = 60.0
    REACH_MIN_ESCROW_UNITS: int = 1000000
    REACH_CREATION_FEE_BPS: int = 250

    PLATFORM_FEE_BPS: int = 500
    MIN_ESCROW_KOBO: int = 100000

    model_config = SettingsConfigDict(
        env_file=".env",
        extra="ignore"
    )

settings = Settings()