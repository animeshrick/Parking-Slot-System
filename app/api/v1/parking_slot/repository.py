from sqlalchemy.orm import Session

from app.api.v1.parking_slot.model import (
    ParkingSlot
)


class ParkingSlotRepository:

    def __init__(self, db: Session):
        self.db = db

    def create_slot(self, slot_data):
        slot = ParkingSlot(**slot_data)
        self.db.add(slot)
        self.db.commit()
        self.db.refresh(slot)
        return slot

    def get_available_slot(self, slot_type: str):
        return (
            self.db.query(ParkingSlot)
            .filter(
                ParkingSlot.slot_type == slot_type,
                ParkingSlot.is_occupied == False
            )
            .first()
        )

    def get_slot_by_id(self, slot_id: str):
        return (
            self.db.query(ParkingSlot)
            .filter(ParkingSlot.id == slot_id)
            .first()
        )

    def try_occupy_slot(
        self,
        slot_id: str,
        vehicle_id: str,
        vehicle_type: str,
        commit: bool = True,
    ) -> bool:
        """
        Atomically claim a slot for a vehicle.

        Issues a single UPDATE ... WHERE id=? AND is_occupied=False
        so two concurrent requests cannot both succeed on the same row.

        Pass commit=False when the caller wants to batch this with
        other writes in the same transaction (e.g. TicketService
        claiming a slot and inserting a ticket together).

        Returns True if this caller claimed the slot, False if it was
        already taken by someone else.
        """
        rows_updated = (
            self.db.query(ParkingSlot)
            .filter(
                ParkingSlot.id == slot_id,
                ParkingSlot.is_occupied == False,
                ParkingSlot.slot_type == vehicle_type,
            )
            .update(
                {
                    "is_occupied": True,
                    "vehicle_id": vehicle_id,
                },
                synchronize_session=False,
            )
        )
        if commit:
            self.db.commit()
        return rows_updated > 0

    def release_slot(self, slot_id: str, commit: bool = True) -> bool:
        """
        Atomically free a slot. Returns True if this call actually
        released an occupied slot, False if it was already free.

        Pass commit=False to batch with other writes (e.g. closing a
        ticket and releasing the slot in one transaction).
        """
        rows_updated = (
            self.db.query(ParkingSlot)
            .filter(
                ParkingSlot.id == slot_id,
                ParkingSlot.is_occupied == True,
            )
            .update(
                {
                    "is_occupied": False,
                    "vehicle_id": None,
                },
                synchronize_session=False,
            )
        )
        if commit:
            self.db.commit()
        return rows_updated > 0

    def get_all_slots(
        self,
        slot_type: str | None = None,
        is_occupied: bool | None = None,
        floor: str | None = None,
    ):
        """
        Return every slot, optionally narrowed by type / occupancy / floor.
        All filters are independent — pass None to skip a filter.
        """
        query = self.db.query(ParkingSlot)

        if slot_type is not None:
            query = query.filter(ParkingSlot.slot_type == slot_type)
        if is_occupied is not None:
            query = query.filter(ParkingSlot.is_occupied == is_occupied)
        if floor is not None:
            query = query.filter(ParkingSlot.floor == floor)

        return query.order_by(ParkingSlot.floor, ParkingSlot.slot_number).all()
    
    def existing_slot_no(self, slot_no: str):
        return (
            self.db.query(ParkingSlot)
            .filter(ParkingSlot.slot_number == slot_no)
            .first()
        )