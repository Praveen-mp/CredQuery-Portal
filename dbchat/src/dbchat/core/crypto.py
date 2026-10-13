from functools import lru_cache

from cryptography.fernet import Fernet

from dbchat.core.config import get_app_settings


@lru_cache
def _fernet() -> Fernet:
    settings = get_app_settings()
    return Fernet(settings.app_secret_key.encode())


def encrypt(value: str) -> str:
    """Encrypts a secret (DB password, LLM API key) before it's written to
    the metadata store. Never store these fields in plaintext."""
    return _fernet().encrypt(value.encode()).decode()


def decrypt(token: str) -> str:
    return _fernet().decrypt(token.encode()).decode()
