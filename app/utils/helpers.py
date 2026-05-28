from app.core.logger import log
from app.core.redis_client import redis_client
from functools import wraps
from fastapi import HTTPException

class Helpers:
    def handle_service_exception_bkp(operation_name: str):
        def decorator(func):
            @wraps(func)
            def wrapper(*args, **kwargs):
                try:
                    return func(*args, **kwargs)
                except HTTPException:
                    raise
                except Exception as e:
                    log.error(
                        message=f"{operation_name}_error",
                        data={"error": str(e)},
                        fileName=f"{operation_name}_error"
                    )
                    raise HTTPException(
                        status_code=500,
                        detail="Internal Server Error"
                    )

            return wrapper

        return decorator
    
    @staticmethod
    def check_vehicle_number(plate_number: str) -> bool:
        plate_number = plate_number.replace(" ", "")
        if len(plate_number) > 10 or len(plate_number) <= 0:
            return False
        return True
    
    @staticmethod
    def handle_service_exception(operation_name: str):
        def decorator(func):
            def wrapper(*args, **kwargs):
                try:
                    return func(*args, **kwargs)
                except HTTPException as e:
                    log.error(
                        message=f"{operation_name}_error_1",
                        data={"error": str(e)},
                        fileName=f"{operation_name}_error_1"
                    )
                    raise e

                except Exception as e:
                    log.error(
                        message=f"{operation_name}_error",
                        data={"error": str(e)},
                        fileName=f"{operation_name}_error"
                    )
                    raise HTTPException(
                        status_code=500,
                        detail=f"{operation_name} failed: {str(e)}"
                    )
            return wrapper
        return decorator
    
    @staticmethod
    def update_redis_slot_per_floor(db, floor: str):
        """Update Redis key with the number of free slots on a given floor.

        Args:
            db: SQLAlchemy Session used to query the ParkingSlot table.
            floor: The floor identifier (string) to count slots for.
        """
        try:
            from app.api.v1.parking_slot.model import ParkingSlot
            # Build key
            key = f"parking:floor:{floor}:available_slots"
            # Count slots that are NOT occupied on the given floor
            available_count = (
                db.query(ParkingSlot)
                .filter(ParkingSlot.floor == floor, ParkingSlot.is_occupied == False)
                .count()
            )
            # Store in Redis with a 1‑hour TTL
            Helpers.redis_set(key, str(available_count), expire_seconds=3600)
            # Return the cached value for convenience
            free_redis_slots = Helpers.redis_get(key)
            return free_redis_slots
        except Exception as e:
            log.error(
                message="update_redis_slot_per_floor",
                data={"error": str(e)},
                fileName="update_redis_slot_per_floor"
            )
            return 0


    @staticmethod
    def redis_set(key: str, value: str, expire_seconds: int | None = None) -> bool:
        """
        Save a key-value pair in Redis. Optionally set an expiration time in seconds.
        """
        try:
            return redis_client.set(key, value, ex=expire_seconds)
        except Exception as e:
            log.error(
                message="redis_set_error",
                data={"key": key, "error": str(e)},
                fileName="redis_error"
            )
            return False

    @staticmethod
    def redis_get(key: str) -> str | None:
        """
        Fetch the value of a key from Redis.
        """
        try:
            return redis_client.get(key)
        except Exception as e:
            log.error(
                message="redis_get_error",
                data={"key": key, "error": str(e)},
                fileName="redis_error"
            )
            return None

helper = Helpers()