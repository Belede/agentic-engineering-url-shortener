"""Short-code generation + bounded collision handling. FR-001, FR-003, FR-009, ADR-003.

The DB unique constraint (short_links.code PRIMARY KEY) is the actual source
of concurrency-safety — `exists` here is a caller-supplied existence check
(typically a DB lookup) used only to deterministically bound regeneration
attempts, not to coordinate concurrent writers itself.
"""
import secrets
from collections.abc import Callable

ALPHABET = "0123456789ABCDEFGHIJKLMNOPQRSTUVWXYZabcdefghijklmnopqrstuvwxyz"
CODE_LENGTH = 7


class CodeSpaceExhaustedError(RuntimeError):
    """Raised when max_attempts consecutive collisions occur (FR-009:
    no unbounded retry). Practically unreachable at 62^7 scale."""


def _random_code() -> str:
    return "".join(secrets.choice(ALPHABET) for _ in range(CODE_LENGTH))


def generate_unique_code(exists: Callable[[str], bool], max_attempts: int = 5) -> str:
    for _ in range(max_attempts):
        code = _random_code()
        if not exists(code):
            return code
    raise CodeSpaceExhaustedError(
        f"No unique code found after {max_attempts} attempts"
    )
