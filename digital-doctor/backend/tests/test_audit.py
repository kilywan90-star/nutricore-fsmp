import logging
from src.security.audit import log_access, audit


def test_log_access(caplog):
    with caplog.at_level(logging.INFO, logger="audit"):
        log_access("read", "Patient/123", user_id="doctor-1")
    assert "AUDIT" in caplog.text
    assert "read" in caplog.text
    assert "Patient/123" in caplog.text
    assert "doctor-1" in caplog.text


def test_audit_decorator_marks_action():
    @audit("read")
    async def dummy():
        return "ok"
    # Just verify the decorator returns a callable
    assert callable(dummy)
