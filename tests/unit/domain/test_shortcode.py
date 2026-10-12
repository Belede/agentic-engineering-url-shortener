"""T007: short-code generation + bounded collision handling. FR-001, FR-003, FR-009, ADR-003."""
import re

import pytest

from shortener.domain.shortcode import CodeSpaceExhaustedError, generate_unique_code

CODE_PATTERN = re.compile(r"^[0-9A-Za-z]{7}$")


def test_generated_code_matches_base62_7_char_format():
    code = generate_unique_code(exists=lambda c: False)
    assert CODE_PATTERN.match(code)


def test_regenerates_on_collision_until_unique():
    seen = {"aaaaaaa"}  # pretend this one is already taken

    def exists(code: str) -> bool:
        return code in seen

    code = generate_unique_code(exists=exists)
    assert code != "aaaaaaa"
    assert CODE_PATTERN.match(code)


def test_bounded_regeneration_raises_after_max_attempts():
    """FR-009: no unbounded retry — must give up deterministically."""
    with pytest.raises(CodeSpaceExhaustedError):
        generate_unique_code(exists=lambda c: True, max_attempts=5)


def test_exists_called_at_most_max_attempts_times():
    calls = {"n": 0}

    def exists(code: str) -> bool:
        calls["n"] += 1
        return True

    with pytest.raises(CodeSpaceExhaustedError):
        generate_unique_code(exists=exists, max_attempts=5)
    assert calls["n"] == 5
