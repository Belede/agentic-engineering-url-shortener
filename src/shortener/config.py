"""Application configuration. Security-sensitive file (ADR constitution VI) —
changes here require SECURITY_APPROVAL in the orchestration engine once
config-touching workflow runs exist (see Scenario C / ambiguous run).

All values are environment-driven with secure defaults (constitution Principle V).
"""
import os
from dataclasses import dataclass


@dataclass(frozen=True)
class Settings:
    db_path: str = os.environ.get("SHORTENER_DB_PATH", "shortener.db")
    rate_limit_per_minute: int = int(os.environ.get("SHORTENER_RATE_LIMIT_PER_MINUTE", "60"))
    llm_provider: str = os.environ.get("LLM_PROVIDER", "none")  # "none" | "anthropic"
    idempotency_retention_seconds: int = int(
        os.environ.get("SHORTENER_IDEMPOTENCY_RETENTION_SECONDS", "86400")
    )
    policy_pack_version: str = os.environ.get("SHORTENER_POLICY_PACK_VERSION", "1.0.0")


def get_settings() -> Settings:
    return Settings()
