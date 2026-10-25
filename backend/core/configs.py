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
    SMTP_START_TLS: bool = True
    FRONTEND_URL: str
    BACKEND_URL: str
    SMTP_FROM_NAME:str
    # Brevo's transactional email API. When BREVO_ENABLED is true, mail goes
    # through the HTTP API instead of SMTP. SMTP_FROM_NAME/SMTP_FROM_EMAIL are
    # still used as the sender, so they must be verified in Brevo.
    BREVO_ENABLED: bool = False
    BREVO_API_URL: str = "https://api.brevo.com/v3"
    BREVO_API_KEY: str | None = None
    BREVO_TIMEOUT_SECONDS: float = 30.0
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
    # The network the treasury's USDC is withdrawn on.
    OBiex_WITHDRAWAL_NETWORK: str = "SOL"

    # Solana settlement layer (Model 1).
    REACH_SOLANA_RPC_URL: str = ""
    REACH_PROGRAM_ID: str = "5iCtrxFDsPQf6qyR2nfjkDgUJyuH7oxoA5Lf1qQiDfwY"
    REACH_STABLE_MINT: str = "EPjFWdd5AufqSSqeM2qN1xzybapC8G4wEGGkZwyTDt1v"
    REACH_RELAYER_SECRET_KEY: str | None = None
    REACH_RELAYER_CONFIRM_TIMEOUT: float = 60.0
    REACH_MIN_ESCROW_UNITS: int = 1000000
    REACH_CREATION_FEE_BPS: int = 250
    # The `expires_at` the backend writes into a provider's application.
    REACH_APPLICATION_TTL_SECONDS: int = 604800
    # The USDC float the treasury keeps on Solana, in base units (6 decimals).
    REACH_TREASURY_TARGET_UNITS: int = 500000000
    # Obiex's minimum withdrawal, in base units.
    REACH_TREASURY_MIN_WITHDRAWAL_UNITS: int = 10000000

    # Provider naira off-ramp. Live money movement is off until the Obiex
    # business account has confirmed third-party bank payouts and USDC/SOL
    # deposits.
    REACH_OFFRAMP_ENABLED: bool = False
    REACH_OFFRAMP_SOURCE_CURRENCY: str = "USDC"
    REACH_OFFRAMP_TARGET_CURRENCY: str = "NGNX"
    REACH_OFFRAMP_NETWORK: str = "SOL"
    REACH_OFFRAMP_FALLBACK_CURRENCY: str = "USDT"
    REACH_OFFRAMP_MIN_USDC_UNITS: int = 5000000
    REACH_OFFRAMP_MAX_USDC_UNITS: int = 1000000000
    REACH_OFFRAMP_MIN_NGN_KOBO: int = 500000
    # The deposit address is ours, not Obiex's one-time collection account;
    # this is the window in which we ask the provider to fund it.
    REACH_OFFRAMP_DEPOSIT_TTL_SECONDS: int = 1800
    REACH_OFFRAMP_QUOTE_TTL_SECONDS: int = 300
    # If the executed swap is more than this far below the quote, hold the
    # payout instead of silently paying a worse naira amount.
    REACH_OFFRAMP_SLIPPAGE_BPS: int = 200
    # Obiex's fiat withdrawal fee is returned on the withdrawal. This is only
    # a quote-time estimate until the account confirms the live fee.
    REACH_OFFRAMP_FIAT_FEE_KOBO: int = 5000
    REACH_OFFRAMP_REQUIRE_NAME_MATCH: bool = True

    PLATFORM_FEE_BPS: int = 500
    MIN_ESCROW_KOBO: int = 100000

    model_config = SettingsConfigDict(
        env_file=".env",
        extra="ignore"
    )

settings = Settings()
