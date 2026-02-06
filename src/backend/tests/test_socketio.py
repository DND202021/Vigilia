"""Tests for SocketIO service."""

import uuid
import pytest
from unittest.mock import Mock, AsyncMock, patch

from app.services import socketio


@pytest.mark.asyncio
class TestSocketIOService:
    """Test suite for SocketIO service functions."""

    async def test_emit_incident_created(self):
        """Test emitting incident created event."""
        with patch.object(socketio, 'sio') as mock_sio:
            mock_sio.emit = AsyncMock()

            incident_data = {
                "id": str(uuid.uuid4()),
                "incident_number": "INC-001",
                "title": "Test Incident",
            }

            await socketio.emit_incident_created(incident_data)

            mock_sio.emit.assert_called_once()

    async def test_emit_incident_updated(self):
        """Test emitting incident updated event."""
        with patch.object(socketio, 'sio') as mock_sio:
            mock_sio.emit = AsyncMock()

            incident_data = {
                "id": str(uuid.uuid4()),
                "status": "on_scene",
            }

            await socketio.emit_incident_updated(incident_data)

            mock_sio.emit.assert_called_once()

    async def test_emit_alert_created(self):
        """Test emitting alert created event."""
        with patch.object(socketio, 'sio') as mock_sio:
            mock_sio.emit = AsyncMock()

            alert_data = {
                "id": str(uuid.uuid4()),
                "title": "Test Alert",
            }

            await socketio.emit_alert_created(alert_data)

            mock_sio.emit.assert_called_once()

    async def test_emit_alert_updated(self):
        """Test emitting alert updated event."""
        with patch.object(socketio, 'sio') as mock_sio:
            mock_sio.emit = AsyncMock()

            alert_data = {
                "id": str(uuid.uuid4()),
                "severity": "critical",
            }

            await socketio.emit_alert_updated(alert_data)

            mock_sio.emit.assert_called_once()

    async def test_emit_resource_updated(self):
        """Test emitting resource updated event."""
        with patch.object(socketio, 'sio') as mock_sio:
            mock_sio.emit = AsyncMock()

            resource_data = {
                "id": str(uuid.uuid4()),
                "status": "en_route",
            }

            await socketio.emit_resource_updated(resource_data)

            mock_sio.emit.assert_called_once()
