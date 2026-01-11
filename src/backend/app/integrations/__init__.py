"""ERIOP External Integrations Module.

This module provides integrations with external systems:
- Alarm systems (Contact ID, SIA protocols)
- Audio analytics (Axis microphones)
- CAD systems (Computer-Aided Dispatch)
- GIS services (geocoding, jurisdictions)
"""

from app.integrations.base import (
    IntegrationError,
    IntegrationAdapter,
    CircuitBreaker,
    CircuitBreakerOpen,
    CircuitState,
)

__all__ = [
    "IntegrationError",
    "IntegrationAdapter",
    "CircuitBreaker",
    "CircuitBreakerOpen",
    "CircuitState",
]
