"""Intelligent Resource Assignment Engine.

This service handles automatic and recommended resource assignments
based on location, capabilities, and incident requirements.
"""

import uuid
from dataclasses import dataclass
from datetime import datetime, timezone
from math import radians, cos, sin, asin, sqrt
from typing import Any

from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

from app.models.resource import Resource, ResourceType, ResourceStatus, Personnel, Vehicle
from app.models.incident import Incident, IncidentCategory, IncidentPriority


@dataclass
class ResourceScore:
    """Scored resource for assignment ranking."""

    resource: Resource
    distance_km: float
    capability_score: float
    availability_score: float
    total_score: float


@dataclass
class AssignmentRecommendation:
    """Recommended resource assignment."""

    resource_id: str
    resource_name: str
    resource_type: str
    call_sign: str | None
    distance_km: float
    score: float
    reasons: list[str]


# Category to capability requirements mapping
CATEGORY_REQUIREMENTS: dict[IncidentCategory, dict[str, Any]] = {
    IncidentCategory.FIRE: {
        "vehicle_types": ["fire_engine", "ladder_truck", "tanker"],
        "specializations": ["firefighter", "hazmat", "rescue"],
        "min_personnel": 4,
    },
    IncidentCategory.MEDICAL: {
        "vehicle_types": ["ambulance", "medic_unit"],
        "specializations": ["paramedic", "emt", "nurse"],
        "min_personnel": 2,
    },
    IncidentCategory.POLICE: {
        "vehicle_types": ["patrol_car", "swat_vehicle"],
        "specializations": ["patrol", "detective", "swat"],
        "min_personnel": 2,
    },
    IncidentCategory.RESCUE: {
        "vehicle_types": ["rescue_vehicle", "heavy_rescue"],
        "specializations": ["rescue", "technical_rescue", "water_rescue"],
        "min_personnel": 4,
    },
    IncidentCategory.TRAFFIC: {
        "vehicle_types": ["patrol_car", "traffic_unit"],
        "specializations": ["traffic_control", "patrol"],
        "min_personnel": 2,
    },
    IncidentCategory.HAZMAT: {
        "vehicle_types": ["hazmat_unit", "decon_unit"],
        "specializations": ["hazmat", "decontamination"],
        "min_personnel": 4,
    },
    IncidentCategory.INTRUSION: {
        "vehicle_types": ["patrol_car", "k9_unit"],
        "specializations": ["patrol", "k9", "investigation"],
        "min_personnel": 2,
    },
}


def haversine_distance(lat1: float, lon1: float, lat2: float, lon2: float) -> float:
    """Calculate the great circle distance between two points in kilometers."""
    # Convert to radians
    lat1, lon1, lat2, lon2 = map(radians, [lat1, lon1, lat2, lon2])

    # Haversine formula
    dlat = lat2 - lat1
    dlon = lon2 - lon1
    a = sin(dlat / 2) ** 2 + cos(lat1) * cos(lat2) * sin(dlon / 2) ** 2
    c = 2 * asin(sqrt(a))

    # Earth's radius in kilometers
    r = 6371

    return c * r


class AssignmentEngine:
    """Service for intelligent resource assignment."""

    def __init__(self, db: AsyncSession):
        """Initialize assignment engine with database session."""
        self.db = db

    async def get_available_resources(
        self,
        agency_id: uuid.UUID,
        resource_types: list[ResourceType] | None = None,
        max_distance_km: float | None = None,
        incident_lat: float | None = None,
        incident_lon: float | None = None,
    ) -> list[Resource]:
        """Get available resources, optionally filtered by type and distance."""
        query = select(Resource).where(
            Resource.agency_id == agency_id,
            Resource.status == ResourceStatus.AVAILABLE,
            Resource.deleted_at.is_(None),
        )

        if resource_types:
            query = query.where(Resource.resource_type.in_(resource_types))

        result = await self.db.execute(query)
        resources = list(result.scalars().all())

        # Filter by distance if location provided
        if max_distance_km and incident_lat and incident_lon:
            resources = [
                r for r in resources
                if r.current_latitude and r.current_longitude
                and haversine_distance(
                    incident_lat, incident_lon,
                    r.current_latitude, r.current_longitude
                ) <= max_distance_km
            ]

        return resources

    async def get_recommendations(
        self,
        incident: Incident,
        max_results: int = 10,
        max_distance_km: float = 50.0,
    ) -> list[AssignmentRecommendation]:
        """Get ranked resource recommendations for an incident.

        Args:
            incident: The incident to get recommendations for
            max_results: Maximum number of recommendations to return
            max_distance_km: Maximum distance to consider resources from

        Returns:
            List of ranked resource recommendations
        """
        # Get category requirements
        requirements = CATEGORY_REQUIREMENTS.get(
            incident.category,
            {"vehicle_types": [], "specializations": [], "min_personnel": 1}
        )

        # Get all available resources for the agency
        resources = await self.get_available_resources(
            agency_id=incident.agency_id,
            max_distance_km=max_distance_km,
            incident_lat=incident.latitude,
            incident_lon=incident.longitude,
        )

        # Score each resource
        scored_resources: list[ResourceScore] = []

        for resource in resources:
            score = await self._score_resource(
                resource,
                incident,
                requirements,
            )
            if score.total_score > 0:
                scored_resources.append(score)

        # Sort by total score (descending)
        scored_resources.sort(key=lambda x: x.total_score, reverse=True)

        # Convert to recommendations
        recommendations = []
        for sr in scored_resources[:max_results]:
            reasons = self._generate_reasons(sr, requirements)
            recommendations.append(AssignmentRecommendation(
                resource_id=str(sr.resource.id),
                resource_name=sr.resource.name,
                resource_type=sr.resource.resource_type.value,
                call_sign=sr.resource.call_sign,
                distance_km=round(sr.distance_km, 2),
                score=round(sr.total_score, 2),
                reasons=reasons,
            ))

        return recommendations

    async def _score_resource(
        self,
        resource: Resource,
        incident: Incident,
        requirements: dict[str, Any],
    ) -> ResourceScore:
        """Score a resource for a given incident."""
        # Calculate distance score (closer = better)
        distance_km = 0.0
        distance_score = 0.0

        if resource.current_latitude and resource.current_longitude:
            distance_km = haversine_distance(
                incident.latitude, incident.longitude,
                resource.current_latitude, resource.current_longitude
            )
            # Score: 1.0 at 0km, 0.0 at 50km+
            distance_score = max(0, 1.0 - (distance_km / 50.0))
        else:
            distance_score = 0.5  # Unknown location gets middle score

        # Calculate capability score
        capability_score = await self._calculate_capability_score(
            resource,
            requirements,
        )

        # Calculate availability score based on status and recent activity
        availability_score = 1.0 if resource.status == ResourceStatus.AVAILABLE else 0.0

        # Weight the scores based on incident priority
        priority_weights = {
            IncidentPriority.CRITICAL: (0.3, 0.5, 0.2),  # capability > distance
            IncidentPriority.HIGH: (0.35, 0.45, 0.2),
            IncidentPriority.MEDIUM: (0.4, 0.4, 0.2),
            IncidentPriority.LOW: (0.5, 0.3, 0.2),  # distance > capability
            IncidentPriority.MINIMAL: (0.5, 0.25, 0.25),
        }

        dist_weight, cap_weight, avail_weight = priority_weights.get(
            IncidentPriority(incident.priority),
            (0.4, 0.4, 0.2)
        )

        total_score = (
            distance_score * dist_weight +
            capability_score * cap_weight +
            availability_score * avail_weight
        )

        return ResourceScore(
            resource=resource,
            distance_km=distance_km,
            capability_score=capability_score,
            availability_score=availability_score,
            total_score=total_score,
        )

    async def _calculate_capability_score(
        self,
        resource: Resource,
        requirements: dict[str, Any],
    ) -> float:
        """Calculate capability match score for a resource."""
        score = 0.0

        if resource.resource_type == ResourceType.VEHICLE:
            # Check if vehicle type matches requirements
            vehicle_types = requirements.get("vehicle_types", [])
            if vehicle_types:
                # Load vehicle-specific data
                vehicle_query = select(Vehicle).where(Vehicle.id == resource.id)
                vehicle_result = await self.db.execute(vehicle_query)
                vehicle = vehicle_result.scalar_one_or_none()

                if vehicle and vehicle.vehicle_type in vehicle_types:
                    score = 1.0
                elif vehicle:
                    score = 0.5  # Related vehicle type

        elif resource.resource_type == ResourceType.PERSONNEL:
            # Check if personnel has required specializations
            specializations = requirements.get("specializations", [])
            if specializations:
                personnel_query = select(Personnel).where(Personnel.id == resource.id)
                personnel_result = await self.db.execute(personnel_query)
                personnel = personnel_result.scalar_one_or_none()

                if personnel and personnel.specializations:
                    matched = sum(
                        1 for s in personnel.specializations
                        if s in specializations
                    )
                    score = matched / len(specializations) if specializations else 0.5
                else:
                    score = 0.3  # No specializations listed

        else:
            # Equipment - basic availability check
            score = 0.5

        return score

    def _generate_reasons(
        self,
        scored_resource: ResourceScore,
        requirements: dict[str, Any],
    ) -> list[str]:
        """Generate human-readable reasons for the recommendation."""
        reasons = []

        if scored_resource.distance_km < 5:
            reasons.append("Very close proximity")
        elif scored_resource.distance_km < 15:
            reasons.append("Good proximity")

        if scored_resource.capability_score >= 0.8:
            reasons.append("Excellent capability match")
        elif scored_resource.capability_score >= 0.5:
            reasons.append("Good capability match")

        if scored_resource.availability_score == 1.0:
            reasons.append("Currently available")

        if not reasons:
            reasons.append("Available resource")

        return reasons

    async def auto_assign(
        self,
        incident: Incident,
        count: int = 1,
    ) -> list[Resource]:
        """Automatically assign best-fit resources to an incident.

        Args:
            incident: The incident to assign resources to
            count: Number of resources to assign

        Returns:
            List of assigned resources
        """
        recommendations = await self.get_recommendations(
            incident,
            max_results=count,
        )

        assigned_resources = []
        for rec in recommendations:
            # Get resource and update status
            resource_query = select(Resource).where(
                Resource.id == uuid.UUID(rec.resource_id)
            )
            result = await self.db.execute(resource_query)
            resource = result.scalar_one_or_none()

            if resource and resource.status == ResourceStatus.AVAILABLE:
                resource.status = ResourceStatus.ASSIGNED
                assigned_resources.append(resource)

                # Add to incident's assigned units
                if incident.assigned_units is None:
                    incident.assigned_units = []
                incident.assigned_units.append(str(resource.id))

        await self.db.commit()
        return assigned_resources
