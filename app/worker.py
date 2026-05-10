import os
import time
from celery import Celery
from dotenv import load_dotenv

load_dotenv()

REDIS_URL = os.getenv("REDIS_URL", "redis://redis:6379/0")

celery_app = Celery(
    "waymark_worker",
    broker=REDIS_URL,
    backend=REDIS_URL
)

celery_app.conf.update(
    task_serializer="json",
    accept_content=["json"],
    result_serializer="json",
    timezone="Asia/Ho_Chi_Minh",
    enable_utc=True,
)

@celery_app.task(name="tasks.process_media")
def process_media(memory_id: str):
    # Dummy media processing (thumbnail generation, transcode)
    print(f"Starting media processing for memory {memory_id}...")
    time.sleep(3) # Simulate work
    print(f"Media processing for memory {memory_id} completed.")
    return True

@celery_app.task(name="tasks.send_notification")
def send_notification(
    user_id: str,
    message: str,
    sender_id: str = None,
    notification_type: int = 1,
    reference_id: str = None
):
    print(f"Sending push notification to user {user_id}: {message}")
    
    # Save notification to PostgreSQL database
    from app.database import SessionLocal
    from app.models import Notification
    import uuid
    
    db = SessionLocal()
    try:
        notif = Notification(
            id=uuid.uuid4(),
            user_id=uuid.UUID(user_id),
            sender_id=uuid.UUID(sender_id) if sender_id else None,
            notification_type=notification_type,
            message=message,
            reference_id=uuid.UUID(reference_id) if reference_id else None,
            is_read=False
        )
        db.add(notif)
        db.commit()
        print(f"Notification successfully saved to database for user_id: {user_id}")
    except Exception as e:
        db.rollback()
        print(f"Failed to save notification: {str(e)}")
    finally:
        db.close()
        
    return True

@celery_app.task(name="tasks.reverse_geocode")
def reverse_geocode(memory_id: str):
    from app.database import SessionLocal
    from app.models import Memory
    from sqlalchemy import func
    import requests
    import uuid

    print(f"Starting reverse geocoding for memory {memory_id}...")
    db = SessionLocal()
    try:
        # Get memory and coordinates
        memory = db.query(Memory).filter(Memory.id == uuid.UUID(memory_id)).first()
        if not memory:
            print(f"Memory {memory_id} not found.")
            return False

        # Extract lat/lng from location geometry
        coords = db.query(
            func.ST_Y(Memory.location).label('lat'),
            func.ST_X(Memory.location).label('lng')
        ).filter(Memory.id == uuid.UUID(memory_id)).first()

        if not coords:
            print(f"Coordinates for memory {memory_id} not found.")
            return False

        lat, lng = coords.lat, coords.lng

        # Rate limiting compliance: sleep a bit before calling Nominatim
        import time
        time.sleep(1.5)
        
        # Call Nominatim API
        url = f"https://nominatim.openstreetmap.org/reverse?lat={lat}&lon={lng}&format=json&addressdetails=1"
        headers = {"User-Agent": "WaymarkPersonalApp/1.1 (contact@waymark.test)"}
        
        try:
            response = requests.get(url, headers=headers, timeout=10)
            if response.status_code == 200:
                data = response.json()
                address = data.get("address", {})
                
                # Map Nominatim fields to our model
                # Vietnam specific mapping: 
                # admin1: Tỉnh/Thành phố trực thuộc Trung ương
                # admin2: Quận/Huyện/Thị xã/Thành phố thuộc tỉnh
                # admin3: Phường/Xã/Thị trấn
                
                address = data.get("address", {})
                memory.country = address.get("country")
                
                # Special handling for Vietnam City-Provinces
                vn_cities = {
                    "VN-SG": "Thành phố Hồ Chí Minh",
                    "VN-HN": "Thành phố Hà Nội",
                    "VN-DN": "Thành phố Đà Nẵng",
                    "VN-HP": "Thành phố Hải Phòng",
                    "VN-CT": "Thành phố Cần Thơ"
                }
                iso_code = address.get("ISO3166-2-lvl4")
                
                # Admin 1: Province/City
                memory.admin1 = (
                    vn_cities.get(iso_code) or
                    address.get("state") or 
                    address.get("province") or 
                    address.get("municipality") or
                    address.get("city") # Fallback
                )
                
                # Admin 2: District/County
                # If city was used for admin1, we try other fields for admin2
                memory.admin2 = (
                    address.get("district") or 
                    address.get("county") or 
                    address.get("city_district") or 
                    (address.get("city") if address.get("city") != memory.admin1 else None) or
                    address.get("suburb")
                )
                
                # Admin 3: Ward/Commune
                memory.admin3 = (
                    address.get("ward") or 
                    address.get("commune") or 
                    (address.get("suburb") if address.get("suburb") != memory.admin2 else None) or
                    address.get("village") or 
                    address.get("town") or
                    address.get("hamlet")
                )
                
                memory.village = (
                    address.get("neighbourhood") or 
                    address.get("hamlet") or 
                    address.get("quarter") or 
                    address.get("allotments")
                )
                
                memory.address_text = data.get("display_name")
                
                # Extract specific place name (restaurant, building, hotel, etc.)
                name_fields = ["restaurant", "cafe", "hotel", "amenity", "tourism", "shop", "office", "building", "historic"]
                p_name = None
                for field in name_fields:
                    if field in address:
                        p_name = address[field]
                        break
                
                # Fallback: if no specific field, use the first part of display_name 
                if not p_name and memory.address_text:
                    parts = memory.address_text.split(",")
                    if len(parts) > 0:
                        p_name = parts[0].strip()
                
                memory.place_name = p_name
                
                db.commit()
                print(f"Successfully reverse geocoded memory {memory_id}: {memory.address_text}")
            else:
                print(f"Failed to fetch geocoding data: HTTP {response.status_code}")
        except Exception as e:
            print(f"Request error for geocoding: {str(e)}")

    except Exception as e:
        db.rollback()
        print(f"Error during reverse geocoding for memory {memory_id}: {str(e)}")
    finally:
        db.close()

    return True
