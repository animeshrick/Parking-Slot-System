from fastapi import (APIRouter, Depends, Query, status)
from sqlalchemy.orm import Session

from app.core.dependencies import get_db
from app.api.v1.parking_slot.constants import SlotType
from app.api.v1.parking_slot.schemas import (
    CreateParkingSlotSchema,
    ParkingSlotResponseSchema,
    ParkVehicleSchema,
    ParkResponseSchema,
)
from app.api.v1.parking_slot.service import (ParkingSlotService)

router = APIRouter()


@router.post(
    "/slots",
    # response_model=ParkingSlotResponseSchema,
    status_code=status.HTTP_201_CREATED,
    summary="Create a new parking slot",
)
def create_slot(payload: CreateParkingSlotSchema, db: Session = Depends(get_db)):
    service = ParkingSlotService(db)
    return service.create_slot(payload)


@router.get(
    "/slots",
    response_model=list[ParkingSlotResponseSchema],
    summary="List all slots (free + occupied), with optional filters",
)
def get_all_slots(
    slot_type: SlotType | None = Query(
        default=None, description="Filter by slot type (CAR / BIKE / TRUCK)"
    ),
    is_occupied: bool | None = Query(
        default=None, description="Filter by occupancy. Omit for both."
    ),
    floor: str | None = Query(
        default=None, description="Filter by floor"
    ),
    db: Session = Depends(get_db),
):
    """
    Returns every slot in the system. Pass any combination of the
    query filters to narrow the result; with no filters you get the
    full list of occupied and free slots.
    """
    service = ParkingSlotService(db)
    return service.get_all_slots(
        slot_type=slot_type.value if slot_type else None,
        is_occupied=is_occupied,
        floor=floor,
    )


# @router.get(
#     "/slots/{slot_type}",
#     response_model=ParkingSlotResponseSchema | None,
#     summary="Get any one available slot of the given type",
# )
# def get_available_slot(slot_type: SlotType, db: Session = Depends(get_db)):
#     # Using SlotType (enum) as the type makes FastAPI validate the
#     # path value and gives Swagger a dropdown.
#     service = ParkingSlotService(db)
#     return service.get_available_slot(slot_type.value)


# @router.post(
#     "/park",
#     response_model=ParkResponseSchema,
#     status_code=status.HTTP_200_OK,
#     summary="Park a vehicle (atomic claim of a free slot)",
#     responses={
#         404: {"description": "Vehicle not found"},
#         409: {"description": "No available slots of this type, or lost race under contention"},
#     },
# )
# def park_vehicle(payload: ParkVehicleSchema, db: Session = Depends(get_db)):
#     """
#     Atomically assign one available slot of the requested type to
#     the vehicle identified by `plate_number`. Replaces the old
#     `occupy_slot` endpoint which had a race condition.
#     """
#     service = ParkingSlotService(db)
#     return service.park_vehicle(payload)


@router.post(
    "/release/{slot_id}",
    response_model=ParkingSlotResponseSchema,
    summary="Release an occupied slot",
    responses={
        404: {"description": "Slot not found"},
        409: {"description": "Slot is already free"},
    },
)
def release_slot(slot_id: str, db: Session = Depends(get_db)):
    service = ParkingSlotService(db)
    return service.release_slot(slot_id)
