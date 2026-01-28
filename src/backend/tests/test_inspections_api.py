"""Tests for Building Inspections API endpoints."""

import pytest
from uuid import uuid4
from datetime import date, timedelta

from app.models.inspection import Inspection, InspectionType, InspectionStatus


class TestInspectionsAPI:
    """Tests for inspection management endpoints."""

    async def get_admin_token(self, client) -> str:
        """Helper to get admin auth token for API requests."""
        login_response = await client.post(
            "/api/v1/auth/login",
            json={
                "email": "admin@example.com",
                "password": "AdminPassword123!",
            },
        )
        return login_response.json()["access_token"]

    async def create_test_building(self, client, token: str) -> str:
        """Helper to create a test building and return its ID."""
        response = await client.post(
            "/api/v1/buildings",
            headers={"Authorization": f"Bearer {token}"},
            json={
                "name": "Inspection Test Building",
                "street_name": "Test Street",
                "city": "Montreal",
                "province_state": "Quebec",
                "latitude": 45.5017,
                "longitude": -73.5673,
            },
        )
        return response.json()["id"]

    @pytest.mark.asyncio
    async def test_create_inspection(self, client, admin_user, test_agency):
        """Test creating an inspection."""
        token = await self.get_admin_token(client)
        building_id = await self.create_test_building(client, token)

        future_date = (date.today() + timedelta(days=30)).isoformat()

        response = await client.post(
            f"/api/v1/buildings/{building_id}/inspections",
            headers={"Authorization": f"Bearer {token}"},
            params={
                "inspection_type": "fire_safety",
                "scheduled_date": future_date,
                "inspector_name": "John Inspector",
            },
        )
        assert response.status_code == 200
        data = response.json()
        assert data["inspection_type"] == "fire_safety"
        assert data["scheduled_date"] == future_date
        assert data["inspector_name"] == "John Inspector"
        assert data["status"] == "scheduled"
        assert "id" in data

    @pytest.mark.asyncio
    async def test_create_inspection_all_types(self, client, admin_user, test_agency):
        """Test creating inspections with all supported types."""
        token = await self.get_admin_token(client)
        building_id = await self.create_test_building(client, token)

        future_date = (date.today() + timedelta(days=30)).isoformat()
        inspection_types = ["fire_safety", "structural", "hazmat", "general"]

        for insp_type in inspection_types:
            response = await client.post(
                f"/api/v1/buildings/{building_id}/inspections",
                headers={"Authorization": f"Bearer {token}"},
                params={
                    "inspection_type": insp_type,
                    "scheduled_date": future_date,
                    "inspector_name": "Test Inspector",
                },
            )
            assert response.status_code == 200
            assert response.json()["inspection_type"] == insp_type

    @pytest.mark.asyncio
    async def test_create_inspection_invalid_type(self, client, admin_user, test_agency):
        """Test creating inspection with invalid type."""
        token = await self.get_admin_token(client)
        building_id = await self.create_test_building(client, token)

        future_date = (date.today() + timedelta(days=30)).isoformat()

        response = await client.post(
            f"/api/v1/buildings/{building_id}/inspections",
            headers={"Authorization": f"Bearer {token}"},
            params={
                "inspection_type": "invalid_type",
                "scheduled_date": future_date,
                "inspector_name": "Test Inspector",
            },
        )
        assert response.status_code == 400

    @pytest.mark.asyncio
    async def test_create_inspection_invalid_date(self, client, admin_user, test_agency):
        """Test creating inspection with invalid date format."""
        token = await self.get_admin_token(client)
        building_id = await self.create_test_building(client, token)

        response = await client.post(
            f"/api/v1/buildings/{building_id}/inspections",
            headers={"Authorization": f"Bearer {token}"},
            params={
                "inspection_type": "fire_safety",
                "scheduled_date": "not-a-date",
                "inspector_name": "Test Inspector",
            },
        )
        assert response.status_code == 400

    @pytest.mark.asyncio
    async def test_create_inspection_building_not_found(self, client, admin_user, test_agency):
        """Test creating inspection for non-existent building."""
        token = await self.get_admin_token(client)

        future_date = (date.today() + timedelta(days=30)).isoformat()

        response = await client.post(
            f"/api/v1/buildings/{uuid4()}/inspections",
            headers={"Authorization": f"Bearer {token}"},
            params={
                "inspection_type": "fire_safety",
                "scheduled_date": future_date,
                "inspector_name": "Test Inspector",
            },
        )
        assert response.status_code == 404

    @pytest.mark.asyncio
    async def test_list_inspections(self, client, admin_user, test_agency):
        """Test listing inspections for a building."""
        token = await self.get_admin_token(client)
        building_id = await self.create_test_building(client, token)

        # Create multiple inspections
        for i in range(3):
            future_date = (date.today() + timedelta(days=30 + i * 7)).isoformat()
            await client.post(
                f"/api/v1/buildings/{building_id}/inspections",
                headers={"Authorization": f"Bearer {token}"},
                params={
                    "inspection_type": "fire_safety",
                    "scheduled_date": future_date,
                    "inspector_name": f"Inspector {i}",
                },
            )

        response = await client.get(
            f"/api/v1/buildings/{building_id}/inspections",
            headers={"Authorization": f"Bearer {token}"},
        )
        assert response.status_code == 200
        data = response.json()
        assert data["total"] == 3
        assert len(data["items"]) == 3

    @pytest.mark.asyncio
    async def test_list_inspections_empty(self, client, admin_user, test_agency):
        """Test listing inspections for building with no inspections."""
        token = await self.get_admin_token(client)
        building_id = await self.create_test_building(client, token)

        response = await client.get(
            f"/api/v1/buildings/{building_id}/inspections",
            headers={"Authorization": f"Bearer {token}"},
        )
        assert response.status_code == 200
        data = response.json()
        assert data["total"] == 0
        assert data["items"] == []

    @pytest.mark.asyncio
    async def test_list_inspections_with_type_filter(self, client, admin_user, test_agency):
        """Test filtering inspections by type."""
        token = await self.get_admin_token(client)
        building_id = await self.create_test_building(client, token)

        future_date = (date.today() + timedelta(days=30)).isoformat()

        # Create inspections of different types
        await client.post(
            f"/api/v1/buildings/{building_id}/inspections",
            headers={"Authorization": f"Bearer {token}"},
            params={
                "inspection_type": "fire_safety",
                "scheduled_date": future_date,
                "inspector_name": "Fire Inspector",
            },
        )
        await client.post(
            f"/api/v1/buildings/{building_id}/inspections",
            headers={"Authorization": f"Bearer {token}"},
            params={
                "inspection_type": "structural",
                "scheduled_date": future_date,
                "inspector_name": "Structural Inspector",
            },
        )

        # Filter by fire_safety
        response = await client.get(
            f"/api/v1/buildings/{building_id}/inspections",
            headers={"Authorization": f"Bearer {token}"},
            params={"inspection_type": "fire_safety"},
        )
        assert response.status_code == 200
        data = response.json()
        assert data["total"] == 1
        assert data["items"][0]["inspection_type"] == "fire_safety"

    @pytest.mark.asyncio
    async def test_list_inspections_with_status_filter(self, client, admin_user, test_agency):
        """Test filtering inspections by status."""
        token = await self.get_admin_token(client)
        building_id = await self.create_test_building(client, token)

        future_date = (date.today() + timedelta(days=30)).isoformat()

        # Create an inspection
        create_response = await client.post(
            f"/api/v1/buildings/{building_id}/inspections",
            headers={"Authorization": f"Bearer {token}"},
            params={
                "inspection_type": "fire_safety",
                "scheduled_date": future_date,
                "inspector_name": "Test Inspector",
            },
        )
        inspection_id = create_response.json()["id"]

        # Update status to completed
        await client.patch(
            f"/api/v1/buildings/inspections/{inspection_id}",
            headers={"Authorization": f"Bearer {token}"},
            params={"status": "completed"},
        )

        # Filter by completed status
        response = await client.get(
            f"/api/v1/buildings/{building_id}/inspections",
            headers={"Authorization": f"Bearer {token}"},
            params={"status": "completed"},
        )
        assert response.status_code == 200
        data = response.json()
        assert data["total"] == 1
        assert data["items"][0]["status"] == "completed"

    @pytest.mark.asyncio
    async def test_list_inspections_pagination(self, client, admin_user, test_agency):
        """Test inspection listing pagination."""
        token = await self.get_admin_token(client)
        building_id = await self.create_test_building(client, token)

        # Create multiple inspections
        for i in range(5):
            future_date = (date.today() + timedelta(days=30 + i)).isoformat()
            await client.post(
                f"/api/v1/buildings/{building_id}/inspections",
                headers={"Authorization": f"Bearer {token}"},
                params={
                    "inspection_type": "fire_safety",
                    "scheduled_date": future_date,
                    "inspector_name": f"Inspector {i}",
                },
            )

        # Get first page with page_size=2
        response = await client.get(
            f"/api/v1/buildings/{building_id}/inspections",
            headers={"Authorization": f"Bearer {token}"},
            params={"page": 1, "page_size": 2},
        )
        assert response.status_code == 200
        data = response.json()
        assert data["total"] == 5
        assert len(data["items"]) == 2
        assert data["page"] == 1
        assert data["page_size"] == 2
        assert data["total_pages"] == 3

    @pytest.mark.asyncio
    async def test_get_inspection(self, client, admin_user, test_agency):
        """Test getting a single inspection."""
        token = await self.get_admin_token(client)
        building_id = await self.create_test_building(client, token)

        future_date = (date.today() + timedelta(days=30)).isoformat()

        create_response = await client.post(
            f"/api/v1/buildings/{building_id}/inspections",
            headers={"Authorization": f"Bearer {token}"},
            params={
                "inspection_type": "fire_safety",
                "scheduled_date": future_date,
                "inspector_name": "Test Inspector",
            },
        )
        inspection_id = create_response.json()["id"]

        response = await client.get(
            f"/api/v1/buildings/inspections/{inspection_id}",
            headers={"Authorization": f"Bearer {token}"},
        )
        assert response.status_code == 200
        assert response.json()["id"] == inspection_id
        assert response.json()["inspection_type"] == "fire_safety"

    @pytest.mark.asyncio
    async def test_get_inspection_not_found(self, client, admin_user, test_agency):
        """Test getting a non-existent inspection."""
        token = await self.get_admin_token(client)

        response = await client.get(
            f"/api/v1/buildings/inspections/{uuid4()}",
            headers={"Authorization": f"Bearer {token}"},
        )
        assert response.status_code == 404

    @pytest.mark.asyncio
    async def test_update_inspection(self, client, admin_user, test_agency):
        """Test updating an inspection."""
        token = await self.get_admin_token(client)
        building_id = await self.create_test_building(client, token)

        future_date = (date.today() + timedelta(days=30)).isoformat()

        create_response = await client.post(
            f"/api/v1/buildings/{building_id}/inspections",
            headers={"Authorization": f"Bearer {token}"},
            params={
                "inspection_type": "fire_safety",
                "scheduled_date": future_date,
                "inspector_name": "Original Inspector",
            },
        )
        inspection_id = create_response.json()["id"]

        response = await client.patch(
            f"/api/v1/buildings/inspections/{inspection_id}",
            headers={"Authorization": f"Bearer {token}"},
            params={
                "inspector_name": "Updated Inspector",
                "status": "in_progress",
            },
        )
        assert response.status_code == 200
        assert response.json()["inspector_name"] == "Updated Inspector"
        assert response.json()["status"] == "in_progress"

    @pytest.mark.asyncio
    async def test_update_inspection_with_findings(self, client, admin_user, test_agency):
        """Test updating inspection with findings."""
        token = await self.get_admin_token(client)
        building_id = await self.create_test_building(client, token)

        future_date = (date.today() + timedelta(days=30)).isoformat()

        create_response = await client.post(
            f"/api/v1/buildings/{building_id}/inspections",
            headers={"Authorization": f"Bearer {token}"},
            params={
                "inspection_type": "fire_safety",
                "scheduled_date": future_date,
                "inspector_name": "Test Inspector",
            },
        )
        inspection_id = create_response.json()["id"]

        completed_date = date.today().isoformat()

        response = await client.patch(
            f"/api/v1/buildings/inspections/{inspection_id}",
            headers={"Authorization": f"Bearer {token}"},
            params={
                "status": "completed",
                "completed_date": completed_date,
                "findings": "All fire extinguishers up to date. Exit signs illuminated.",
            },
        )
        assert response.status_code == 200
        assert response.json()["status"] == "completed"
        assert response.json()["completed_date"] == completed_date
        assert "fire extinguishers" in response.json()["findings"]

    @pytest.mark.asyncio
    async def test_update_inspection_with_follow_up(self, client, admin_user, test_agency):
        """Test updating inspection with follow-up required."""
        token = await self.get_admin_token(client)
        building_id = await self.create_test_building(client, token)

        future_date = (date.today() + timedelta(days=30)).isoformat()

        create_response = await client.post(
            f"/api/v1/buildings/{building_id}/inspections",
            headers={"Authorization": f"Bearer {token}"},
            params={
                "inspection_type": "fire_safety",
                "scheduled_date": future_date,
                "inspector_name": "Test Inspector",
            },
        )
        inspection_id = create_response.json()["id"]

        follow_up_date = (date.today() + timedelta(days=60)).isoformat()

        response = await client.patch(
            f"/api/v1/buildings/inspections/{inspection_id}",
            headers={"Authorization": f"Bearer {token}"},
            params={
                "status": "failed",
                "findings": "Fire extinguisher expired",
                "follow_up_required": True,
                "follow_up_date": follow_up_date,
            },
        )
        assert response.status_code == 200
        assert response.json()["status"] == "failed"
        assert response.json()["follow_up_required"] is True
        assert response.json()["follow_up_date"] == follow_up_date

    @pytest.mark.asyncio
    async def test_update_inspection_not_found(self, client, admin_user, test_agency):
        """Test updating a non-existent inspection."""
        token = await self.get_admin_token(client)

        response = await client.patch(
            f"/api/v1/buildings/inspections/{uuid4()}",
            headers={"Authorization": f"Bearer {token}"},
            params={"inspector_name": "New Inspector"},
        )
        assert response.status_code == 404

    @pytest.mark.asyncio
    async def test_delete_inspection(self, client, admin_user, test_agency):
        """Test deleting an inspection."""
        token = await self.get_admin_token(client)
        building_id = await self.create_test_building(client, token)

        future_date = (date.today() + timedelta(days=30)).isoformat()

        create_response = await client.post(
            f"/api/v1/buildings/{building_id}/inspections",
            headers={"Authorization": f"Bearer {token}"},
            params={
                "inspection_type": "fire_safety",
                "scheduled_date": future_date,
                "inspector_name": "Test Inspector",
            },
        )
        inspection_id = create_response.json()["id"]

        response = await client.delete(
            f"/api/v1/buildings/inspections/{inspection_id}",
            headers={"Authorization": f"Bearer {token}"},
        )
        assert response.status_code == 200

        # Verify deleted
        get_response = await client.get(
            f"/api/v1/buildings/inspections/{inspection_id}",
            headers={"Authorization": f"Bearer {token}"},
        )
        assert get_response.status_code == 404

    @pytest.mark.asyncio
    async def test_delete_inspection_not_found(self, client, admin_user, test_agency):
        """Test deleting a non-existent inspection."""
        token = await self.get_admin_token(client)

        response = await client.delete(
            f"/api/v1/buildings/inspections/{uuid4()}",
            headers={"Authorization": f"Bearer {token}"},
        )
        assert response.status_code == 404

    @pytest.mark.asyncio
    async def test_get_upcoming_inspections(self, client, admin_user, test_agency):
        """Test getting upcoming inspections across all buildings."""
        token = await self.get_admin_token(client)
        building_id = await self.create_test_building(client, token)

        # Create inspections with future dates
        for i in range(3):
            future_date = (date.today() + timedelta(days=10 + i * 7)).isoformat()
            await client.post(
                f"/api/v1/buildings/{building_id}/inspections",
                headers={"Authorization": f"Bearer {token}"},
                params={
                    "inspection_type": "fire_safety",
                    "scheduled_date": future_date,
                    "inspector_name": f"Inspector {i}",
                },
            )

        response = await client.get(
            "/api/v1/buildings/inspections/upcoming",
            headers={"Authorization": f"Bearer {token}"},
        )
        assert response.status_code == 200
        data = response.json()
        assert data["total"] >= 3
        # Verify all returned inspections are in the future
        for item in data["items"]:
            assert item["status"] == "scheduled"

    @pytest.mark.asyncio
    async def test_get_upcoming_inspections_pagination(self, client, admin_user, test_agency):
        """Test pagination of upcoming inspections."""
        token = await self.get_admin_token(client)
        building_id = await self.create_test_building(client, token)

        # Create multiple inspections
        for i in range(5):
            future_date = (date.today() + timedelta(days=10 + i)).isoformat()
            await client.post(
                f"/api/v1/buildings/{building_id}/inspections",
                headers={"Authorization": f"Bearer {token}"},
                params={
                    "inspection_type": "fire_safety",
                    "scheduled_date": future_date,
                    "inspector_name": f"Inspector {i}",
                },
            )

        response = await client.get(
            "/api/v1/buildings/inspections/upcoming",
            headers={"Authorization": f"Bearer {token}"},
            params={"page": 1, "page_size": 2},
        )
        assert response.status_code == 200
        data = response.json()
        assert data["page"] == 1
        assert data["page_size"] == 2
        assert len(data["items"]) <= 2

    @pytest.mark.asyncio
    async def test_get_overdue_inspections(self, client, admin_user, test_agency):
        """Test getting overdue inspections."""
        token = await self.get_admin_token(client)
        building_id = await self.create_test_building(client, token)

        # Create an inspection with a past date
        past_date = (date.today() - timedelta(days=10)).isoformat()
        await client.post(
            f"/api/v1/buildings/{building_id}/inspections",
            headers={"Authorization": f"Bearer {token}"},
            params={
                "inspection_type": "fire_safety",
                "scheduled_date": past_date,
                "inspector_name": "Past Inspector",
            },
        )

        # Create an inspection with a future date (should not appear)
        future_date = (date.today() + timedelta(days=10)).isoformat()
        await client.post(
            f"/api/v1/buildings/{building_id}/inspections",
            headers={"Authorization": f"Bearer {token}"},
            params={
                "inspection_type": "fire_safety",
                "scheduled_date": future_date,
                "inspector_name": "Future Inspector",
            },
        )

        response = await client.get(
            "/api/v1/buildings/inspections/overdue",
            headers={"Authorization": f"Bearer {token}"},
        )
        assert response.status_code == 200
        data = response.json()
        # Should have at least the past inspection
        assert data["total"] >= 1
        # All returned inspections should have status=scheduled and past date
        for item in data["items"]:
            assert item["status"] == "scheduled"
            item_date = date.fromisoformat(item["scheduled_date"])
            assert item_date < date.today()

    @pytest.mark.asyncio
    async def test_get_overdue_inspections_excludes_completed(self, client, admin_user, test_agency):
        """Test that completed inspections don't appear in overdue list."""
        token = await self.get_admin_token(client)
        building_id = await self.create_test_building(client, token)

        # Create an inspection with a past date
        past_date = (date.today() - timedelta(days=10)).isoformat()
        create_response = await client.post(
            f"/api/v1/buildings/{building_id}/inspections",
            headers={"Authorization": f"Bearer {token}"},
            params={
                "inspection_type": "fire_safety",
                "scheduled_date": past_date,
                "inspector_name": "Past Inspector",
            },
        )
        inspection_id = create_response.json()["id"]

        # Mark it as completed
        await client.patch(
            f"/api/v1/buildings/inspections/{inspection_id}",
            headers={"Authorization": f"Bearer {token}"},
            params={"status": "completed"},
        )

        response = await client.get(
            "/api/v1/buildings/inspections/overdue",
            headers={"Authorization": f"Bearer {token}"},
        )
        assert response.status_code == 200
        data = response.json()
        # The completed inspection should not appear
        for item in data["items"]:
            assert item["id"] != inspection_id

    @pytest.mark.asyncio
    async def test_inspection_created_by_tracked(self, client, admin_user, test_agency):
        """Test that created_by_id is tracked for inspections."""
        token = await self.get_admin_token(client)
        building_id = await self.create_test_building(client, token)

        future_date = (date.today() + timedelta(days=30)).isoformat()

        response = await client.post(
            f"/api/v1/buildings/{building_id}/inspections",
            headers={"Authorization": f"Bearer {token}"},
            params={
                "inspection_type": "fire_safety",
                "scheduled_date": future_date,
                "inspector_name": "Test Inspector",
            },
        )
        assert response.status_code == 200
        data = response.json()
        assert "created_by_id" in data
        # Should have the admin user's ID
        assert data["created_by_id"] is not None

    @pytest.mark.asyncio
    async def test_update_inspection_reschedule(self, client, admin_user, test_agency):
        """Test rescheduling an inspection."""
        token = await self.get_admin_token(client)
        building_id = await self.create_test_building(client, token)

        original_date = (date.today() + timedelta(days=30)).isoformat()

        create_response = await client.post(
            f"/api/v1/buildings/{building_id}/inspections",
            headers={"Authorization": f"Bearer {token}"},
            params={
                "inspection_type": "fire_safety",
                "scheduled_date": original_date,
                "inspector_name": "Test Inspector",
            },
        )
        inspection_id = create_response.json()["id"]

        new_date = (date.today() + timedelta(days=60)).isoformat()

        response = await client.patch(
            f"/api/v1/buildings/inspections/{inspection_id}",
            headers={"Authorization": f"Bearer {token}"},
            params={"scheduled_date": new_date},
        )
        assert response.status_code == 200
        assert response.json()["scheduled_date"] == new_date
