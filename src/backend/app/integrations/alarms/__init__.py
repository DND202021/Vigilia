"""Alarm System Integration.

Provides integration with alarm monitoring systems using:
- Contact ID (Ademco) protocol
- SIA DC-07/DC-09 protocols
"""

from app.integrations.alarms.protocols import (
    AlarmProtocol,
    RawAlarmSignal,
    StandardizedAlarm,
    AlarmDecoder,
)
from app.integrations.alarms.contact_id import ContactIdDecoder
from app.integrations.alarms.normalizer import AlarmNormalizer
from app.integrations.alarms.receiver import AlarmReceiverService

__all__ = [
    "AlarmProtocol",
    "RawAlarmSignal",
    "StandardizedAlarm",
    "AlarmDecoder",
    "ContactIdDecoder",
    "AlarmNormalizer",
    "AlarmReceiverService",
]
