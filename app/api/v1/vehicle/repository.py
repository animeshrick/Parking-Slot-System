from sqlalchemy.orm import Session
from app.api.v1.vehicle.model import Vehicle


class VehicleRepository:

    def __init__(self, db: Session):
        self.db = db

    def create_vehicle(self, vehicle_data):
        vehicle = Vehicle(**vehicle_data)

        self.db.add(vehicle)
        self.db.commit()
        self.db.refresh(vehicle)

        return vehicle

    def get_vehicle_by_plate_number(
        self,
        plate_number: str
    ):
        return (
            self.db.query(Vehicle)
            .filter(
                Vehicle.plate_number == plate_number
            )
            .first()
        )
        # return vehicle

    def get_all_vehicle(self):
        return (self.db.query(Vehicle).all())