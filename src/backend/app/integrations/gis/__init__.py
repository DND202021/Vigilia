"""GIS Integration Service.

Provides geographic information services including:
- Address geocoding/reverse geocoding
- Jurisdiction boundary lookup
- Map layer management
- Routing and distance calculations
"""

from app.integrations.gis.service import (
    GISService,
    GeocodedAddress,
    Jurisdiction,
    MapLayer,
    GISError,
)

__all__ = [
    "GISService",
    "GeocodedAddress",
    "Jurisdiction",
    "MapLayer",
    "GISError",
]
