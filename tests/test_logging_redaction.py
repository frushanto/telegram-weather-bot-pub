import json
import logging

import pytest

from weatherbot.observability.logging import configure_logging


@pytest.fixture(autouse=True)
def reset_logging():
    # Ensure a clean logging setup per test
    root = logging.getLogger()
    for h in list(root.handlers):
        root.removeHandler(h)
    for f in list(root.filters):
        root.removeFilter(f)
    yield
    for h in list(root.handlers):
        root.removeHandler(h)
    for f in list(root.filters):
        root.removeFilter(f)


def _parse_last_json_line(stderr_text: str) -> dict:
    # Our logger outputs one JSON object per line; take the last non-empty line
    lines = [ln for ln in stderr_text.splitlines() if ln.strip()]
    assert lines, "no log output captured"
    return json.loads(lines[-1])


def test_redacts_token_when_url_in_message(capsys):
    configure_logging()
    url = "https://api.telegram.org/bot12345:ABCdef/getUpdates"
    logging.getLogger("test").info("Request to %s", url)

    captured = capsys.readouterr()
    payload = _parse_last_json_line(captured.err)
    assert "***REDACTED***" in payload["message"]
    assert "bot12345:ABCdef" not in payload["message"]


def test_redacts_token_when_url_in_plain_msg(capsys):
    configure_logging()
    msg = "HTTP POST https://api.telegram.org/bot999:XYZ/getMe"
    logging.getLogger("test").info(msg)

    captured = capsys.readouterr()
    payload = _parse_last_json_line(captured.err)
    assert "***REDACTED***" in payload["message"]
    assert "bot999:XYZ" not in payload["message"]


def test_httpx_info_logs_suppressed(capsys):
    configure_logging()
    logging.getLogger("httpx").info(
        "HTTP Request: %s", "https://api.telegram.org/botSHOULDNOT/log"
    )

    captured = capsys.readouterr()
    # No httpx INFO logs should appear due to level WARNING
    assert not captured.err.strip(), "httpx INFO logs should be suppressed"
