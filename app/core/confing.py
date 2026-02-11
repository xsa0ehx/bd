import os
from dataclasses import dataclass
from functools import lru_cache
from typing import Tuple


def _parse_bool(value: str, default: bool) -> bool:
    if value is None:
        return default
    return value.strip().lower() in {"1", "true", "yes", "on"}


def _parse_csv(value: str, default: Tuple[str, ...]) -> Tuple[str, ...]:
    if value is None:
        return default
    items = [item.strip() for item in value.split(",") if item.strip()]
    return tuple(items) if items else default


@dataclass(frozen=True)

class Settings:
    database_url: str
    sql_echo: bool
    cors_allow_origins: Tuple[str, ...]
    cors_allow_credentials: bool
    cors_allow_methods: Tuple[str, ...]
    cors_allow_headers: Tuple[str, ...]
    secret_key: str
    access_token_expire_minutes: int
    cookie_secure: bool
    log_level: str
    admin_password_hash: str

@lru_cache(maxsize=1)
def get_settings() -> Settings:
    return Settings(
        database_url=os.getenv("DATABASE_URL", "sqlite:///./basij.db"),
        sql_echo=_parse_bool(os.getenv("SQL_ECHO"), False),
        cors_allow_origins=_parse_csv(os.getenv("CORS_ALLOW_ORIGINS"), ("*",)),
        cors_allow_credentials=_parse_bool(os.getenv("CORS_ALLOW_CREDENTIALS"), True),
        cors_allow_methods=_parse_csv(os.getenv("CORS_ALLOW_METHODS"), ("*",)),
        cors_allow_headers=_parse_csv(os.getenv("CORS_ALLOW_HEADERS"), ("*",)),
        secret_key=os.getenv("SECRET_KEY", "CHANGE_THIS_SECRET_KEY"),
        access_token_expire_minutes=int(os.getenv("ACCESS_TOKEN_EXPIRE_MINUTES", "60")),
        cookie_secure=_parse_bool(os.getenv("COOKIE_SECURE"), False),
        log_level=os.getenv("LOG_LEVEL", "INFO"),
        admin_password_hash=os.getenv("ADMIN_PASSWORD_HASH", ""),
    )

@lru_cache(maxsize=1)
def get_settings() -> Settings:
    return Settings(
        database_url=os.getenv("DATABASE_URL", "sqlite:///./basij.db"),
        sql_echo=_parse_bool(os.getenv("SQL_ECHO"), False),
        cors_allow_origins=_parse_csv(os.getenv("CORS_ALLOW_ORIGINS"), ("*",)),
        cors_allow_credentials=_parse_bool(os.getenv("CORS_ALLOW_CREDENTIALS"), True),
        cors_allow_methods=_parse_csv(os.getenv("CORS_ALLOW_METHODS"), ("*",)),
        cors_allow_headers=_parse_csv(os.getenv("CORS_ALLOW_HEADERS"), ("*",)),
        secret_key=os.getenv("SECRET_KEY", "CHANGE_THIS_SECRET_KEY"),
        access_token_expire_minutes=int(os.getenv("ACCESS_TOKEN_EXPIRE_MINUTES", "60")),
        cookie_secure=_parse_bool(os.getenv("COOKIE_SECURE"), False),
        log_level=os.getenv("LOG_LEVEL", "INFO"),
        admin_password_hash=os.getenv("ADMIN_PASSWORD_HASH", ""),
    )


settings = get_settings()