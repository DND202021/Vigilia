"""Tests for Building Documents API endpoints."""

import pytest
from uuid import uuid4
from io import BytesIO

from app.models.document import BuildingDocument, DocumentCategory


class TestDocumentsAPI:
    """Tests for document management endpoints."""

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
                "name": "Document Test Building",
                "street_name": "Test Street",
                "city": "Montreal",
                "province_state": "Quebec",
                "latitude": 45.5017,
                "longitude": -73.5673,
            },
        )
        return response.json()["id"]

    @pytest.mark.asyncio
    async def test_list_documents_empty(self, client, admin_user, test_agency):
        """Test listing documents for building with no documents."""
        token = await self.get_admin_token(client)
        building_id = await self.create_test_building(client, token)

        response = await client.get(
            f"/api/v1/buildings/{building_id}/documents",
            headers={"Authorization": f"Bearer {token}"},
        )
        assert response.status_code == 200
        data = response.json()
        assert data["total"] == 0
        assert data["items"] == []

    @pytest.mark.asyncio
    async def test_upload_document(self, client, admin_user, test_agency):
        """Test uploading a document."""
        token = await self.get_admin_token(client)
        building_id = await self.create_test_building(client, token)

        pdf_content = b"%PDF-1.4\ntest content\n%%EOF"

        response = await client.post(
            f"/api/v1/buildings/{building_id}/documents/upload",
            headers={"Authorization": f"Bearer {token}"},
            files={"file": ("test.pdf", BytesIO(pdf_content), "application/pdf")},
            data={
                "title": "Test Document",
                "category": "pre_plan",
                "description": "Test description",
            },
        )
        assert response.status_code == 200
        data = response.json()
        assert data["title"] == "Test Document"
        assert data["category"] == "pre_plan"
        assert data["file_type"] == "pdf"
        assert data["description"] == "Test description"
        assert "id" in data

    @pytest.mark.asyncio
    async def test_upload_document_building_not_found(self, client, admin_user, test_agency):
        """Test uploading document to non-existent building."""
        token = await self.get_admin_token(client)
        pdf_content = b"%PDF-1.4\ntest\n%%EOF"

        response = await client.post(
            f"/api/v1/buildings/{uuid4()}/documents/upload",
            headers={"Authorization": f"Bearer {token}"},
            files={"file": ("test.pdf", BytesIO(pdf_content), "application/pdf")},
            data={"title": "Test", "category": "other"},
        )
        assert response.status_code == 404

    @pytest.mark.asyncio
    async def test_upload_document_no_auth(self, client, admin_user, test_agency):
        """Test uploading document without authentication."""
        token = await self.get_admin_token(client)
        building_id = await self.create_test_building(client, token)

        pdf_content = b"%PDF-1.4\ntest\n%%EOF"

        response = await client.post(
            f"/api/v1/buildings/{building_id}/documents/upload",
            files={"file": ("test.pdf", BytesIO(pdf_content), "application/pdf")},
            data={"title": "Test", "category": "other"},
        )
        assert response.status_code == 401

    @pytest.mark.asyncio
    async def test_list_documents_with_category_filter(self, client, admin_user, test_agency):
        """Test filtering documents by category."""
        token = await self.get_admin_token(client)
        building_id = await self.create_test_building(client, token)

        pdf_content = b"%PDF-1.4\ntest\n%%EOF"

        # Upload two documents with different categories
        await client.post(
            f"/api/v1/buildings/{building_id}/documents/upload",
            headers={"Authorization": f"Bearer {token}"},
            files={"file": ("doc1.pdf", BytesIO(pdf_content), "application/pdf")},
            data={"title": "Pre-Plan Doc", "category": "pre_plan"},
        )
        await client.post(
            f"/api/v1/buildings/{building_id}/documents/upload",
            headers={"Authorization": f"Bearer {token}"},
            files={"file": ("doc2.pdf", BytesIO(pdf_content), "application/pdf")},
            data={"title": "Permit Doc", "category": "permit"},
        )

        # Filter by pre_plan
        response = await client.get(
            f"/api/v1/buildings/{building_id}/documents",
            headers={"Authorization": f"Bearer {token}"},
            params={"category": "pre_plan"},
        )
        assert response.status_code == 200
        data = response.json()
        assert data["total"] == 1
        assert data["items"][0]["category"] == "pre_plan"

    @pytest.mark.asyncio
    async def test_list_documents_pagination(self, client, admin_user, test_agency):
        """Test document listing pagination."""
        token = await self.get_admin_token(client)
        building_id = await self.create_test_building(client, token)

        pdf_content = b"%PDF-1.4\ntest\n%%EOF"

        # Upload multiple documents
        for i in range(5):
            await client.post(
                f"/api/v1/buildings/{building_id}/documents/upload",
                headers={"Authorization": f"Bearer {token}"},
                files={"file": (f"doc{i}.pdf", BytesIO(pdf_content), "application/pdf")},
                data={"title": f"Document {i}", "category": "other"},
            )

        # Get first page with page_size=2
        response = await client.get(
            f"/api/v1/buildings/{building_id}/documents",
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
    async def test_get_document(self, client, admin_user, test_agency):
        """Test getting a single document."""
        token = await self.get_admin_token(client)
        building_id = await self.create_test_building(client, token)

        pdf_content = b"%PDF-1.4\ntest\n%%EOF"

        upload_response = await client.post(
            f"/api/v1/buildings/{building_id}/documents/upload",
            headers={"Authorization": f"Bearer {token}"},
            files={"file": ("test.pdf", BytesIO(pdf_content), "application/pdf")},
            data={"title": "Test Doc", "category": "other"},
        )
        doc_id = upload_response.json()["id"]

        response = await client.get(
            f"/api/v1/buildings/documents/{doc_id}",
            headers={"Authorization": f"Bearer {token}"},
        )
        assert response.status_code == 200
        assert response.json()["title"] == "Test Doc"
        assert response.json()["id"] == doc_id

    @pytest.mark.asyncio
    async def test_get_document_not_found(self, client, admin_user, test_agency):
        """Test getting a non-existent document."""
        token = await self.get_admin_token(client)

        response = await client.get(
            f"/api/v1/buildings/documents/{uuid4()}",
            headers={"Authorization": f"Bearer {token}"},
        )
        assert response.status_code == 404

    @pytest.mark.asyncio
    async def test_update_document(self, client, admin_user, test_agency):
        """Test updating a document."""
        token = await self.get_admin_token(client)
        building_id = await self.create_test_building(client, token)

        pdf_content = b"%PDF-1.4\ntest\n%%EOF"

        upload_response = await client.post(
            f"/api/v1/buildings/{building_id}/documents/upload",
            headers={"Authorization": f"Bearer {token}"},
            files={"file": ("test.pdf", BytesIO(pdf_content), "application/pdf")},
            data={"title": "Original Title", "category": "other"},
        )
        doc_id = upload_response.json()["id"]

        response = await client.patch(
            f"/api/v1/buildings/documents/{doc_id}",
            headers={"Authorization": f"Bearer {token}"},
            params={"title": "Updated Title", "category": "inspection"},
        )
        assert response.status_code == 200
        assert response.json()["title"] == "Updated Title"
        assert response.json()["category"] == "inspection"

    @pytest.mark.asyncio
    async def test_update_document_description(self, client, admin_user, test_agency):
        """Test updating document description."""
        token = await self.get_admin_token(client)
        building_id = await self.create_test_building(client, token)

        pdf_content = b"%PDF-1.4\ntest\n%%EOF"

        upload_response = await client.post(
            f"/api/v1/buildings/{building_id}/documents/upload",
            headers={"Authorization": f"Bearer {token}"},
            files={"file": ("test.pdf", BytesIO(pdf_content), "application/pdf")},
            data={"title": "Test Doc", "category": "other"},
        )
        doc_id = upload_response.json()["id"]

        response = await client.patch(
            f"/api/v1/buildings/documents/{doc_id}",
            headers={"Authorization": f"Bearer {token}"},
            params={"description": "New description added"},
        )
        assert response.status_code == 200
        assert response.json()["description"] == "New description added"

    @pytest.mark.asyncio
    async def test_update_document_not_found(self, client, admin_user, test_agency):
        """Test updating a non-existent document."""
        token = await self.get_admin_token(client)

        response = await client.patch(
            f"/api/v1/buildings/documents/{uuid4()}",
            headers={"Authorization": f"Bearer {token}"},
            params={"title": "New Title"},
        )
        assert response.status_code == 404

    @pytest.mark.asyncio
    async def test_delete_document(self, client, admin_user, test_agency):
        """Test deleting a document."""
        token = await self.get_admin_token(client)
        building_id = await self.create_test_building(client, token)

        pdf_content = b"%PDF-1.4\ntest\n%%EOF"

        upload_response = await client.post(
            f"/api/v1/buildings/{building_id}/documents/upload",
            headers={"Authorization": f"Bearer {token}"},
            files={"file": ("test.pdf", BytesIO(pdf_content), "application/pdf")},
            data={"title": "To Delete", "category": "other"},
        )
        doc_id = upload_response.json()["id"]

        response = await client.delete(
            f"/api/v1/buildings/documents/{doc_id}",
            headers={"Authorization": f"Bearer {token}"},
        )
        assert response.status_code == 200

        # Verify deleted
        get_response = await client.get(
            f"/api/v1/buildings/documents/{doc_id}",
            headers={"Authorization": f"Bearer {token}"},
        )
        assert get_response.status_code == 404

    @pytest.mark.asyncio
    async def test_delete_document_not_found(self, client, admin_user, test_agency):
        """Test deleting a non-existent document."""
        token = await self.get_admin_token(client)

        response = await client.delete(
            f"/api/v1/buildings/documents/{uuid4()}",
            headers={"Authorization": f"Bearer {token}"},
        )
        assert response.status_code == 404

    @pytest.mark.asyncio
    async def test_upload_document_various_categories(self, client, admin_user, test_agency):
        """Test uploading documents with all supported categories."""
        token = await self.get_admin_token(client)
        building_id = await self.create_test_building(client, token)

        pdf_content = b"%PDF-1.4\ntest\n%%EOF"
        categories = ["pre_plan", "floor_plan", "permit", "inspection", "manual", "other"]

        for category in categories:
            response = await client.post(
                f"/api/v1/buildings/{building_id}/documents/upload",
                headers={"Authorization": f"Bearer {token}"},
                files={"file": (f"{category}.pdf", BytesIO(pdf_content), "application/pdf")},
                data={"title": f"Document {category}", "category": category},
            )
            assert response.status_code == 200
            assert response.json()["category"] == category

    @pytest.mark.asyncio
    async def test_upload_document_default_category(self, client, admin_user, test_agency):
        """Test uploading document without specifying category uses 'other' default."""
        token = await self.get_admin_token(client)
        building_id = await self.create_test_building(client, token)

        pdf_content = b"%PDF-1.4\ntest\n%%EOF"

        # Upload without category
        response = await client.post(
            f"/api/v1/buildings/{building_id}/documents/upload",
            headers={"Authorization": f"Bearer {token}"},
            files={"file": ("test.pdf", BytesIO(pdf_content), "application/pdf")},
            data={"title": "No Category Doc"},
        )
        assert response.status_code == 200
        assert response.json()["category"] == "other"

    @pytest.mark.asyncio
    async def test_document_file_size_recorded(self, client, admin_user, test_agency):
        """Test that uploaded document file size is recorded."""
        token = await self.get_admin_token(client)
        building_id = await self.create_test_building(client, token)

        pdf_content = b"%PDF-1.4\n" + b"x" * 1000 + b"\n%%EOF"

        response = await client.post(
            f"/api/v1/buildings/{building_id}/documents/upload",
            headers={"Authorization": f"Bearer {token}"},
            files={"file": ("test.pdf", BytesIO(pdf_content), "application/pdf")},
            data={"title": "Size Test Doc", "category": "other"},
        )
        assert response.status_code == 200
        assert response.json()["file_size"] > 0
        assert response.json()["file_size"] == len(pdf_content)
