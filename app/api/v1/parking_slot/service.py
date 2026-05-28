from fastapi import HTTPException, status

from app.api.v1.parking_slot.schemas import CreateParkingSlotSchema
from app.core.base_service import BaseService
from app.api.v1.parking_slot.repository import (ParkingSlotRepository)
from app.api.v1.vehicle.repository import (VehicleRepository)
from app.utils.helpers import Helpers
from app.core.config import appconfig

# How many times park_vehicle will retry if it loses a race for a slot
# before giving up. Each retry picks a fresh available slot.
MAX_PARK_RETRIES = 5


class ParkingSlotService(BaseService):

    def __init__(self, db):
        super().__init__(db)
        self.slot_repository = ParkingSlotRepository(self.db)
        self.vehicle_repository = VehicleRepository(self.db)

    @Helpers.handle_service_exception("create_slot")
    def create_slot(self, payload: CreateParkingSlotSchema):

        existing_slot = self.slot_repository.existing_slot_no(payload.slot_number)
        existing_slot = self.slot_repository.existing_slot_no(payload.slot_number)
        if existing_slot:
            raise HTTPException(status_code=status.HTTP_400_BAD_REQUEST, detail=f"The slot no '{existing_slot.slot_number}' is already exist.")

        if int(payload.floor) < 0 or int(payload.floor) > int(appconfig.TOTAL_FLOORS):
            raise HTTPException(status_code=status.HTTP_400_BAD_REQUEST, detail=f"Floor cannot be greater than {appconfig.TOTAL_FLOORS}")

        if int(payload.slot_number) < 0 or int(payload.slot_number) > int(appconfig.TOTAL_SLOTS):
            raise HTTPException(status_code=status.HTTP_400_BAD_REQUEST, detail=f"Slot number cannot be greater than {appconfig.TOTAL_SLOTS}")
        
        new_slot = self.slot_repository.create_slot(payload.model_dump())

        return new_slot

    @Helpers.handle_service_exception("get_available_slot")
    def get_available_slot(self, slot_type):
        return self.slot_repository.get_available_slot(slot_type)

    @Helpers.handle_service_exception("park_vehicle")
    def park_vehicle(self, payload):
        """
        Find a free slot of the requested type and atomically assign
        it to the vehicle. Retries if another request claimed the
        same slot first.
        """
        vehicle = self.vehicle_repository.get_vehicle_by_plate_number(
            payload.plate_number
        )
        if not vehicle:
            raise HTTPException(
                status_code=404,
                detail=f"Vehicle with plate '{payload.plate_number}' not found"
            )

        slot_type = payload.slot_type.value

        for _ in range(MAX_PARK_RETRIES):
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
            )
            if claimed:
                # Re-read to get fresh state with vehicle_id set
                slot = self.slot_repository.get_slot_by_id(slot.id)
                return {
                    "slot_id": slot.id,
                    "slot_number": slot.slot_number,
                    "floor": slot.floor,
                    "slot_type": slot.slot_type,
                    "vehicle_id": vehicle.id,
                    "plate_number": vehicle.plate_number,
                }

        # Lost the race MAX_PARK_RETRIES times in a row — system is busy.
        raise HTTPException(
            status_code=409,
            detail=f"Could not acquire a slot of type '{slot_type}' under contention, please retry"
        )

    @Helpers.handle_service_exception("release_slot")
    def release_slot(self, slot_id: str):
        released = self.slot_repository.release_slot(slot_id)
        if not released:
            # Either the slot doesn't exist or was already free.
            # Disambiguate so the client gets a useful error.
            slot = self.slot_repository.get_slot_by_id(slot_id)
            if not slot:
                raise HTTPException(
                    status_code=404,
                    detail=f"Slot '{slot_id}' not found"
                )
            raise HTTPException(
                status_code=409,
                detail=f"Slot '{slot_id}' is already free"
            )
        return self.slot_repository.get_slot_by_id(slot_id)

    @Helpers.handle_service_exception("get_all_slots")
    def get_all_slots(
        self,
        slot_type: str | None = None,
        is_occupied: bool | None = None,
        floor: str | None = None,
    ):
        return self.slot_repository.get_all_slots(
            slot_type=slot_type,
            is_occupied=is_occupied,
            floor=floor,
        )
