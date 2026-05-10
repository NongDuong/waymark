import sys
import os
from datetime import datetime, timezone, timedelta
import uuid

# Append parent directory to sys.path so we can import app modules
sys.path.append(os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

from app.database import SessionLocal
from app import models

def test_features():
    db = SessionLocal()
    print("Successfully connected to the database.")
    
    # Generate unique emails and usernames
    test_username_owner = f"owner_{uuid.uuid4().hex[:6]}"
    test_username_viewer = f"viewer_{uuid.uuid4().hex[:6]}"
    
    owner = None
    viewer = None
    memory = None
    
    try:
        # 1. Test is_vip default value on User creation
        print("\n--- 1. Testing Default is_vip Column on User ---")
        owner = models.User(
            id=uuid.uuid4(),
            username=test_username_owner,
            primary_email=f"{test_username_owner}@example.com",
            hashed_password="hashed_password_123"
        )
        viewer = models.User(
            id=uuid.uuid4(),
            username=test_username_viewer,
            primary_email=f"{test_username_viewer}@example.com",
            hashed_password="hashed_password_123"
        )
        db.add(owner)
        db.add(viewer)
        db.commit()
        
        db.refresh(owner)
        db.refresh(viewer)
        print(f"Created user '{owner.username}' with id: {owner.id}")
        print(f"User is_vip default value: {owner.is_vip} (Expected: False/0)")
        assert owner.is_vip is False, "is_vip must default to False"
        
        # 2. Test default visibility_expires_at on Memory creation
        print("\n--- 2. Testing Default visibility_expires_at on Memory ---")
        # POINT location
        wkt_point = "SRID=4326;POINT(105.8544 21.0285)"
        memory = models.Memory(
            id=uuid.uuid4(),
            user_id=owner.id,
            caption="Great view of Hanoi!",
            privacy_level=3, # Public
            location=wkt_point
        )
        db.add(memory)
        db.commit()
        db.refresh(memory)
        
        print(f"Created Memory '{memory.id}'")
        print(f"Memory posted_at: {memory.posted_at}")
        print(f"Memory visibility_expires_at: {memory.visibility_expires_at}")
        
        expected_expiry = memory.posted_at + timedelta(days=30)
        diff = abs((memory.visibility_expires_at - expected_expiry).total_seconds())
        print(f"Difference between visibility_expires_at and (posted_at + 30 days): {diff} seconds")
        assert diff < 5, "visibility_expires_at should default to posted_at + 30 days"
        
        # 3. Test Query Filtering: Unexpired memory
        print("\n--- 3. Testing Query Filtering on Unexpired Public Memory ---")
        # Search for public memories inside database for the viewer (not the owner)
        unexpired_query = db.query(models.Memory).filter(
            models.Memory.id == memory.id,
            (models.Memory.user_id == viewer.id) |
            ((models.Memory.privacy_level == 3) & (models.Memory.visibility_expires_at >= datetime.now(timezone.utc)))
        ).first()
        
        assert unexpired_query is not None, "Viewer should be able to see the unexpired public memory"
        print("Success: Viewer successfully found the unexpired memory!")
        
        # 4. Test Query Filtering: Expired memory
        print("\n--- 4. Testing Query Filtering on Expired Public Memory ---")
        # Simulating expiration: setting visibility_expires_at to 1 day ago
        memory.visibility_expires_at = datetime.now(timezone.utc) - timedelta(days=1)
        db.commit()
        db.refresh(memory)
        print(f"Expired memory visibility_expires_at set to: {memory.visibility_expires_at}")
        
        # Query from viewer's perspective (should not find it)
        expired_query_viewer = db.query(models.Memory).filter(
            models.Memory.id == memory.id,
            (models.Memory.user_id == viewer.id) |
            ((models.Memory.privacy_level == 3) & (models.Memory.visibility_expires_at >= datetime.now(timezone.utc)))
        ).first()
        
        assert expired_query_viewer is None, "Viewer should NOT see the expired public memory"
        print("Success: Viewer is blocked from seeing the expired memory.")
        
        # Query from owner's perspective (should always find it)
        expired_query_owner = db.query(models.Memory).filter(
            models.Memory.id == memory.id,
            (models.Memory.user_id == owner.id) |
            ((models.Memory.privacy_level == 3) & (models.Memory.visibility_expires_at >= datetime.now(timezone.utc)))
        ).first()
        
        assert expired_query_owner is not None, "Owner should still see their own expired memory"
        print("Success: Owner successfully retrieved their own expired memory.")
        
        # 5. Test Extending visibility
        print("\n--- 5. Testing Extending Memory Visibility ---")
        # Extend from current_expires (which is in the past, so it should extend from now)
        now = datetime.now(timezone.utc)
        current_expires = memory.visibility_expires_at or now
        if current_expires < now:
            current_expires = now
            
        memory.visibility_expires_at = current_expires + timedelta(days=30)
        db.commit()
        db.refresh(memory)
        
        print(f"Extended memory visibility_expires_at: {memory.visibility_expires_at}")
        expected_new_expiry = now + timedelta(days=30)
        diff_new = abs((memory.visibility_expires_at - expected_new_expiry).total_seconds())
        assert diff_new < 5, f"Extended expiry should be approximately {expected_new_expiry}"
        print("Success: Memory visibility was successfully extended by 30 days!")
        
        print("\nALL TESTS PASSED SUCCESSFULLY! ✅")
        
    finally:
        # Clean up database data
        print("\n--- Cleaning up test data ---")
        if memory:
            db.delete(memory)
        if owner:
            db.delete(owner)
        if viewer:
            db.delete(viewer)
        db.commit()
        db.close()
        print("Cleanup completed.")

if __name__ == "__main__":
    test_features()
