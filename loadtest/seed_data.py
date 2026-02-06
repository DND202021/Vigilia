#!/usr/bin/env python3
"""Seed test data for load testing.

Creates:
- Test agencies
- Test users (dispatchers, responders, alert systems)
- Test buildings
- Test resources
- Initial incidents and alerts

This script should be run BEFORE load tests to populate the database
with realistic baseline data.
"""

import asyncio
import sys
import os
from datetime import datetime, timezone
from pathlib import Path

# Add backend to Python path
backend_path = Path(__file__).parent.parent / "src" / "backend"
sys.path.insert(0, str(backend_path))

from sqlalchemy.ext.asyncio import create_async_engine, AsyncSession
from sqlalchemy.orm import sessionmaker
from sqlalchemy import select

from app.core.config import get_settings
from app.models.base import Base
from app.models.user import User
from app.models.agency import Agency
from app.models.role import Role
from app.models.building import Building, BuildingType, OccupancyType, ConstructionType, HazardLevel
from app.models.resource import Resource, ResourceType, ResourceStatus
from app.models.incident import Incident, IncidentStatus, IncidentCategory, IncidentPriority
from app.models.alert import Alert, AlertStatus, AlertSeverity, AlertSource
from app.core.security import get_password_hash


async def create_test_agency(session: AsyncSession) -> Agency:
    """Create a test agency."""
    agency = Agency(
        name="Load Test Agency",
        agency_code="LOADTEST",
        city="Montreal",
        province_state="Quebec",
        country="Canada",
        timezone="America/Toronto",
        is_active=True
    )
    session.add(agency)
    await session.flush()
    return agency


async def create_test_users(session: AsyncSession, agency: Agency) -> dict[str, list[User]]:
    """Create test users for different roles."""
    # Get roles
    role_query = select(Role)
    result = await session.execute(role_query)
    roles = {role.name: role for role in result.scalars().all()}

    dispatcher_role = roles.get("dispatcher")
    responder_role = roles.get("responder")
    public_user_role = roles.get("public_user")

    users = {
        "dispatchers": [],
        "responders": [],
        "alert_systems": []
    }

    # Create 100 dispatchers
    print("Creating 100 dispatchers...")
    for i in range(1, 101):
        user = User(
            email=f"dispatcher{i}@test.eriop.local",
            hashed_password=get_password_hash("TestPass123456!"),
            full_name=f"Dispatcher {i}",
            role_id=dispatcher_role.id if dispatcher_role else None,
            agency_id=agency.id,
            is_active=True,
            is_verified=True,
            mfa_enabled=False
        )
        session.add(user)
        users["dispatchers"].append(user)

    # Create 200 responders
    print("Creating 200 responders...")
    for i in range(1, 201):
        user = User(
            email=f"responder{i}@test.eriop.local",
            hashed_password=get_password_hash("TestPass123456!"),
            full_name=f"Responder {i}",
            badge_number=f"R{i:04d}",
            role_id=responder_role.id if responder_role else None,
            agency_id=agency.id,
            is_active=True,
            is_verified=True,
            mfa_enabled=False
        )
        session.add(user)
        users["responders"].append(user)

    # Create 50 alert system users
    print("Creating 50 alert system users...")
    for i in range(1, 51):
        user = User(
            email=f"alertsystem{i}@test.eriop.local",
            hashed_password=get_password_hash("TestPass123456!"),
            full_name=f"Alert System {i}",
            role_id=public_user_role.id if public_user_role else None,
            agency_id=agency.id,
            is_active=True,
            is_verified=True,
            mfa_enabled=False
        )
        session.add(user)
        users["alert_systems"].append(user)

    await session.flush()
    return users


async def create_test_buildings(session: AsyncSession) -> list[Building]:
    """Create test buildings."""
    print("Creating 50 test buildings...")
    buildings = []

    base_lat = 45.5017  # Montreal
    base_lon = -73.5673

    for i in range(1, 51):
        building = Building(
            name=f"Test Building {i}",
            civic_number=str(1000 + i),
            street_name="Test Street",
            street_type="Street",
            city="Montreal",
            province_state="Quebec",
            postal_code=f"H1H {i:03d}",
            country="Canada",
            latitude=base_lat + (i * 0.01),
            longitude=base_lon + (i * 0.01),
            building_type=BuildingType.COMMERCIAL,
            occupancy_type=OccupancyType.BUSINESS,
            construction_type=ConstructionType.TYPE_III,
            hazard_level=HazardLevel.MODERATE,
            total_floors=i % 10 + 1,
            basement_levels=1 if i % 3 == 0 else 0,
            has_sprinkler_system=i % 2 == 0,
            has_fire_alarm=True,
            has_elevator=i % 2 == 0
        )
        session.add(building)
        buildings.append(building)

    await session.flush()
    return buildings


async def create_test_resources(session: AsyncSession, agency: Agency) -> list[Resource]:
    """Create test resources."""
    print("Creating 100 test resources...")
    resources = []

    base_lat = 45.5017
    base_lon = -73.5673

    # 40 personnel
    for i in range(1, 41):
        resource = Resource(
            resource_type=ResourceType.PERSONNEL,
            name=f"Officer {i}",
            call_sign=f"P-{i:03d}",
            status=ResourceStatus.AVAILABLE if i <= 30 else ResourceStatus.OFF_DUTY,
            current_latitude=base_lat + (i * 0.005),
            current_longitude=base_lon + (i * 0.005),
            agency_id=agency.id
        )
        session.add(resource)
        resources.append(resource)

    # 40 vehicles
    for i in range(1, 41):
        resource = Resource(
            resource_type=ResourceType.VEHICLE,
            name=f"Vehicle {i}",
            call_sign=f"V-{i:03d}",
            status=ResourceStatus.AVAILABLE if i <= 30 else ResourceStatus.OUT_OF_SERVICE,
            current_latitude=base_lat + (i * 0.005),
            current_longitude=base_lon + (i * 0.005),
            agency_id=agency.id
        )
        session.add(resource)
        resources.append(resource)

    # 20 equipment
    for i in range(1, 21):
        resource = Resource(
            resource_type=ResourceType.EQUIPMENT,
            name=f"Equipment {i}",
            call_sign=f"E-{i:03d}",
            status=ResourceStatus.AVAILABLE if i <= 15 else ResourceStatus.OUT_OF_SERVICE,
            agency_id=agency.id
        )
        session.add(resource)
        resources.append(resource)

    await session.flush()
    return resources


async def create_baseline_incidents(session: AsyncSession, agency: Agency) -> list[Incident]:
    """Create baseline incidents."""
    print("Creating 50 baseline incidents...")
    incidents = []

    base_lat = 45.5017
    base_lon = -73.5673

    categories = [IncidentCategory.FIRE, IncidentCategory.MEDICAL, IncidentCategory.POLICE,
                  IncidentCategory.RESCUE, IncidentCategory.TRAFFIC]
    statuses = [IncidentStatus.NEW, IncidentStatus.ASSIGNED, IncidentStatus.EN_ROUTE,
                IncidentStatus.ON_SCENE]

    for i in range(1, 51):
        now = datetime.now(timezone.utc)
        incident = Incident(
            incident_number=f"INC-LOAD-{i:04d}",
            category=categories[i % len(categories)],
            priority=((i % 5) + 1),  # 1-5
            status=statuses[i % len(statuses)],
            title=f"Test Incident {i}",
            description=f"Baseline incident for load testing",
            latitude=base_lat + (i * 0.01),
            longitude=base_lon + (i * 0.01),
            address=f"{1000 + i} Test Street",
            reported_at=now,
            agency_id=agency.id,
            assigned_units=[]
        )
        session.add(incident)
        incidents.append(incident)

    await session.flush()
    return incidents


async def create_baseline_alerts(session: AsyncSession) -> list[Alert]:
    """Create baseline alerts."""
    print("Creating 100 baseline alerts...")
    alerts = []

    base_lat = 45.5017
    base_lon = -73.5673

    alert_types = ["gunshot", "explosion", "glass_break", "aggression", "scream", "car_alarm"]
    severities = [AlertSeverity.CRITICAL, AlertSeverity.HIGH, AlertSeverity.MEDIUM, AlertSeverity.LOW]
    sources = [AlertSource.FUNDAMENTUM, AlertSource.ALARM_SYSTEM, AlertSource.AXIS_MICROPHONE]

    for i in range(1, 101):
        now = datetime.now(timezone.utc)
        alert = Alert(
            source=sources[i % len(sources)],
            source_id=f"device_{1000 + i}",
            severity=severities[i % len(severities)],
            status=AlertStatus.PENDING if i <= 50 else AlertStatus.ACKNOWLEDGED,
            alert_type=alert_types[i % len(alert_types)],
            title=f"Test Alert {i}",
            description="Baseline alert for load testing",
            latitude=base_lat + (i * 0.01),
            longitude=base_lon + (i * 0.01),
            address=f"{1000 + i} Alert Street",
            raw_payload={"test": True, "baseline": True}
        )
        session.add(alert)
        alerts.append(alert)

    await session.flush()
    return alerts


async def main():
    """Main seeding function."""
    print("\n" + "="*80)
    print("ERIOP Load Test Data Seeding")
    print("="*80 + "\n")

    settings = get_settings()
    engine = create_async_engine(settings.database_url, echo=False)

    async_session = sessionmaker(
        engine, class_=AsyncSession, expire_on_commit=False
    )

    async with async_session() as session:
        try:
            print("Creating test agency...")
            agency = await create_test_agency(session)

            print("Creating test users...")
            users = await create_test_users(session, agency)

            print("Creating test buildings...")
            buildings = await create_test_buildings(session)

            print("Creating test resources...")
            resources = await create_test_resources(session, agency)

            print("Creating baseline incidents...")
            incidents = await create_baseline_incidents(session, agency)

            print("Creating baseline alerts...")
            alerts = await create_baseline_alerts(session)

            await session.commit()

            print("\n" + "="*80)
            print("Seeding Complete!")
            print("="*80)
            print(f"Created:")
            print(f"  - 1 test agency")
            print(f"  - {len(users['dispatchers'])} dispatchers")
            print(f"  - {len(users['responders'])} responders")
            print(f"  - {len(users['alert_systems'])} alert system users")
            print(f"  - {len(buildings)} buildings")
            print(f"  - {len(resources)} resources")
            print(f"  - {len(incidents)} incidents")
            print(f"  - {len(alerts)} alerts")
            print("="*80 + "\n")

        except Exception as e:
            print(f"\nERROR: {e}")
            await session.rollback()
            raise
        finally:
            await engine.dispose()


if __name__ == "__main__":
    asyncio.run(main())
