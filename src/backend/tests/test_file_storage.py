"""Tests for FileStorageService."""

import os
import tempfile
from pathlib import Path
from unittest.mock import patch
import uuid

import pytest

from app.services.file_storage import FileStorageService, FileStorageError


class TestFileStorageService:
    """Tests for FileStorageService."""

    @pytest.fixture
    def temp_storage_dir(self):
        """Create a temporary storage directory."""
        with tempfile.TemporaryDirectory() as tmpdir:
            yield tmpdir

    @pytest.fixture
    def storage_service(self, temp_storage_dir):
        """Create a FileStorageService with temp directory."""
        service = FileStorageService(base_path=temp_storage_dir)
        return service

    # ==================== File Type Validation ====================

    def test_allowed_floor_plan_types(self, storage_service):
        """Verify all expected file types are allowed."""
        expected_types = ['image/png', 'image/jpeg', 'image/jpg', 'application/pdf', 'image/svg+xml']
        for content_type in expected_types:
            assert content_type in storage_service.ALLOWED_FLOOR_PLAN_TYPES

    def test_get_file_extension_png(self, storage_service):
        """Test getting file extension for PNG."""
        ext = storage_service.ALLOWED_FLOOR_PLAN_TYPES.get('image/png')
        assert ext == 'png'

    def test_get_file_extension_pdf(self, storage_service):
        """Test getting file extension for PDF."""
        ext = storage_service.ALLOWED_FLOOR_PLAN_TYPES.get('application/pdf')
        assert ext == 'pdf'

    def test_get_file_extension_svg(self, storage_service):
        """Test getting file extension for SVG."""
        ext = storage_service.ALLOWED_FLOOR_PLAN_TYPES.get('image/svg+xml')
        assert ext == 'svg'

    # ==================== Content Type Detection ====================

    def test_get_content_type_png(self, storage_service):
        """Test getting content type for PNG file."""
        content_type = storage_service.get_content_type('image.png')
        assert content_type == 'image/png'

    def test_get_content_type_jpg(self, storage_service):
        """Test getting content type for JPG file."""
        content_type = storage_service.get_content_type('image.jpg')
        assert content_type == 'image/jpeg'

    def test_get_content_type_pdf(self, storage_service):
        """Test getting content type for PDF file."""
        content_type = storage_service.get_content_type('document.pdf')
        assert content_type == 'application/pdf'

    def test_get_content_type_svg(self, storage_service):
        """Test getting content type for SVG file."""
        content_type = storage_service.get_content_type('diagram.svg')
        assert content_type == 'image/svg+xml'

    def test_get_content_type_unknown(self, storage_service):
        """Test getting content type for unknown file type."""
        content_type = storage_service.get_content_type('file.xyz')
        assert content_type == 'application/octet-stream'

    # ==================== File Size Validation ====================

    def test_max_file_size(self, storage_service):
        """Test maximum file size is 50MB."""
        assert storage_service.MAX_FILE_SIZE == 50 * 1024 * 1024

    # ==================== Thumbnail Configuration ====================

    def test_thumbnail_size(self, storage_service):
        """Test thumbnail size configuration."""
        assert storage_service.THUMBNAIL_SIZE == (300, 300)

    # ==================== File Validation ====================

    def test_validate_file_valid_png(self, storage_service):
        """Test validation passes for valid PNG."""
        ext = storage_service.validate_file('image/png', 1000)
        assert ext == 'png'

    def test_validate_file_valid_pdf(self, storage_service):
        """Test validation passes for valid PDF."""
        ext = storage_service.validate_file('application/pdf', 1000)
        assert ext == 'pdf'

    def test_validate_file_invalid_type(self, storage_service):
        """Test validation fails for invalid type."""
        with pytest.raises(FileStorageError, match='Invalid file type'):
            storage_service.validate_file('application/exe', 1000)

    def test_validate_file_too_large(self, storage_service):
        """Test validation fails for oversized file."""
        with pytest.raises(FileStorageError, match='File too large'):
            storage_service.validate_file('image/png', 60 * 1024 * 1024)  # 60MB

    def test_validate_file_zero_size(self, storage_service):
        """Test validation passes for zero size file (size check only for max)."""
        # Note: validate_file only checks max size, not empty files
        ext = storage_service.validate_file('image/png', 0)
        assert ext == 'png'

    # ==================== Save Floor Plan ====================

    @pytest.mark.asyncio
    async def test_save_floor_plan_pdf(self, storage_service):
        """Test saving a PDF floor plan."""
        building_id = uuid.uuid4()
        pdf_data = b'%PDF-1.4\n1 0 obj<</Type/Catalog/Pages 2 0 R>>endobj\n%%EOF'

        file_url, thumb_url, file_type = await storage_service.save_floor_plan(
            building_id=building_id,
            floor_number=0,
            file_content=pdf_data,
            content_type='application/pdf'
        )

        assert file_url is not None
        assert 'floor_0' in file_url
        assert file_url.endswith('.pdf')
        assert file_type == 'pdf'
        assert thumb_url is None  # PDFs don't get thumbnails

    @pytest.mark.asyncio
    async def test_save_floor_plan_svg(self, storage_service):
        """Test saving an SVG floor plan."""
        building_id = uuid.uuid4()
        svg_data = b'<svg xmlns="http://www.w3.org/2000/svg"><rect width="100" height="100"/></svg>'

        file_url, thumb_url, file_type = await storage_service.save_floor_plan(
            building_id=building_id,
            floor_number=-1,  # Basement
            file_content=svg_data,
            content_type='image/svg+xml'
        )

        assert file_url is not None
        assert 'floor_-1' in file_url
        assert file_url.endswith('.svg')
        assert file_type == 'svg'

    @pytest.mark.asyncio
    async def test_save_floor_plan_invalid_type(self, storage_service):
        """Test saving with invalid content type raises error."""
        building_id = uuid.uuid4()

        with pytest.raises(FileStorageError, match='Invalid file type'):
            await storage_service.save_floor_plan(
                building_id=building_id,
                floor_number=1,
                file_content=b'test data',
                content_type='application/exe'
            )

    @pytest.mark.asyncio
    async def test_save_floor_plan_too_large(self, storage_service):
        """Test saving file that exceeds size limit raises error."""
        building_id = uuid.uuid4()
        # Create content larger than MAX_FILE_SIZE
        large_content = b'x' * (storage_service.MAX_FILE_SIZE + 1)

        with pytest.raises(FileStorageError, match='File too large'):
            await storage_service.save_floor_plan(
                building_id=building_id,
                floor_number=1,
                file_content=large_content,
                content_type='image/png'
            )

    @pytest.mark.asyncio
    async def test_save_floor_plan_empty(self, storage_service):
        """Test saving empty file still creates file (no validation for empty)."""
        building_id = uuid.uuid4()
        # Empty files are allowed through - they just won't work as images
        file_url, thumb_url, file_type = await storage_service.save_floor_plan(
            building_id=building_id,
            floor_number=1,
            file_content=b'',
            content_type='image/png'
        )
        assert file_url is not None
        assert file_type == 'png'

    # ==================== Get File Path ====================

    @pytest.mark.asyncio
    async def test_get_file_path_exists(self, storage_service):
        """Test get_file_path returns path for existing file."""
        building_id = uuid.uuid4()
        pdf_data = b'%PDF-1.4\ntest content\n%%EOF'

        file_url, _, _ = await storage_service.save_floor_plan(
            building_id=building_id,
            floor_number=1,
            file_content=pdf_data,
            content_type='application/pdf'
        )

        filename = os.path.basename(file_url)
        file_path = storage_service.get_file_path(building_id, filename)

        assert file_path is not None
        assert file_path.exists()

    def test_get_file_path_not_found(self, storage_service):
        """Test get_file_path returns None for non-existent file."""
        building_id = uuid.uuid4()
        # Building directory needs to exist
        building_path = storage_service._get_building_path(building_id)

        file_path = storage_service.get_file_path(building_id, 'nonexistent.pdf')
        assert file_path is None

    # ==================== Delete File ====================

    @pytest.mark.asyncio
    async def test_delete_file(self, storage_service):
        """Test deleting a file."""
        building_id = uuid.uuid4()
        pdf_data = b'%PDF-1.4\ntest content\n%%EOF'

        file_url, _, _ = await storage_service.save_floor_plan(
            building_id=building_id,
            floor_number=1,
            file_content=pdf_data,
            content_type='application/pdf'
        )

        filename = os.path.basename(file_url)

        # Verify file exists
        file_path = storage_service.get_file_path(building_id, filename)
        assert file_path is not None

        # Delete the file
        result = storage_service.delete_file(building_id, filename)
        assert result is True

        # Verify file is deleted
        file_path = storage_service.get_file_path(building_id, filename)
        assert file_path is None

    def test_delete_file_not_found(self, storage_service):
        """Test deleting non-existent file returns False."""
        building_id = uuid.uuid4()
        # Create the building path
        storage_service._get_building_path(building_id)

        result = storage_service.delete_file(building_id, 'nonexistent.pdf')
        assert result is False

    # ==================== Delete Building Files ====================

    @pytest.mark.asyncio
    async def test_delete_building_files(self, storage_service):
        """Test deleting all files for a building."""
        building_id = uuid.uuid4()
        pdf_data = b'%PDF-1.4\ntest content\n%%EOF'

        # Save multiple files
        await storage_service.save_floor_plan(
            building_id=building_id,
            floor_number=0,
            file_content=pdf_data,
            content_type='application/pdf'
        )
        await storage_service.save_floor_plan(
            building_id=building_id,
            floor_number=1,
            file_content=pdf_data,
            content_type='application/pdf'
        )

        # Delete all files
        count = storage_service.delete_building_files(building_id)
        assert count == 2

    def test_delete_building_files_empty(self, storage_service):
        """Test deleting files from non-existent building returns 0."""
        building_id = uuid.uuid4()
        count = storage_service.delete_building_files(building_id)
        assert count == 0


class TestFileStorageServiceHelpers:
    """Tests for helper functions in file storage."""

    def test_get_file_storage_factory(self):
        """Test get_file_storage returns a FileStorageService instance."""
        with tempfile.TemporaryDirectory() as tmpdir:
            with patch.dict(os.environ, {'FILE_STORAGE_PATH': tmpdir}):
                # Reset the global instance
                import app.services.file_storage as fs
                fs._file_storage = None

                from app.services.file_storage import get_file_storage
                service = get_file_storage()
                assert isinstance(service, FileStorageService)

                # Reset again after test
                fs._file_storage = None

    def test_content_type_mapping_complete(self):
        """Test all content type mappings have extensions."""
        with tempfile.TemporaryDirectory() as tmpdir:
            service = FileStorageService(base_path=tmpdir)
            for content_type, extension in service.ALLOWED_FLOOR_PLAN_TYPES.items():
                assert extension is not None
                assert len(extension) > 0
                assert '.' not in extension  # Extension without dot
