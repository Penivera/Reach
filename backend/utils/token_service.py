import secrets

async def generate_token() -> str:
    return secrets.token_urlsafe(32)