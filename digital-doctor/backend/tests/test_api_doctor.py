import pytest
from src.api.doctor import list_patients


@pytest.mark.asyncio
async def test_list_patients_endpoint_requires_db():
    """Test that list_patients properly requires a db session dependency.

    Since we can't provide a real AsyncSession without a running database,
    this test verifies the function signature and behaviour at import time.
    """
    # The function is importable and callable
    import inspect
    sig = inspect.signature(list_patients)
    params = list(sig.parameters.keys())
    assert "page" in params
    assert "page_size" in params
    assert "search" in params
    assert "risk_filter" in params
    assert "db" in params
