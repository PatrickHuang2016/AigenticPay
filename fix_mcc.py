from dotenv import load_dotenv
load_dotenv()
import sqlite3
from app.database import SessionLocal, engine
from app.models import User, UserMCC, Base

from sqlalchemy import text

# Fix missing columns (Works for both SQLite and PostgreSQL)
try:
    with engine.connect() as conn:
        conn.execute(text("ALTER TABLE user_mccs ADD COLUMN currency VARCHAR DEFAULT 'USD'"))
        conn.execute(text("ALTER TABLE limit_change_logs ADD COLUMN currency VARCHAR DEFAULT 'USD'"))
        conn.commit()
        print("Schema altered successfully.")
except Exception as e:
    print("Columns may already exist or error:", e)

# Ensure tables exist
Base.metadata.create_all(bind=engine)

def fix_mccs():
    db = SessionLocal()
    users = db.query(User).all()
    default_mccs = [
        ("5411", "Grocery Stores", 200.0),
        ("5812", "Restaurants", 100.0),
        ("5814", "Fast Food", 50.0),
        ("5541", "Gas Stations", 100.0),
        ("4121", "Ride Shares", 50.0),
        ("5311", "Retail Stores", 300.0)
    ]
    
    for user in users:
        existing_mccs = db.query(UserMCC).filter(UserMCC.user_id == user.id).all()
        if not existing_mccs:
            for code, desc, limit in default_mccs:
                db.add(UserMCC(user_id=user.id, mcc_code=code, description=desc, limit=round(limit, 2), currency="USD"))
            print(f"Added default MCCs for user: {user.email}")
        else:
            print(f"User {user.email} already has MCCs.")
            
    db.commit()
    db.close()

if __name__ == "__main__":
    fix_mccs()

if __name__ == "__main__":
    fix_mccs()
