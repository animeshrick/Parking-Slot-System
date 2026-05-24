from datetime import datetime
import uuid

from sqlalchemy import (
    Column,
    String,
    DateTime,
    Integer,
    ForeignKey,
    Index,
    text,
)

from app.core.database import Base


class Ticket(Base):
    """
    One parking session — from entry to exit.

    Lifecycle: ACTIVE on issue → CLOSED on exit. Rows are never
    deleted; closed tickets are the permanent billing record.
    """

    __tablename__ = "tickets"

    id = Column(
        String,
        primary_key=True,
        default=lambda: str(uuid.uuid4())
    )

    # Human-friendly identifier shown on the printed slip.
    # Format: "{plate_number}-{slot_number}-{int(entry_time.timestamp())}"
    # Uniqueness comes from the timestamp: a vehicle cannot be
    # issued two tickets in the same second.
    ticket_number = Column(
        String,
        unique=True,
        nullable=False,
        index=True,
    )

    vehicle_id = Column(
        String,
        ForeignKey("vehicles.id"),
        nullable=False,
        index=True,
    )

    slot_id = Column(
        String,
        ForeignKey("parking_slots.id"),
        nullable=False,
        index=True,
    )

    entry_time = Column(
        DateTime,
        nullable=False,
        default=datetime.utcnow,
    )

    # Null while ACTIVE, set on close.
    exit_time = Column(
        DateTime,
        nullable=True,
    )

    # Snapshot of the rate at issue time so future env changes
    # don't retroactively change historical bills.
    rate_per_hour = Column(
        Integer,
        nullable=False,
    )

    # Null while ACTIVE, computed on close.
    fee_amount = Column(
        Integer,
        nullable=True,
    )

    status = Column(
        String,
        nullable=False,
        default="ACTIVE",
        index=True,
    )

    created_at = Column(
        DateTime,
        default=datetime.utcnow,
    )

    updated_at = Column(
        DateTime,
        default=datetime.utcnow,
        onupdate=datetime.utcnow,
    )

    __table_args__ = (
        # A vehicle can only have one ACTIVE ticket at a time.
        # Partial unique index: enforced by DB, not just by app logic,
        # so a race between two concurrent /issue calls can never end
        # with the same vehicle holding two open tickets.
        Index(
            "uq_active_ticket_per_vehicle",
            "vehicle_id",
            unique=True,
            sqlite_where=text("status = 'ACTIVE'"),
            postgresql_where=text("status = 'ACTIVE'"),
        ),
    )
