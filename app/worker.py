import os
import time
import json
from celery import Celery
from dotenv import load_dotenv

load_dotenv()

# Initialize Firebase Admin SDK once at module import
import firebase_admin
from firebase_admin import credentials as fb_credentials, messaging as fb_messaging

_firebase_initialized = False

def _init_firebase():
    global _firebase_initialized
    if _firebase_initialized:
        return
    try:
        # Priority 1: read from FIREBASE_SERVICE_ACCOUNT_JSON env var (production)
        sa_json = os.getenv("FIREBASE_SERVICE_ACCOUNT_JSON")
        if sa_json:
            sa_dict = json.loads(sa_json)
            cred = fb_credentials.Certificate(sa_dict)
        else:
            # Priority 2: fallback to local file (development only, never commit this file)
            sa_path = os.path.join(os.path.dirname(os.path.dirname(__file__)), "firebase_service_account.json")
            if not os.path.exists(sa_path):
                print("Firebase: no FIREBASE_SERVICE_ACCOUNT_JSON env var and no local file found. FCM disabled.")
                return
            cred = fb_credentials.Certificate(sa_path)

        firebase_admin.initialize_app(cred)
        _firebase_initialized = True
        print("Firebase Admin SDK initialized successfully.")
    except Exception as e:
        print(f"Firebase Admin SDK initialization failed: {e}")

_init_firebase()

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

_NOTIFICATION_TITLES = {
    1: "Lượt thích mới",
    2: "Bình luận mới",
    3: "Người theo dõi mới",
    4: "Tin nhắn mới",
}

@celery_app.task(name="tasks.send_notification")
def send_notification(
    user_id: str,
    message: str,
    sender_id: str = None,
    notification_type: int = 1,
    reference_id: str = None
):
    print(f"Sending notification to user {user_id}: {message}")

    from app.database import SessionLocal
    from app.models import Notification, DeviceToken
    import uuid as uuid_mod

    db = SessionLocal()
    try:
        # 1. Save notification record to DB
        notif = Notification(
            id=uuid_mod.uuid4(),
            user_id=uuid_mod.UUID(user_id),
            sender_id=uuid_mod.UUID(sender_id) if sender_id else None,
            notification_type=notification_type,
            message=message,
            reference_id=uuid_mod.UUID(reference_id) if reference_id else None,
            is_read=False
        )
        db.add(notif)
        db.commit()
        print(f"Notification saved to DB for user_id: {user_id}")

        # 2. Send FCM push notifications to all device tokens of the recipient
        device_tokens = db.query(DeviceToken).filter(
            DeviceToken.user_id == uuid_mod.UUID(user_id)
        ).all()

        if not device_tokens:
            print(f"No device tokens registered for user {user_id}, skipping FCM.")
            return True

        title = _NOTIFICATION_TITLES.get(notification_type, "Thông báo mới")
        data_payload = {
            "notification_type": str(notification_type),
            "reference_id": reference_id or "",
            "sender_id": sender_id or "",
        }

        failed_tokens = []
        for dt in device_tokens:
            try:
                msg = fb_messaging.Message(
                    notification=fb_messaging.Notification(title=title, body=message),
                    data=data_payload,
                    token=dt.token,
                )
                response = fb_messaging.send(msg)
                print(f"FCM sent to token {dt.token[:20]}...: {response}")
            except fb_messaging.UnregisteredError:
                print(f"FCM token expired/unregistered, removing: {dt.token[:20]}...")
                failed_tokens.append(dt.id)
            except Exception as e:
                print(f"FCM send error for token {dt.token[:20]}...: {e}")

        # Clean up expired tokens
        if failed_tokens:
            db.query(DeviceToken).filter(DeviceToken.id.in_(failed_tokens)).delete(synchronize_session=False)
            db.commit()

    except Exception as e:
        db.rollback()
        print(f"send_notification task error: {e}")
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
