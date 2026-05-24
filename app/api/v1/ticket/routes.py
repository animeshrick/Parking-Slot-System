from fastapi import (APIRouter, Depends, Query, status)
from sqlalchemy.orm import Session

from app.core.dependencies import get_db
from app.api.v1.ticket.constants import TicketStatus
from app.api.v1.ticket.schemas import (
    IssueTicketSchema,
    TicketResponseSchema,
)
from app.api.v1.ticket.service import TicketService

router = APIRouter()


@router.post(
    "/issue",
    response_model=TicketResponseSchema,
    status_code=status.HTTP_201_CREATED,
    summary="Issue a ticket — picks a free slot and starts the parking session",
    responses={
        404: {"description": "Vehicle not found"},
        409: {
            "description": (
                "No available slots of this type, vehicle already has an "
                "active ticket, or lost the slot-claim race under contention"
            )
        },
    },
)
def issue_ticket(payload: IssueTicketSchema, db: Session = Depends(get_db)):
    """
    Atomic check-in: resolves the vehicle, finds an available slot of
    the requested type, claims it, and creates a new ACTIVE ticket
    (all in one DB transaction). The returned `ticket_number` is what
    the driver presents on exit.
    """
    service = TicketService(db)
    return service.issue_ticket(payload)


@router.post(
    "/{ticket_id}/close",
    response_model=TicketResponseSchema,
    summary="Close a ticket — computes the fee and frees the slot",
    responses={
        404: {"description": "Ticket not found"},
        409: {"description": "Ticket is already closed"},
    },
)
def close_ticket(ticket_id: str, db: Session = Depends(get_db)):
    service = TicketService(db)
    return service.close_ticket(ticket_id)


@router.get(
    "/active/{plate_number}",
    response_model=TicketResponseSchema,
    summary="Look up a vehicle's currently active ticket",
    responses={404: {"description": "Vehicle or active ticket not found"}},
)
def get_active_ticket_by_plate(plate_number: str, db: Session = Depends(get_db)):
    """Useful at exit when the driver only has the plate, not the ticket id."""
    service = TicketService(db)
    return service.get_active_by_plate(plate_number)


@router.get(
    "/{ticket_id}",
    response_model=TicketResponseSchema,
    summary="Fetch one ticket by id (active or closed)",
    responses={404: {"description": "Ticket not found"}},
)
def get_ticket(ticket_id: str, db: Session = Depends(get_db)):
    service = TicketService(db)
    return service.get_ticket(ticket_id)


@router.get(
    "/",
    response_model=list[TicketResponseSchema],
    summary="List tickets with optional filters",
)
def list_tickets(
    status: TicketStatus | None = Query(
        default=None, description="Filter by status"
    ),
    plate_number: str | None = Query(
        default=None, description="Filter by vehicle plate number"
    ),
    slot_id: str | None = Query(
        default=None, description="Filter by slot id"
    ),
    db: Session = Depends(get_db),
):
    """
    Returns all tickets ordered by entry_time desc. Pass any
    combination of filters to narrow the result. Unknown plate
    returns [], not 404.
    """
    service = TicketService(db)
    return service.list_tickets(
        status=status.value if status else None,
        plate_number=plate_number,
        slot_id=slot_id,
    )
