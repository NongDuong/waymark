import uuid
import os
from datetime import datetime
from app.database import SessionLocal
from app import models
from app.core.security import pwd_context

def main():
    db = SessionLocal()
    try:
        # 1. Reset all users to standard (is_admin = False)
        db.query(models.User).update({models.User.is_admin: False})
        db.commit()
        print("Successfully reset all users' is_admin status to False.")

        # 2. Setup the default admin account dynamically via environment variables
        admin_username = os.getenv("ADMIN_USERNAME", "admin")
        admin_email = os.getenv("ADMIN_EMAIL", "admin@waymark.vn")
        admin_password_plain = os.getenv("ADMIN_PASSWORD", "Admin@123456")
        
        
        # Check if username or email already exists
        existing_user = db.query(models.User).filter(
            (models.User.username == admin_username) | 
            (models.User.primary_email == admin_email)
        ).first()

        if existing_user:
            # Upgrade existing user to admin and reset password
            existing_user.username = admin_username
            existing_user.primary_email = admin_email
            existing_user.hashed_password = pwd_context.hash(admin_password_plain)
            existing_user.is_admin = True
            existing_user.status = 1  # Active
            db.commit()
            admin_user = existing_user
            print(f"Updated existing user '{admin_username}' to be the default Admin.")
        else:
            # Create a brand new admin user
            admin_id = uuid.uuid4()
            admin_user = models.User(
                id=admin_id,
                username=admin_username,
                primary_email=admin_email,
                hashed_password=pwd_context.hash(admin_password_plain),
                is_admin=True,
                status=1,  # Active
                email_verified_at=datetime.utcnow()
            )
            db.add(admin_user)
            db.commit()
            print(f"Created brand new default Admin user '{admin_username}'.")

        # 3. Create or update profile for admin
        profile = db.query(models.UserProfile).filter_by(user_id=admin_user.id).first()
        if not profile:
            profile = models.UserProfile(
                user_id=admin_user.id,
                display_name="Waymark System Admin",
                bio="Quản trị viên hệ thống tối cao"
            )
            db.add(profile)
            db.commit()
            print("Created Profile for the Admin user.")
        else:
            profile.display_name = "Waymark System Admin"
            db.commit()
            print("Updated Profile for the Admin user.")

        print("\n" + "="*50)
        print("SETUP DEFAULT ADMIN COMPLETE!")
        print(f"Username: {admin_username}")
        print(f"Email:    {admin_email}")
        print(f"Password: {admin_password_plain}")
        print("="*50)

    except Exception as e:
        db.rollback()
        print(f"Error executing script: {e}")
    finally:
        db.close()

if __name__ == "__main__":
    main()
