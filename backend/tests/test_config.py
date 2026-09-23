import pytest
from pydantic import ValidationError

from app.core.config import Settings


def production_settings(**overrides):
    values = {
        "APP_ENV": "production",
        "DATABASE_URL": "postgresql+psycopg://stock:secret@db:5432/stock",
        "SECRET_KEY": "production-secret-with-more-than-32-characters",
        "BACKEND_CORS_ORIGINS": "https://stock.example.com",
        "TRUSTED_HOSTS": "stock.example.com",
    }
    values.update(overrides)
    return Settings(_env_file=None, **values)


def test_production_settings_accept_explicit_secure_values():
    settings = production_settings()

    assert settings.APP_ENV == "production"
    assert settings.cors_origins == ["https://stock.example.com"]
    assert settings.trusted_hosts == ["stock.example.com"]


@pytest.mark.parametrize(
    ("overrides", "message"),
    [
        ({"DATABASE_URL": "sqlite:///./stock.db"}, "PostgreSQL"),
        ({"SECRET_KEY": "short"}, "SECRET_KEY"),
        ({"SECRET_KEY": "replace-with-a-random-secret-containing-at-least-32-characters"}, "SECRET_KEY"),
        ({"BACKEND_CORS_ORIGINS": "*"}, "BACKEND_CORS_ORIGINS"),
        ({"TRUSTED_HOSTS": "*"}, "TRUSTED_HOSTS"),
    ],
)
def test_production_settings_reject_insecure_values(overrides, message):
    with pytest.raises(ValidationError, match=message):
        production_settings(**overrides)
