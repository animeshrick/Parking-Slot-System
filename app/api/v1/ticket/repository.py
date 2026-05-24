from datetime import datetime

from sqlalchemy.orm import Session

from app.api.v1.ticket.constants import TicketStatus
from app.api.v1.ticket.model import Ticket


class TicketRepository:

    def __init__(self, db: Session):
        self.db = db

    def create(
        self,
        ticket_data: dict,
        commit: bool = True,
    ) -> Ticket:
        """
        Insert a new ticket. Pass commit=False when the caller wants
        to batch this with other writes (e.g. claiming a slot and
        issuing the ticket inside one transaction).
        """
        ticket = Ticket(**ticket_data)
        self.db.add(ticket)
        if commit:
            self.db.commit()
            self.db.refresh(ticket)
        else:
            self.db.flush()  # populates defaults (id, timestamps) without committing
        return ticket

    def get_by_id(self, ticket_id: str) -> Ticket | None:
        return (
            self.db.query(Ticket)
            .filter(Ticket.id == ticket_id)
            .first()
        )

    def get_active_by_vehicle(self, vehicle_id: str) -> Ticket | None:
        return (
            self.db.query(Ticket)
            .filter(
                Ticket.vehicle_id == vehicle_id,
                Ticket.status == TicketStatus.ACTIVE.value,
            )
            .first()
        )

    def try_close_atomic(
        self,
        ticket_id: str,
        exit_time: datetime,
        fee_amount: int,
        commit: bool = True,
    ) -> bool:
        """
        Atomically transition ACTIVE → CLOSED.

        UPDATE tickets
           SET status='CLOSED', exit_time=?, fee_amount=?
         WHERE id=? AND status='ACTIVE'

        Only one concurrent close request gets rows=1; the other
        gets 0 and the service maps that to a 409.
        """
        rows_updated = (
            self.db.query(Ticket)
            .filter(
                Ticket.id == ticket_id,
                Ticket.status == TicketStatus.ACTIVE.value,
            )
            .update(
                {
                    "status": TicketStatus.CLOSED.value,
                    "exit_time": exit_time,
                    "fee_amount": fee_amount,
                },
                synchronize_session=False,
            )
        )
        if commit:
            self.db.commit()
        return rows_updated > 0

    def list_tickets(
        self,
        status: str | None = None,
        vehicle_id: str | None = None,
        slot_id: str | None = None,
    ) -> list[Ticket]:
        query = self.db.query(Ticket)
        if status is not None:
            query = query.filter(Ticket.status == status)
        if vehicle_id is not None:
            query = query.filter(Ticket.vehicle_id == vehicle_id)
        if slot_id is not None:
            query = query.filter(Ticket.slot_id == slot_id)
        return query.order_by(Ticket.entry_time.desc()).all()
