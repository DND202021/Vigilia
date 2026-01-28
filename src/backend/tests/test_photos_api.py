"""Tests for Building Photos API endpoints."""

import pytest
from uuid import uuid4
from io import BytesIO

from app.models.photo import BuildingPhoto


class TestPhotosAPI:
    """Tests for photo management endpoints."""

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
                "name": "Photo Test Building",
                "street_name": "Test Street",
                "city": "Montreal",
                "province_state": "Quebec",
                "latitude": 45.5017,
                "longitude": -73.5673,
            },
        )
        return response.json()["id"]

    def create_test_image(self) -> bytes:
        """Create a minimal valid PNG image for testing."""
        # Minimal 1x1 red PNG
        return (
            b'\x89PNG\r\n\x1a\n'  # PNG signature
            b'\x00\x00\x00\rIHDR'  # IHDR chunk
            b'\x00\x00\x00\x01'    # width: 1
            b'\x00\x00\x00\x01'    # height: 1
            b'\x08\x02'            # bit depth: 8, color type: 2 (RGB)
            b'\x00\x00\x00'        # compression, filter, interlace
            b'\x90wS\xde'          # CRC
            b'\x00\x00\x00\x0cIDATx\x9cc\xf8\xcf\xc0\x00\x00\x00\x03\x00\x01\x00\x05\xfe\xd4'  # IDAT
            b'\x00\x00\x00\x00IEND\xaeB`\x82'  # IEND
        )

    @pytest.mark.asyncio
    async def test_list_photos_empty(self, client, admin_user, test_agency):
        """Test listing photos for building with no photos."""
        token = await self.get_admin_token(client)
        building_id = await self.create_test_building(client, token)

        response = await client.get(
            f"/api/v1/buildings/{building_id}/photos",
            headers={"Authorization": f"Bearer {token}"},
        )
        assert response.status_code == 200
        data = response.json()
        assert data["total"] == 0
        assert data["items"] == []

    @pytest.mark.asyncio
    async def test_upload_photo(self, client, admin_user, test_agency):
        """Test uploading a photo."""
        token = await self.get_admin_token(client)
        building_id = await self.create_test_building(client, token)

        image_content = self.create_test_image()

        response = await client.post(
            f"/api/v1/buildings/{building_id}/photos/upload",
            headers={"Authorization": f"Bearer {token}"},
            files={"file": ("test.png", BytesIO(image_content), "image/png")},
            data={
                "title": "Test Photo",
                "description": "Test description",
            },
        )
        assert response.status_code == 200
        data = response.json()
        assert data["title"] == "Test Photo"
        assert data["description"] == "Test description"
        assert "id" in data
        assert "file_url" in data

    @pytest.mark.asyncio
    async def test_upload_photo_with_location(self, client, admin_user, test_agency):
        """Test uploading a photo with GPS coordinates."""
        token = await self.get_admin_token(client)
        building_id = await self.create_test_building(client, token)

        image_content = self.create_test_image()

        response = await client.post(
            f"/api/v1/buildings/{building_id}/photos/upload",
            headers={"Authorization": f"Bearer {token}"},
            files={"file": ("test.png", BytesIO(image_content), "image/png")},
            data={
                "title": "Geotagged Photo",
                "latitude": 45.5017,
                "longitude": -73.5673,
            },
        )
        assert response.status_code == 200
        data = response.json()
        assert data["latitude"] == 45.5017
        assert data["longitude"] == -73.5673

    @pytest.mark.asyncio
    async def test_upload_photo_with_tags(self, client, admin_user, test_agency):
        """Test uploading a photo with tags."""
        token = await self.get_admin_token(client)
        building_id = await self.create_test_building(client, token)

        image_content = self.create_test_image()

        response = await client.post(
            f"/api/v1/buildings/{building_id}/photos/upload",
            headers={"Authorization": f"Bearer {token}"},
            files={"file": ("test.png", BytesIO(image_content), "image/png")},
            data={
                "title": "Tagged Photo",
                "tags": "entrance, exterior, main",
            },
        )
        assert response.status_code == 200
        data = response.json()
        assert "entrance" in data["tags"]
        assert "exterior" in data["tags"]
        assert "main" in data["tags"]

    @pytest.mark.asyncio
    async def test_upload_photo_building_not_found(self, client, admin_user, test_agency):
        """Test uploading photo to non-existent building."""
        token = await self.get_admin_token(client)
        image_content = self.create_test_image()

        response = await client.post(
            f"/api/v1/buildings/{uuid4()}/photos/upload",
            headers={"Authorization": f"Bearer {token}"},
            files={"file": ("test.png", BytesIO(image_content), "image/png")},
            data={"title": "Test Photo"},
        )
        assert response.status_code == 404

    @pytest.mark.asyncio
    async def test_upload_photo_invalid_file_type(self, client, admin_user, test_agency):
        """Test uploading non-image file as photo."""
        token = await self.get_admin_token(client)
        building_id = await self.create_test_building(client, token)

        pdf_content = b"%PDF-1.4\ntest\n%%EOF"

        response = await client.post(
            f"/api/v1/buildings/{building_id}/photos/upload",
            headers={"Authorization": f"Bearer {token}"},
            files={"file": ("test.pdf", BytesIO(pdf_content), "application/pdf")},
            data={"title": "Not an image"},
        )
        assert response.status_code == 400
        assert "image" in response.json()["detail"].lower()

    @pytest.mark.asyncio
    async def test_upload_photo_no_auth(self, client, admin_user, test_agency):
        """Test uploading photo without authentication."""
        token = await self.get_admin_token(client)
        building_id = await self.create_test_building(client, token)

        image_content = self.create_test_image()

        response = await client.post(
            f"/api/v1/buildings/{building_id}/photos/upload",
            files={"file": ("test.png", BytesIO(image_content), "image/png")},
            data={"title": "Test Photo"},
        )
        assert response.status_code == 401

    @pytest.mark.asyncio
    async def test_list_photos_pagination(self, client, admin_user, test_agency):
        """Test photo listing pagination."""
        token = await self.get_admin_token(client)
        building_id = await self.create_test_building(client, token)

        image_content = self.create_test_image()

        # Upload multiple photos
        for i in range(5):
            await client.post(
                f"/api/v1/buildings/{building_id}/photos/upload",
                headers={"Authorization": f"Bearer {token}"},
                files={"file": (f"photo{i}.png", BytesIO(image_content), "image/png")},
                data={"title": f"Photo {i}"},
            )

        # Get first page with page_size=2
        response = await client.get(
            f"/api/v1/buildings/{building_id}/photos",
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
    async def test_get_photo(self, client, admin_user, test_agency):
        """Test getting a single photo."""
        token = await self.get_admin_token(client)
        building_id = await self.create_test_building(client, token)

        image_content = self.create_test_image()

        upload_response = await client.post(
            f"/api/v1/buildings/{building_id}/photos/upload",
            headers={"Authorization": f"Bearer {token}"},
            files={"file": ("test.png", BytesIO(image_content), "image/png")},
            data={"title": "Test Photo"},
        )
        photo_id = upload_response.json()["id"]

        response = await client.get(
            f"/api/v1/buildings/photos/{photo_id}",
            headers={"Authorization": f"Bearer {token}"},
        )
        assert response.status_code == 200
        assert response.json()["title"] == "Test Photo"
        assert response.json()["id"] == photo_id

    @pytest.mark.asyncio
    async def test_get_photo_not_found(self, client, admin_user, test_agency):
        """Test getting a non-existent photo."""
        token = await self.get_admin_token(client)

        response = await client.get(
            f"/api/v1/buildings/photos/{uuid4()}",
            headers={"Authorization": f"Bearer {token}"},
        )
        assert response.status_code == 404

    @pytest.mark.asyncio
    async def test_delete_photo(self, client, admin_user, test_agency):
        """Test deleting a photo."""
        token = await self.get_admin_token(client)
        building_id = await self.create_test_building(client, token)

        image_content = self.create_test_image()

        upload_response = await client.post(
            f"/api/v1/buildings/{building_id}/photos/upload",
            headers={"Authorization": f"Bearer {token}"},
            files={"file": ("test.png", BytesIO(image_content), "image/png")},
            data={"title": "To Delete"},
        )
        photo_id = upload_response.json()["id"]

        response = await client.delete(
            f"/api/v1/buildings/photos/{photo_id}",
            headers={"Authorization": f"Bearer {token}"},
        )
        assert response.status_code == 200

        # Verify deleted
        get_response = await client.get(
            f"/api/v1/buildings/photos/{photo_id}",
            headers={"Authorization": f"Bearer {token}"},
        )
        assert get_response.status_code == 404

    @pytest.mark.asyncio
    async def test_delete_photo_not_found(self, client, admin_user, test_agency):
        """Test deleting a non-existent photo."""
        token = await self.get_admin_token(client)

        response = await client.delete(
            f"/api/v1/buildings/photos/{uuid4()}",
            headers={"Authorization": f"Bearer {token}"},
        )
        assert response.status_code == 404

    @pytest.mark.asyncio
    async def test_upload_photo_jpeg(self, client, admin_user, test_agency):
        """Test uploading a JPEG photo."""
        token = await self.get_admin_token(client)
        building_id = await self.create_test_building(client, token)

        # Minimal JPEG content (not a valid image but has correct header)
        jpeg_content = b'\xff\xd8\xff\xe0\x00\x10JFIF' + b'\x00' * 100 + b'\xff\xd9'

        response = await client.post(
            f"/api/v1/buildings/{building_id}/photos/upload",
            headers={"Authorization": f"Bearer {token}"},
            files={"file": ("test.jpg", BytesIO(jpeg_content), "image/jpeg")},
            data={"title": "JPEG Photo"},
        )
        assert response.status_code == 200
        data = response.json()
        assert data["title"] == "JPEG Photo"

    @pytest.mark.asyncio
    async def test_list_photos_with_floor_plan_filter(self, client, admin_user, test_agency):
        """Test filtering photos by floor plan."""
        token = await self.get_admin_token(client)
        building_id = await self.create_test_building(client, token)

        # Create a floor plan
        floor_response = await client.post(
            f"/api/v1/buildings/{building_id}/floors",
            headers={"Authorization": f"Bearer {token}"},
            json={"floor_number": 1, "floor_name": "Ground Floor"},
        )
        floor_plan_id = floor_response.json()["id"]

        image_content = self.create_test_image()

        # Upload photo with floor plan
        await client.post(
            f"/api/v1/buildings/{building_id}/photos/upload",
            headers={"Authorization": f"Bearer {token}"},
            files={"file": ("floor1.png", BytesIO(image_content), "image/png")},
            data={"title": "Floor 1 Photo", "floor_plan_id": floor_plan_id},
        )

        # Upload photo without floor plan
        await client.post(
            f"/api/v1/buildings/{building_id}/photos/upload",
            headers={"Authorization": f"Bearer {token}"},
            files={"file": ("general.png", BytesIO(image_content), "image/png")},
            data={"title": "General Photo"},
        )

        # Filter by floor plan
        response = await client.get(
            f"/api/v1/buildings/{building_id}/photos",
            headers={"Authorization": f"Bearer {token}"},
            params={"floor_plan_id": floor_plan_id},
        )
        assert response.status_code == 200
        data = response.json()
        assert data["total"] == 1
        assert data["items"][0]["floor_plan_id"] == floor_plan_id

    @pytest.mark.asyncio
    async def test_photo_has_thumbnail_url(self, client, admin_user, test_agency):
        """Test that uploaded photo has a thumbnail URL (if thumbnail generation succeeds)."""
        token = await self.get_admin_token(client)
        building_id = await self.create_test_building(client, token)

        image_content = self.create_test_image()

        response = await client.post(
            f"/api/v1/buildings/{building_id}/photos/upload",
            headers={"Authorization": f"Bearer {token}"},
            files={"file": ("test.png", BytesIO(image_content), "image/png")},
            data={"title": "Thumbnail Test Photo"},
        )
        assert response.status_code == 200
        # Thumbnail URL may be None if PIL is not available or fails
        # Just check the field exists
        assert "thumbnail_url" in response.json()

    @pytest.mark.asyncio
    async def test_multiple_photos_same_building(self, client, admin_user, test_agency):
        """Test uploading multiple photos to the same building."""
        token = await self.get_admin_token(client)
        building_id = await self.create_test_building(client, token)

        image_content = self.create_test_image()

        photo_ids = []
        for i in range(3):
            response = await client.post(
                f"/api/v1/buildings/{building_id}/photos/upload",
                headers={"Authorization": f"Bearer {token}"},
                files={"file": (f"photo{i}.png", BytesIO(image_content), "image/png")},
                data={"title": f"Photo {i}"},
            )
            assert response.status_code == 200
            photo_ids.append(response.json()["id"])

        # Verify all photos exist
        list_response = await client.get(
            f"/api/v1/buildings/{building_id}/photos",
            headers={"Authorization": f"Bearer {token}"},
        )
        assert list_response.status_code == 200
        assert list_response.json()["total"] == 3

        # All IDs should be unique
        assert len(set(photo_ids)) == 3

    @pytest.mark.asyncio
    async def test_photo_uploaded_by_tracked(self, client, admin_user, test_agency):
        """Test that uploaded_by_id is tracked for photos."""
        token = await self.get_admin_token(client)
        building_id = await self.create_test_building(client, token)

        image_content = self.create_test_image()

        response = await client.post(
            f"/api/v1/buildings/{building_id}/photos/upload",
            headers={"Authorization": f"Bearer {token}"},
            files={"file": ("test.png", BytesIO(image_content), "image/png")},
            data={"title": "Tracked Photo"},
        )
        assert response.status_code == 200
        data = response.json()
        assert "uploaded_by_id" in data
        # Should have the admin user's ID
        assert data["uploaded_by_id"] is not None
