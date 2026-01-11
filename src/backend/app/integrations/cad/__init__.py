"""CAD (Computer-Aided Dispatch) Integration.

Provides integration with external CAD systems for:
- Bidirectional incident synchronization
- Unit status updates
- Real-time dispatching
"""

from app.integrations.cad.base import (
    CADAdapter,
    CADIncident,
    CADUnit,
    CADIncidentStatus,
    CADUnitStatus,
    CADAdapterError,
)
from app.integrations.cad.sync_service import CADSyncService
from app.integrations.cad.mock_adapter import MockCADAdapter

__all__ = [
    "CADAdapter",
    "CADIncident",
    "CADUnit",
    "CADIncidentStatus",
    "CADUnitStatus",
    "CADAdapterError",
    "CADSyncService",
    "MockCADAdapter",
]
