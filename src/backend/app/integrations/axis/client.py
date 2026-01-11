"""Axis device client for VAPIX API communication."""

from dataclasses import dataclass
from datetime import datetime, timezone
from typing import Any
import asyncio
import logging
import aiohttp

from app.integrations.base import IntegrationAdapter, IntegrationError, CircuitBreakerConfig


logger = logging.getLogger(__name__)


class AxisDeviceError(IntegrationError):
    """Axis device specific errors."""
    pass


@dataclass
class AxisDeviceInfo:
    """Axis device information."""
    device_id: str
    name: str
    model: str
    firmware_version: str
    serial_number: str
    ip_address: str
    mac_address: str | None = None
    location: tuple[float, float] | None = None  # (lat, lon)
    location_name: str | None = None
    capabilities: list[str] | None = None


@dataclass
class AudioAnalyticsConfig:
    """Audio analytics configuration for an Axis device."""
    gunshot_enabled: bool = True
    gunshot_sensitivity: int = 50
    glass_break_enabled: bool = True
    glass_break_sensitivity: int = 50
    aggression_enabled: bool = True
    aggression_sensitivity: int = 50
    scream_enabled: bool = True
    scream_sensitivity: int = 50


class AxisDeviceClient(IntegrationAdapter):
    """
    Client for communicating with Axis audio devices.

    Uses VAPIX API for device management and configuration.
    """

    def __init__(
        self,
        device_ip: str,
        username: str,
        password: str,
        verify_ssl: bool = False,
        device_name: str | None = None,
        device_location: tuple[float, float] | None = None,
        location_name: str | None = None,
        circuit_breaker_config: CircuitBreakerConfig | None = None,
    ):
        super().__init__(
            name=f"axis_{device_ip.replace('.', '_')}",
            circuit_breaker_config=circuit_breaker_config,
        )

        self.device_ip = device_ip
        self.username = username
        self.password = password
        self.verify_ssl = verify_ssl
        self.device_name = device_name
        self.device_location = device_location
        self.location_name = location_name

        self.base_url = f"https://{device_ip}" if verify_ssl else f"http://{device_ip}"
        self._session: aiohttp.ClientSession | None = None
        self._device_info: AxisDeviceInfo | None = None

    async def connect(self) -> bool:
        """Connect to Axis device."""
        try:
            auth = aiohttp.BasicAuth(self.username, self.password)
            connector = aiohttp.TCPConnector(ssl=self.verify_ssl)
            self._session = aiohttp.ClientSession(
                auth=auth,
                connector=connector,
            )

            # Verify connection by getting device info
            self._device_info = await self._get_device_info()
            self._connected = True

            logger.info(f"Connected to Axis device: {self._device_info.name} ({self.device_ip})")
            return True

        except Exception as e:
            logger.error(f"Failed to connect to Axis device {self.device_ip}: {e}")
            if self._session:
                await self._session.close()
                self._session = None
            raise AxisDeviceError(
                f"Connection failed: {e}",
                source=self.name,
                original_error=e,
            )

    async def disconnect(self) -> None:
        """Disconnect from Axis device."""
        if self._session:
            await self._session.close()
            self._session = None
        self._connected = False
        logger.info(f"Disconnected from Axis device {self.device_ip}")

    async def health_check(self) -> dict[str, Any]:
        """Check device health."""
        if not self._session:
            return {"healthy": False, "error": "Not connected"}

        try:
            info = await self._get_device_info()
            return {
                "healthy": True,
                "device_id": info.device_id,
                "name": info.name,
                "model": info.model,
                "firmware": info.firmware_version,
            }
        except Exception as e:
            return {"healthy": False, "error": str(e)}

    @property
    def device_info(self) -> AxisDeviceInfo | None:
        """Get cached device info."""
        return self._device_info

    async def _get_device_info(self) -> AxisDeviceInfo:
        """Retrieve device information via VAPIX."""
        if not self._session:
            raise AxisDeviceError("Not connected", source=self.name)

        url = f"{self.base_url}/axis-cgi/basicdeviceinfo.cgi"
        params = {"infoTypes": "all"}

        async with self._session.get(url, params=params) as response:
            if response.status != 200:
                raise AxisDeviceError(
                    f"Failed to get device info: HTTP {response.status}",
                    source=self.name,
                )

            data = await response.json()
            info = data.get("data", {}).get("propertyList", {})

            return AxisDeviceInfo(
                device_id=info.get("SerialNumber", self.device_ip),
                name=self.device_name or info.get("ProdNbr", "Unknown"),
                model=info.get("ProdNbr", "Unknown"),
                firmware_version=info.get("Version", "Unknown"),
                serial_number=info.get("SerialNumber", "Unknown"),
                ip_address=self.device_ip,
                mac_address=info.get("HardwareID"),
                location=self.device_location,
                location_name=self.location_name,
                capabilities=self._parse_capabilities(info),
            )

    def _parse_capabilities(self, info: dict) -> list[str]:
        """Parse device capabilities."""
        capabilities = []
        if info.get("Audio", False):
            capabilities.append("audio")
        if info.get("AudioAnalytics", False):
            capabilities.append("audio_analytics")
        return capabilities

    async def get_audio_analytics_config(self) -> AudioAnalyticsConfig:
        """Get current audio analytics configuration."""
        if not self._session:
            raise AxisDeviceError("Not connected", source=self.name)

        url = f"{self.base_url}/axis-cgi/param.cgi"
        params = {"action": "list", "group": "AudioAnalytics"}

        async with self._session.get(url, params=params) as response:
            if response.status != 200:
                raise AxisDeviceError(
                    f"Failed to get audio config: HTTP {response.status}",
                    source=self.name,
                )

            text = await response.text()
            return self._parse_audio_config(text)

    def _parse_audio_config(self, config_text: str) -> AudioAnalyticsConfig:
        """Parse VAPIX parameter response into config object."""
        config = AudioAnalyticsConfig()

        for line in config_text.strip().split("\n"):
            if "=" not in line:
                continue
            key, value = line.split("=", 1)

            if "Gunshot.Enabled" in key:
                config.gunshot_enabled = value.lower() == "yes"
            elif "Gunshot.Sensitivity" in key:
                config.gunshot_sensitivity = int(value)
            elif "GlassBreak.Enabled" in key:
                config.glass_break_enabled = value.lower() == "yes"
            elif "GlassBreak.Sensitivity" in key:
                config.glass_break_sensitivity = int(value)
            elif "Aggression.Enabled" in key:
                config.aggression_enabled = value.lower() == "yes"
            elif "Aggression.Sensitivity" in key:
                config.aggression_sensitivity = int(value)
            elif "Scream.Enabled" in key:
                config.scream_enabled = value.lower() == "yes"
            elif "Scream.Sensitivity" in key:
                config.scream_sensitivity = int(value)

        return config

    async def configure_detection(
        self,
        detection_type: str,
        enabled: bool = True,
        sensitivity: int = 50,
    ) -> bool:
        """
        Configure audio detection parameters.

        Args:
            detection_type: Type of detection (gunshot, glass_break, aggression, scream)
            enabled: Whether detection is enabled
            sensitivity: Detection sensitivity (0-100)

        Returns:
            True if configuration successful
        """
        if not self._session:
            raise AxisDeviceError("Not connected", source=self.name)

        # Map detection type to VAPIX parameter
        type_map = {
            "gunshot": "Gunshot",
            "glass_break": "GlassBreak",
            "aggression": "Aggression",
            "scream": "Scream",
        }

        vapix_type = type_map.get(detection_type.lower())
        if not vapix_type:
            raise AxisDeviceError(
                f"Unknown detection type: {detection_type}",
                source=self.name,
                retryable=False,
            )

        url = f"{self.base_url}/axis-cgi/param.cgi"
        params = {
            "action": "update",
            f"AudioAnalytics.{vapix_type}.Enabled": "yes" if enabled else "no",
            f"AudioAnalytics.{vapix_type}.Sensitivity": str(sensitivity),
        }

        async with self._session.get(url, params=params) as response:
            if response.status != 200:
                raise AxisDeviceError(
                    f"Failed to configure detection: HTTP {response.status}",
                    source=self.name,
                )

            text = await response.text()
            return "OK" in text

    async def get_audio_clip(
        self,
        start_time: datetime,
        duration_seconds: int = 10,
    ) -> bytes | None:
        """
        Retrieve audio clip around event timestamp.

        Args:
            start_time: When to start the clip
            duration_seconds: Duration of clip to retrieve

        Returns:
            Audio data in WAV format or None if not available
        """
        if not self._session:
            raise AxisDeviceError("Not connected", source=self.name)

        # Axis audio clip API
        url = f"{self.base_url}/axis-cgi/media.cgi"
        params = {
            "audio": "1",
            "duration": str(duration_seconds),
            "starttime": start_time.strftime("%Y-%m-%dT%H:%M:%S"),
        }

        try:
            async with self._session.get(url, params=params) as response:
                if response.status != 200:
                    logger.warning(f"Failed to get audio clip: HTTP {response.status}")
                    return None

                return await response.read()
        except Exception as e:
            logger.warning(f"Error retrieving audio clip: {e}")
            return None


class AxisDeviceRegistry:
    """Registry for managing multiple Axis devices."""

    def __init__(self):
        self._devices: dict[str, AxisDeviceClient] = {}

    async def register(self, client: AxisDeviceClient):
        """Register a device client."""
        await client.connect()
        if client.device_info:
            self._devices[client.device_info.device_id] = client

    async def unregister(self, device_id: str):
        """Unregister a device."""
        client = self._devices.pop(device_id, None)
        if client:
            await client.disconnect()

    def get(self, device_id: str) -> AxisDeviceClient | None:
        """Get device client by ID."""
        return self._devices.get(device_id)

    def get_all(self) -> list[AxisDeviceClient]:
        """Get all registered devices."""
        return list(self._devices.values())

    async def disconnect_all(self):
        """Disconnect all devices."""
        for client in self._devices.values():
            await client.disconnect()
        self._devices.clear()
