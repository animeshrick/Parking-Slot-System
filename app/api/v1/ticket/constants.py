from enum import Enum

from app.api.v1.parking_slot.constants import SlotType
from app.core.config import appconfig


class TicketStatus(str, Enum):
    ACTIVE = "ACTIVE"
    CLOSED = "CLOSED"


# Map each slot type to its hourly rate (loaded from env on import).
# Lookup happens at ticket-issue time; the resolved rate is then
# snapshotted into the ticket row so future env changes don't
# rewrite past bills.
RATE_PER_HOUR_BY_SLOT_TYPE = {
    SlotType.CAR.value:   appconfig.RATE_CAR,
    SlotType.BIKE.value:  appconfig.RATE_BIKE,
    SlotType.TRUCK.value: appconfig.RATE_TRUCK,
}
