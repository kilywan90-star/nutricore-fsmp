import logging
from src.security.audit import audit, log_access, audit_logger


def test_audit_decorator_logs_access(caplog):
    caplog.set_level(logging.INFO, logger="audit")

    @audit("read")
    async def read_patient(patient_id: str):
        return {"id": patient_id}

    # Run the decorated async function
    import asyncio
    result = asyncio.run(read_patient("p-001"))

    assert result == {"id": "p-001"}
    assert len(caplog.records) >= 1
    assert "AUDIT" in caplog.text
    assert "read" in caplog.text
