#!/usr/bin/env python3
"""
Initialize database with default admin user
Run this before starting the backend server
"""

from database import SessionLocal, User, Base, engine
from auth_utils import get_password_hash

# Create tables
Base.metadata.create_all(bind=engine)

# Create session
db = SessionLocal()

# Check if admin user exists
admin_user = db.query(User).filter(User.username == "admin").first()

if not admin_user:
    print("Creating default admin user...")
    admin = User(
        username="admin",
        password_hash=get_password_hash("Admin@12345"),  # Secure password
        role="admin",
        mfa_enabled=False
    )
    db.add(admin)
    db.commit()
    print("✓ Admin user created successfully!")
    print("  Username: admin")
    print("  Password: Admin@12345")
else:
    print("✓ Admin user already exists")

db.close()
