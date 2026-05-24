from datetime import datetime

from pydantic import BaseModel

from app.api.v1.parking_slot.constants import SlotType
from app.api.v1.ticket.constants import TicketStatus


class IssueTicketSchema(BaseModel):
    """Input for POST /v1/ticket/issue."""
    plate_number: str
    slot_type: SlotType


class TicketResponseSchema(BaseModel):
    id: str
    ticket_number: str
    vehicle_id: str
    slot_id: str
    entry_time: datetime
    exit_time: datetime | None
    rate_per_hour: int
    # Populated only after the ticket is closed.
    fee_amount: int | None
    status: TicketStatus
    created_at: datetime
    updated_at: datetime

    class Config:
        from_attributes = True
