"""EMR Adapter Factory — selects the correct vendor adapter based on settings."""

from ..config import settings
from .emr_base import BaseEMRAdapter
from .vendors.noop import NoOpAdapter


def get_emr_adapter() -> BaseEMRAdapter:
    """Return the configured EMR adapter instance.

    Reads settings.EMR_VENDOR and settings.EMR_ENDPOINT.
    Adapters are lazily instantiated and cached.
    """
    global _adapter_cache

    vendor = settings.EMR_VENDOR
    endpoint = settings.EMR_ENDPOINT
    cache_key = (vendor, endpoint)

    if cache_key in _adapter_cache:
        return _adapter_cache[cache_key]

    adapter = _create_adapter(vendor, endpoint)
    _adapter_cache[cache_key] = adapter
    return adapter


def _create_adapter(vendor: str, endpoint: str) -> BaseEMRAdapter:
    if vendor == "neusoft":
        from .vendors.neusoft import NeusoftAdapter
        return NeusoftAdapter(endpoint)
    if vendor == "winning":
        from .vendors.winning import WinningAdapter
        return WinningAdapter(endpoint)
    if vendor == "bsoft":
        from .vendors.bsoft import BsoftAdapter
        return BsoftAdapter(endpoint)
    if vendor == "wonders":
        from .vendors.wonders import WondersAdapter
        return WondersAdapter(endpoint)
    if vendor == "xintong":
        from .vendors.xintong import XintongAdapter
        return XintongAdapter(endpoint)
    if vendor == "zuobiao":
        from .vendors.zuobiao import ZuobiaoAdapter
        return ZuobiaoAdapter(endpoint)
    if vendor == "fhir":
        from .vendors.fhir_standard import FHIRStandardAdapter
        return FHIRStandardAdapter(endpoint)
    # Default: noop
    return NoOpAdapter(endpoint)


def reset_emr_adapter() -> None:
    """Clear the cached adapter (useful for testing)."""
    _adapter_cache.clear()


# Module-level cache
_adapter_cache: dict[tuple[str, str], BaseEMRAdapter] = {}
