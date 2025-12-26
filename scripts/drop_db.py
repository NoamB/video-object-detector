import asyncio
import sys
import os

# Add necessary paths to sys.path to allow importing from services
root_dir = os.path.abspath(os.path.join(os.path.dirname(__file__), ".."))
service_dir = os.path.join(root_dir, "services", "detection")
sys.path.append(service_dir)

try:
    from database import Base, engine
    # Import models to ensure metadata is aware of tables
    from models import DetectionResult
except ImportError as e:
    print(f"Error: Could not import database/models. Detail: {e}")
    sys.exit(1)

async def run_drop():
    print("WARNING: Dropping all tables...")
    async with engine.begin() as conn:
        await conn.run_sync(Base.metadata.drop_all)
    print("Database wiped successfully.")

if __name__ == "__main__":
    confirm = input("Are you sure you want to drop the database? (y/N): ")
    if confirm.lower() == 'y':
        asyncio.run(run_drop())
    else:
        print("Aborted.")
