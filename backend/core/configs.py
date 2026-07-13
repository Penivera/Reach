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

    model_config = SettingsConfigDict(
        env_file=".env",
        extra="ignore"
    )

settings = Settings()