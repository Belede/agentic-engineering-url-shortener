"""T042 implementation: SHORTENER_DEFAULT_TTL_DAYS config. Resolved CL-03
(ambiguous scenario), real human-approved design (ARCH_APPROVAL + SECURITY_APPROVAL)."""
import pytest

from shortener.config import Settings


def test_default_ttl_days_defaults_to_90(monkeypatch):
    monkeypatch.delenv("SHORTENER_DEFAULT_TTL_DAYS", raising=False)
    assert Settings.from_env().default_ttl_days == 90


def test_default_ttl_days_reads_from_env(monkeypatch):
    monkeypatch.setenv("SHORTENER_DEFAULT_TTL_DAYS", "30")
    assert Settings.from_env().default_ttl_days == 30


def test_default_ttl_days_rejects_value_over_365(monkeypatch):
    monkeypatch.setenv("SHORTENER_DEFAULT_TTL_DAYS", "400")
    with pytest.raises(ValueError, match="365"):
        Settings.from_env()
