"""T006: URL validation — scheme allow-list + SSRF block. FR-002, NFR-001, CL-05."""
import pytest

from shortener.domain.validation import InvalidUrlError, SsrfBlockedError, validate_target_url


@pytest.mark.parametrize("url", [
    "https://example.com/path",
    "http://example.com",
    "https://example.com:8443/a?b=c",
])
def test_accepts_valid_http_https_urls(url):
    validate_target_url(url)  # must not raise


@pytest.mark.parametrize("url", [
    "javascript:alert(1)",
    "data:text/html,<script>alert(1)</script>",
    "file:///etc/passwd",
    "ftp://example.com/file",
    "not-a-url",
    "",
])
def test_rejects_disallowed_scheme_or_malformed(url):
    with pytest.raises(InvalidUrlError):
        validate_target_url(url)


@pytest.mark.parametrize("url", [
    "http://localhost/admin",
    "http://127.0.0.1/secret",
    "http://127.0.0.1:8080/",
    "http://[::1]/admin",
    "http://10.0.0.5/internal",
    "http://172.16.0.1/internal",
    "http://192.168.1.1/router",
])
def test_rejects_ssrf_style_private_and_loopback_targets(url):
    with pytest.raises(SsrfBlockedError):
        validate_target_url(url)


def test_rejects_url_over_length_limit():
    long_url = "https://example.com/" + ("a" * 3000)
    with pytest.raises(InvalidUrlError):
        validate_target_url(long_url)
