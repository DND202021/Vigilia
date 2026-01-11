"""Axis Audio Analytics Integration.

Provides integration with Axis network audio devices for:
- Gunshot detection
- Glass break detection
- Aggression detection
- Scream detection
"""

from app.integrations.axis.client import (
    AxisDeviceClient,
    AxisDeviceInfo,
    AxisDeviceError,
)
from app.integrations.axis.events import (
    AudioEventType,
    AxisAudioEvent,
    AxisEventSubscriber,
)
from app.integrations.axis.alert_generator import AudioAlertGenerator

__all__ = [
    "AxisDeviceClient",
    "AxisDeviceInfo",
    "AxisDeviceError",
    "AudioEventType",
    "AxisAudioEvent",
    "AxisEventSubscriber",
    "AudioAlertGenerator",
]
