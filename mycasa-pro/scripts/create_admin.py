#!/usr/bin/env python3
"""
Create initial admin user for MyCasa Pro
"""
from auth.security import get_password_hash
from config.settings import DEFAULT_TENANT_ID
from database import get_db
from database.models import User

def create_admin_user(username: str, email: str, password: str):
    with get_db() as db:
        # Check if user already exists
        existing = db.query(User).filter(User.username == username).first()
        if existing:
            print(f"User {username} already exists")
            return
        
        # Create new admin user
        user = User(
            username=username,
            email=email,
            hashed_password=get_password_hash(password),
            is_admin=True,
            is_active=True,
            tenant_id=DEFAULT_TENANT_ID,
        )
        db.add(user)
        db.commit()
        print(f"Admin user {username} created successfully")

if __name__ == "__main__":
    import sys
    if len(sys.argv) != 4:
        print("Usage: python create_admin.py <username> <email> <password>")
        sys.exit(1)
    
    username = sys.argv[1]
    email = sys.argv[2]
    password = sys.argv[3]
    
    create_admin_user(username, email, password)
