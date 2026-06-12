import importlib
import os
import sys


def test_default_admin_password_should_not_use_public_fallback(monkeypatch):
    monkeypatch.delenv("ADMIN_PASSWORD", raising=False)
    monkeypatch.delenv("MARKET_ADMIN_PASSWORD", raising=False)
    monkeypatch.delenv("OPERATOR_ADMIN_PASSWORD", raising=False)
    monkeypatch.delenv("BOSS_PASSWORD", raising=False)

    sys.modules.pop("admin_routes", None)
    admin_routes = importlib.import_module("admin_routes")

    assert admin_routes.DEFAULT_ADMINS["admin"]["password"] != "123456"
    assert admin_routes.DEFAULT_ADMINS["market"]["password"] != "123456"


def test_security_utils_should_respect_environment_secret(monkeypatch):
    monkeypatch.setenv("APP_SECRET_KEY", "env-secret-for-test")
    monkeypatch.setenv("TOKEN_SALT", "env-salt-for-test")

    sys.modules.pop("security_utils", None)
    security_utils = importlib.import_module("security_utils")

    assert security_utils.SECRET_KEY == b"env-secret-for-test"
    assert security_utils.TOKEN_SALT == "env-salt-for-test"
