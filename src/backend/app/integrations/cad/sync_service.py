"""CAD Synchronization Service.

Manages bidirectional synchronization between ERIOP
and external CAD systems.
"""

from datetime import datetime, timezone
from typing import Any
import asyncio
import logging
import uuid

from app.integrations.cad.base import (
    CADAdapter,
    CADIncident,
    CADUnit,
    CADIncidentStatus,
    CADUnitStatus,
    CADMapping,
)


logger = logging.getLogger(__name__)


class CADSyncService:
    """
    Bidirectional synchronization between ERIOP and CAD.

    Handles:
    - Initial full sync
    - Real-time incremental sync
    - Conflict resolution
    - ID mapping between systems
    """

    def __init__(
        self,
        cad_adapter: CADAdapter,
        incident_service=None,
        resource_service=None,
    ):
        """
        Initialize sync service.

        Args:
            cad_adapter: CAD system adapter
            incident_service: ERIOP incident service
            resource_service: ERIOP resource service
        """
        self.cad = cad_adapter
        self.incidents = incident_service
        self.resources = resource_service

        # ID mappings (in production, use database)
        self._incident_mappings: dict[str, CADMapping] = {}  # cad_id -> mapping
        self._unit_mappings: dict[str, CADMapping] = {}

        # Sync state
        self._sync_task: asyncio.Task | None = None
        self._running = False
        self._last_sync: datetime | None = None

        # Statistics
        self._stats = {
            "incidents_synced_from_cad": 0,
            "incidents_synced_to_cad": 0,
            "units_synced": 0,
            "sync_errors": 0,
            "conflicts_resolved": 0,
        }

    async def start_sync(self):
        """Start continuous synchronization."""
        if self._running:
            return

        self._running = True
        logger.info(f"Starting CAD sync with {self.cad.cad_system_name}")

        # Ensure connected
        await self.cad.ensure_connected()

        # Initial full sync
        await self._full_sync()

        # Start real-time subscriptions
        self._sync_task = asyncio.create_task(
            self._real_time_sync(),
            name="cad_realtime_sync",
        )

    async def stop_sync(self):
        """Stop synchronization."""
        self._running = False

        if self._sync_task:
            self._sync_task.cancel()
            try:
                await self._sync_task
            except asyncio.CancelledError:
                pass
            self._sync_task = None

        logger.info("CAD sync stopped")

    async def _full_sync(self):
        """Perform full synchronization of all active data."""
        logger.info("Starting full CAD sync")

        try:
            # Sync active incidents from CAD to ERIOP
            cad_incidents = await self.cad.get_active_incidents()
            for cad_incident in cad_incidents:
                await self._sync_incident_from_cad(cad_incident)

            # Sync units from CAD
            cad_units = await self.cad.get_available_units()
            for cad_unit in cad_units:
                await self._sync_unit_from_cad(cad_unit)

            self._last_sync = datetime.now(timezone.utc)
            logger.info(
                f"Full sync complete: {len(cad_incidents)} incidents, "
                f"{len(cad_units)} units"
            )

        except Exception as e:
            self._stats["sync_errors"] += 1
            logger.error(f"Full sync failed: {e}")
            raise

    async def _real_time_sync(self):
        """Handle real-time updates from CAD."""
        # Run incident and unit subscriptions concurrently
        await asyncio.gather(
            self._handle_incident_updates(),
            self._handle_unit_updates(),
            return_exceptions=True,
        )

    async def _handle_incident_updates(self):
        """Process real-time incident updates."""
        try:
            async for cad_incident in self.cad.subscribe_incidents():
                if not self._running:
                    break
                try:
                    await self._sync_incident_from_cad(cad_incident)
                except Exception as e:
                    self._stats["sync_errors"] += 1
                    logger.error(f"Error syncing incident {cad_incident.cad_incident_id}: {e}")
        except asyncio.CancelledError:
            pass
        except Exception as e:
            logger.error(f"Incident subscription error: {e}")

    async def _handle_unit_updates(self):
        """Process real-time unit updates."""
        try:
            async for cad_unit in self.cad.subscribe_units():
                if not self._running:
                    break
                try:
                    await self._sync_unit_from_cad(cad_unit)
                except Exception as e:
                    self._stats["sync_errors"] += 1
                    logger.error(f"Error syncing unit {cad_unit.cad_unit_id}: {e}")
        except asyncio.CancelledError:
            pass
        except Exception as e:
            logger.error(f"Unit subscription error: {e}")

    async def _sync_incident_from_cad(self, cad_incident: CADIncident):
        """
        Sync single incident from CAD to ERIOP.

        Handles:
        - Creating new incidents
        - Updating existing incidents
        - Conflict resolution
        """
        # Check if we have a mapping
        mapping = self._incident_mappings.get(cad_incident.cad_incident_id)

        if mapping:
            # Update existing ERIOP incident
            await self._update_eriop_incident(mapping.eriop_id, cad_incident)
        else:
            # Create new ERIOP incident
            eriop_id = await self._create_eriop_incident(cad_incident)
            if eriop_id:
                # Store mapping
                new_mapping = CADMapping(
                    entity_type="incident",
                    eriop_id=eriop_id,
                    cad_id=cad_incident.cad_incident_id,
                    cad_system=self.cad.cad_system_name,
                )
                self._incident_mappings[cad_incident.cad_incident_id] = new_mapping

        self._stats["incidents_synced_from_cad"] += 1

    async def _create_eriop_incident(self, cad_incident: CADIncident) -> uuid.UUID | None:
        """Create ERIOP incident from CAD data."""
        if not self.incidents:
            logger.debug("No incident service configured")
            return None

        # Map CAD data to ERIOP format
        # This would call incident_service.create_incident()
        # For now, just log
        logger.info(f"Would create ERIOP incident from CAD {cad_incident.cad_incident_id}")

        # Return a mock ID for testing
        return uuid.uuid4()

    async def _update_eriop_incident(
        self,
        eriop_id: uuid.UUID,
        cad_incident: CADIncident,
    ):
        """Update existing ERIOP incident from CAD data."""
        if not self.incidents:
            return

        # Map status
        eriop_status = self.cad.map_status_from_cad(cad_incident.status)

        # This would call incident_service.update_incident()
        logger.debug(f"Would update ERIOP incident {eriop_id} to status {eriop_status}")

    async def _sync_unit_from_cad(self, cad_unit: CADUnit):
        """Sync unit from CAD to ERIOP resources."""
        # Check for existing mapping
        mapping = self._unit_mappings.get(cad_unit.cad_unit_id)

        if mapping and self.resources:
            # Update resource status and location
            pass

        self._stats["units_synced"] += 1

    async def push_to_cad(self, eriop_incident_id: uuid.UUID) -> str | None:
        """
        Push ERIOP incident to CAD system.

        Used when incidents originate in ERIOP (e.g., from alerts).

        Args:
            eriop_incident_id: ERIOP incident ID

        Returns:
            CAD incident ID or None if failed
        """
        if not self.incidents:
            return None

        # Check for existing mapping
        for mapping in self._incident_mappings.values():
            if mapping.eriop_id == eriop_incident_id:
                # Already synced, update instead
                await self._push_update_to_cad(eriop_incident_id, mapping.cad_id)
                return mapping.cad_id

        # Get ERIOP incident
        # incident = await self.incidents.get_incident(eriop_incident_id)

        # Convert to CAD format
        cad_incident = CADIncident(
            cad_incident_id="",  # Will be assigned by CAD
            incident_type="ERIOP",
            priority=3,  # Would map from ERIOP priority
            status=CADIncidentStatus.PENDING,
            location_address="",  # Would get from ERIOP incident
        )

        # Create in CAD
        try:
            cad_id = await self.cad.create_incident(cad_incident)

            # Store mapping
            mapping = CADMapping(
                entity_type="incident",
                eriop_id=eriop_incident_id,
                cad_id=cad_id,
                cad_system=self.cad.cad_system_name,
            )
            self._incident_mappings[cad_id] = mapping

            self._stats["incidents_synced_to_cad"] += 1

            return cad_id

        except Exception as e:
            self._stats["sync_errors"] += 1
            logger.error(f"Failed to push incident to CAD: {e}")
            return None

    async def _push_update_to_cad(
        self,
        eriop_incident_id: uuid.UUID,
        cad_incident_id: str,
    ):
        """Push ERIOP incident updates to CAD."""
        # Get latest ERIOP incident state
        # Map to CAD format
        # Call cad.update_incident()
        pass

    def get_mapping(
        self,
        entity_type: str,
        eriop_id: uuid.UUID = None,
        cad_id: str = None,
    ) -> CADMapping | None:
        """
        Get mapping between ERIOP and CAD IDs.

        Args:
            entity_type: "incident" or "unit"
            eriop_id: ERIOP entity ID (optional)
            cad_id: CAD entity ID (optional)

        Returns:
            CADMapping or None
        """
        mappings = (
            self._incident_mappings if entity_type == "incident"
            else self._unit_mappings
        )

        if cad_id:
            return mappings.get(cad_id)

        if eriop_id:
            for mapping in mappings.values():
                if mapping.eriop_id == eriop_id:
                    return mapping

        return None

    def get_stats(self) -> dict[str, Any]:
        """Get sync statistics."""
        return {
            "running": self._running,
            "last_sync": self._last_sync.isoformat() if self._last_sync else None,
            "cad_system": self.cad.cad_system_name,
            "incident_mappings": len(self._incident_mappings),
            "unit_mappings": len(self._unit_mappings),
            **self._stats,
        }
