"""Application configuration. Security-sensitive file (constitution Principle
VI) — changes here require SECURITY_APPROVAL in the orchestration engine
once config-touching workflow runs exist (see docs/scenarios/ambiguous.md).

All values are environment-driven with secure defaults (constitution
Principle V). Settings.from_env() reads the environment fresh on every
call — a dataclass field default like `os.environ.get(...)` is evaluated
ONCE at class-definition time, not per-instantiation, which would silently
freeze every setting to whatever the environment was at import time. This
was a real latent bug caught by tests/unit/test_config_default_ttl.py
(a monkeypatched env var was ignored) while implementing the ambiguous-
scenario's resolution — fixed here for all settings, not just the new one.
"""
import os
from dataclasses import dataclass

MAX_DEFAULT_TTL_DAYS = 365


@dataclass(frozen=True)
class Settings:
    db_path: str
    rate_limit_per_minute: int
    llm_provider: str  # "none" | "anthropic"
    idempotency_retention_seconds: int
    policy_pack_version: str
    # CL-03 resolution (ambiguous scenario): applies ONLY to newly created
    # links that set neither expires_at/ttl_seconds nor no_expiry=true.
    # Existing links are never retroactively affected. Human-approved via
    # ARCH_APPROVAL + SECURITY_APPROVAL (this is a security-sensitive file).
    default_ttl_days: int

    def __post_init__(self) -> None:
        if self.default_ttl_days > MAX_DEFAULT_TTL_DAYS:
            raise ValueError(
                f"SHORTENER_DEFAULT_TTL_DAYS={self.default_ttl_days} exceeds the "
                f"maximum of {MAX_DEFAULT_TTL_DAYS} days"
            )

    @classmethod
    def from_env(cls) -> "Settings":
        return cls(
            db_path=os.environ.get("SHORTENER_DB_PATH", "shortener.db"),
            rate_limit_per_minute=int(os.environ.get("SHORTENER_RATE_LIMIT_PER_MINUTE", "60")),
            llm_provider=os.environ.get("LLM_PROVIDER", "none"),
            idempotency_retention_seconds=int(
                os.environ.get("SHORTENER_IDEMPOTENCY_RETENTION_SECONDS", "86400")
            ),
            policy_pack_version=os.environ.get("SHORTENER_POLICY_PACK_VERSION", "1.0.0"),
            default_ttl_days=int(os.environ.get("SHORTENER_DEFAULT_TTL_DAYS", "90")),
        )


def get_settings() -> Settings:
    return Settings.from_env()
