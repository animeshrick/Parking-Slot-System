from datetime import datetime

from fastapi import HTTPException
from sqlalchemy.exc import IntegrityError

from app.core.base_service import BaseService
from app.core.config import appconfig
from app.utils.helpers import Helpers

from app.api.v1.vehicle.repository import VehicleRepository
from app.api.v1.parking_slot.repository import ParkingSlotRepository

from app.api.v1.ticket.billing import compute_fee
from app.api.v1.ticket.constants import (
    RATE_PER_HOUR_BY_SLOT_TYPE,
    TicketStatus,
)
from app.api.v1.ticket.repository import TicketRepository

# How many times issue_ticket retries when it loses the slot-claim
# race to a concurrent request before giving up with 409.
MAX_ISSUE_RETRIES = appconfig.MAX_TICKET_ISSUE_RETRIES


class TicketService(BaseService):

    def __init__(self, db):
        super().__init__(db)
        self.ticket_repository = TicketRepository(self.db)
        self.vehicle_repository = VehicleRepository(self.db)
        self.slot_repository = ParkingSlotRepository(self.db)

    @Helpers.handle_service_exception("issue_ticket")
    def issue_ticket(self, payload):
        """
        Flow:
          1. Resolve the vehicle by plate.
          2. Reject if it already has an active ticket (service check
             — the DB partial unique index is the ultimate guard).
          3. Loop: pick a free slot of the requested type, atomically
             claim it (no commit yet), then create the ticket. Both
             writes commit together; if either step fails the session
             rolls back so the slot stays free.
        """
        vehicle = self.vehicle_repository.get_vehicle_by_plate_number(
            payload.plate_number
        )
        if not vehicle:
            raise HTTPException(
                status_code=404,
                detail=f"Vehicle with plate '{payload.plate_number}' not found"
            )

        existing_active = self.ticket_repository.get_active_by_vehicle(vehicle.id)
        if existing_active:
            raise HTTPException(
                status_code=409,
                detail=(
                    f"Vehicle '{payload.plate_number}' already has an active "
                    f"ticket ({existing_active.ticket_number})"
                ),
            )

        slot_type = payload.slot_type.value
        rate = RATE_PER_HOUR_BY_SLOT_TYPE[slot_type]

        for _ in range(MAX_ISSUE_RETRIES):
            slot = self.slot_repository.get_available_slot(slot_type)
            if not slot:
                raise HTTPException(
                    status_code=409,
                    detail=f"No available '{slot_type}' slots"
                )

            claimed = self.slot_repository.try_occupy_slot(
                slot_id=slot.id,
                vehicle_id=vehicle.id,
                vehicle_type=vehicle.vehicle_type,
                commit=False,
            )
            if not claimed:
                # Lost the race for this specific slot — pick another.
                continue

            entry_time = datetime.utcnow()
            ticket_number = (
                f"{vehicle.plate_number}-{slot.slot_number}-"
                f"{int(entry_time.timestamp())}"
            )

            try:
                ticket = self.ticket_repository.create(
                    ticket_data={
                        "ticket_number": ticket_number,
                        "vehicle_id": vehicle.id,
                        "slot_id": slot.id,
                        "entry_time": entry_time,
                        "rate_per_hour": rate,
                        "status": TicketStatus.ACTIVE.value,
                    },
                    commit=False,
                )
                self.db.commit()
                self.db.refresh(ticket)
                # return ticket
                return {
                    "ticket": ticket,
                    "slot": slot,
                    "fee": {
                        "rate_per_hour": ticket.rate_per_hour,
                        "fee_amount": ticket.fee_amount,
                        "entry_time": ticket.entry_time,
                        "status": ticket.status
                    },
                }

            except IntegrityError:
                # The partial unique index caught a race — between our
                # "existing active" check and this insert, another
                # request issued a ticket for the same vehicle.
                self.db.rollback()
                raise HTTPException(
                    status_code=409,
                    detail=(
                        f"Vehicle '{payload.plate_number}' already has an "
                        f"active ticket"
                    ),
                )
            except Exception:
                # Any other failure: roll back so the slot claim is undone.
                self.db.rollback()
                raise

        raise HTTPException(
            status_code=409,
            detail=(
                f"Could not acquire a slot of type '{slot_type}' under "
                f"contention, please retry"
            ),
        )

    @Helpers.handle_service_exception("close_ticket")
    def close_ticket(self, ticket_id: str):
        """
        Flow:
          1. Load ticket; 404 if missing.
          2. Compute fee using the snapshotted rate + grace period
             from current config.
          3. Atomic close (ACTIVE → CLOSED). If it loses the race
             (already closed) → 409.
          4. Release the slot in the same transaction.
          5. Return the updated ticket.
        """
        ticket = self.ticket_repository.get_by_id(ticket_id)
        if not ticket:
            raise HTTPException(
                status_code=404,
                detail=f"Ticket '{ticket_id}' not found",
            )
        if ticket.status != TicketStatus.ACTIVE.value:
            raise HTTPException(
                status_code=409,
                detail=f"Ticket '{ticket_id}' is already {ticket.status}",
            )

        exit_time = datetime.utcnow()
        fee = compute_fee(
            entry_time=ticket.entry_time,
            exit_time=exit_time,
            rate_per_hour=ticket.rate_per_hour,
            grace_minutes=appconfig.GRACE_PERIOD_MINUTES,
        )

        try:
            closed = self.ticket_repository.try_close_atomic(
                ticket_id=ticket_id,
                exit_time=exit_time,
                fee_amount=fee,
                commit=False,
            )
            if not closed:
                # Someone else closed it between our check and the UPDATE.
                self.db.rollback()
                raise HTTPException(
                    status_code=409,
                    detail=f"Ticket '{ticket_id}' was just closed by another request",
                )

            # release_slot is itself atomic (WHERE is_occupied=True);
            # if the slot somehow isn't occupied, this is a no-op rather
            # than an error, which is what we want here.
            self.slot_repository.release_slot(
                slot_id=ticket.slot_id,
                commit=False,
            )
            self.db.commit()
        except HTTPException:
            raise
        except Exception:
            self.db.rollback()
            raise

        return self.ticket_repository.get_by_id(ticket_id)

    @Helpers.handle_service_exception("get_ticket")
    def get_ticket(self, ticket_id: str):
        ticket = self.ticket_repository.get_by_id(ticket_id)
        if not ticket:
            raise HTTPException(
                status_code=404,
                detail=f"Ticket '{ticket_id}' not found",
            )
        return ticket

    @Helpers.handle_service_exception("get_active_by_plate")
    def get_active_by_plate(self, plate_number: str):
        vehicle = self.vehicle_repository.get_vehicle_by_plate_number(plate_number)
        if not vehicle:
            raise HTTPException(
                status_code=404,
                detail=f"Vehicle with plate '{plate_number}' not found",
            )
        ticket = self.ticket_repository.get_active_by_vehicle(vehicle.id)
        if not ticket:
            raise HTTPException(
                status_code=404,
                detail=f"No active ticket for vehicle '{plate_number}'",
            )
        return ticket

    @Helpers.handle_service_exception("list_tickets")
    def list_tickets(
        self,
        status: str | None = None,
        plate_number: str | None = None,
        slot_id: str | None = None,
    ):
        # Translate plate_number → vehicle_id so the repository
        # stays generic.
        vehicle_id = None
        if plate_number:
            vehicle = self.vehicle_repository.get_vehicle_by_plate_number(plate_number)
            if not vehicle:
                # Filtering by a plate that doesn't exist returns []
                # rather than 404 — list endpoints should not 404 on
                # zero matches.
                return []
            vehicle_id = vehicle.id

        return self.ticket_repository.list_tickets(
            status=status,
            vehicle_id=vehicle_id,
            slot_id=slot_id,
        )
