"""File storage service for managing uploaded files."""

import os
import uuid
import hashlib
import logging
from pathlib import Path
from datetime import datetime
from typing import BinaryIO

from PIL import Image
import io

logger = logging.getLogger(__name__)


class FileStorageError(Exception):
    """File storage related errors."""
    pass


class FileStorageService:
    """Service for managing file uploads and storage."""

    # Allowed file types for floor plans
    ALLOWED_FLOOR_PLAN_TYPES = {
        'image/png': 'png',
        'image/jpeg': 'jpg',
        'image/jpg': 'jpg',
        'application/pdf': 'pdf',
        'image/svg+xml': 'svg',
        # DWG files (AutoCAD)
        'application/acad': 'dwg',
        'application/x-acad': 'dwg',
        'application/x-autocad': 'dwg',
        'application/dwg': 'dwg',
        'image/vnd.dwg': 'dwg',
        'image/x-dwg': 'dwg',
    }

    # Maximum file size (50MB)
    MAX_FILE_SIZE = 50 * 1024 * 1024

    # Thumbnail settings
    THUMBNAIL_SIZE = (300, 300)

    def __init__(self, base_path: str = "/data/buildings"):
        """Initialize file storage service.

        Args:
            base_path: Base directory for file storage
        """
        self.base_path = Path(base_path)
        self._ensure_base_directory()
        logger.info(f"FileStorageService initialized with base_path: {self.base_path.resolve()}")

    def _ensure_base_directory(self) -> None:
        """Ensure the base storage directory exists and is writable."""
        try:
            self.base_path.mkdir(parents=True, exist_ok=True)
            # Check if directory is writable
            if not os.access(self.base_path, os.W_OK):
                logger.error(f"Base directory is not writable: {self.base_path}")
        except PermissionError as e:
            logger.error(f"Cannot create base directory {self.base_path}: {e}")

    def _get_building_path(self, building_id: uuid.UUID) -> Path:
        """Get the storage path for a building."""
        path = self.base_path / str(building_id) / "floor_plans"
        try:
            path.mkdir(parents=True, exist_ok=True)
            logger.debug(f"Building path ready: {path}")
        except PermissionError as e:
            logger.error(f"Cannot create building directory {path}: {e}")
            raise FileStorageError(f"Cannot create storage directory: permission denied")
        return path

    def _generate_filename(
        self,
        floor_number: int,
        extension: str,
        suffix: str = "",
    ) -> str:
        """Generate a unique filename for a floor plan."""
        timestamp = datetime.utcnow().strftime("%Y%m%d_%H%M%S")
        unique_id = uuid.uuid4().hex[:8]
        suffix_str = f"_{suffix}" if suffix else ""
        return f"floor_{floor_number}{suffix_str}_{timestamp}_{unique_id}.{extension}"

    def validate_file(
        self,
        content_type: str,
        file_size: int,
    ) -> str:
        """Validate file type and size.

        Args:
            content_type: MIME type of the file
            file_size: Size of the file in bytes

        Returns:
            File extension

        Raises:
            FileStorageError: If validation fails
        """
        # Check file type
        if content_type not in self.ALLOWED_FLOOR_PLAN_TYPES:
            raise FileStorageError(
                f"Invalid file type: {content_type}. "
                f"Allowed types: PNG, JPG, PDF, SVG, DWG"
            )

        # Check file size
        if file_size > self.MAX_FILE_SIZE:
            max_mb = self.MAX_FILE_SIZE / (1024 * 1024)
            raise FileStorageError(
                f"File too large. Maximum size is {max_mb:.0f}MB"
            )

        return self.ALLOWED_FLOOR_PLAN_TYPES[content_type]

    async def save_floor_plan(
        self,
        building_id: uuid.UUID,
        floor_number: int,
        file_content: bytes,
        content_type: str,
    ) -> tuple[str, str | None, str]:
        """Save a floor plan file.

        Args:
            building_id: UUID of the building
            floor_number: Floor number for this plan
            file_content: Binary content of the file
            content_type: MIME type of the file

        Returns:
            Tuple of (file_url, thumbnail_url, file_type)
        """
        # Validate file
        extension = self.validate_file(content_type, len(file_content))

        # Get storage path
        building_path = self._get_building_path(building_id)

        # Generate filename
        filename = self._generate_filename(floor_number, extension)
        file_path = building_path / filename

        # Save file
        try:
            with open(file_path, 'wb') as f:
                f.write(file_content)
                f.flush()
                os.fsync(f.fileno())  # Force write to disk
        except PermissionError as e:
            logger.error(f"Permission denied writing file {file_path}: {e}")
            raise FileStorageError(f"Cannot write file: permission denied")
        except OSError as e:
            logger.error(f"OS error writing file {file_path}: {e}")
            raise FileStorageError(f"Cannot write file: {e}")

        # Verify file was saved
        if file_path.exists():
            file_size = file_path.stat().st_size
            logger.info(f"Floor plan saved successfully: {file_path} ({file_size} bytes)")
        else:
            logger.error(f"Floor plan file NOT found after save: {file_path}")
            raise FileStorageError("File save failed: file not found after write")

        # Generate thumbnail for images
        thumbnail_url = None
        if extension in ('png', 'jpg', 'jpeg'):
            thumbnail_url = await self._generate_thumbnail(
                building_id,
                floor_number,
                file_content,
                extension,
            )

        # Generate URL (relative path for API serving)
        file_url = f"/api/v1/buildings/{building_id}/floor-plans/files/{filename}"

        return file_url, thumbnail_url, extension

    async def _generate_thumbnail(
        self,
        building_id: uuid.UUID,
        floor_number: int,
        file_content: bytes,
        extension: str,
    ) -> str | None:
        """Generate a thumbnail for an image file."""
        try:
            # Open image
            img = Image.open(io.BytesIO(file_content))

            # Convert to RGB if necessary (for PNG with transparency)
            if img.mode in ('RGBA', 'P'):
                img = img.convert('RGB')

            # Create thumbnail
            img.thumbnail(self.THUMBNAIL_SIZE, Image.Resampling.LANCZOS)

            # Save thumbnail
            building_path = self._get_building_path(building_id)
            thumb_filename = self._generate_filename(floor_number, 'jpg', 'thumb')
            thumb_path = building_path / thumb_filename

            img.save(thumb_path, 'JPEG', quality=85)

            return f"/api/v1/buildings/{building_id}/floor-plans/files/{thumb_filename}"

        except Exception as e:
            # Log error but don't fail - thumbnail is optional
            print(f"Failed to generate thumbnail: {e}")
            return None

    def get_file_path(
        self,
        building_id: uuid.UUID,
        filename: str,
    ) -> Path | None:
        """Get the full path to a stored file.

        Args:
            building_id: UUID of the building
            filename: Name of the file

        Returns:
            Full path to the file, or None if not found
        """
        building_path = self._get_building_path(building_id)
        file_path = building_path / filename

        logger.info(f"Looking for file: {file_path}")

        # Security: ensure the path is within the building directory
        try:
            file_path.resolve().relative_to(building_path.resolve())
        except ValueError:
            logger.warning(f"Path traversal attempt detected: {filename}")
            return None

        if file_path.exists():
            logger.info(f"File found: {file_path}")
            return file_path

        # Debug: list files in directory
        if building_path.exists():
            files = list(building_path.iterdir())
            logger.warning(f"File NOT found: {file_path}. Directory contains {len(files)} files: {[f.name for f in files[:10]]}")
        else:
            logger.warning(f"Building directory does not exist: {building_path}")

        return None

    def delete_file(
        self,
        building_id: uuid.UUID,
        filename: str,
    ) -> bool:
        """Delete a stored file.

        Args:
            building_id: UUID of the building
            filename: Name of the file to delete

        Returns:
            True if deleted, False if not found
        """
        file_path = self.get_file_path(building_id, filename)
        if file_path:
            file_path.unlink()
            return True
        return False

    def delete_building_files(self, building_id: uuid.UUID) -> int:
        """Delete all files for a building.

        Args:
            building_id: UUID of the building

        Returns:
            Number of files deleted
        """
        building_path = self.base_path / str(building_id)
        if not building_path.exists():
            return 0

        count = 0
        for file_path in building_path.rglob('*'):
            if file_path.is_file():
                file_path.unlink()
                count += 1

        # Remove empty directories
        for dir_path in sorted(building_path.rglob('*'), reverse=True):
            if dir_path.is_dir():
                try:
                    dir_path.rmdir()
                except OSError:
                    pass

        try:
            building_path.rmdir()
        except OSError:
            pass

        return count

    def get_content_type(self, filename: str) -> str:
        """Get the content type for a filename."""
        ext = filename.rsplit('.', 1)[-1].lower()
        content_types = {
            'png': 'image/png',
            'jpg': 'image/jpeg',
            'jpeg': 'image/jpeg',
            'pdf': 'application/pdf',
            'svg': 'image/svg+xml',
            'dwg': 'application/octet-stream',
        }
        return content_types.get(ext, 'application/octet-stream')


# Global instance with configurable path
_file_storage: FileStorageService | None = None


def get_file_storage() -> FileStorageService:
    """Get the file storage service instance."""
    global _file_storage
    if _file_storage is None:
        # Use environment variable or default
        base_path = os.environ.get('FILE_STORAGE_PATH', '/data/buildings')
        _file_storage = FileStorageService(base_path)
    return _file_storage
