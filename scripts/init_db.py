import asyncio
import sys
import os

# Add necessary paths to sys.path to allow importing from services
root_dir = os.path.abspath(os.path.join(os.path.dirname(__file__), ".."))
service_dir = os.path.join(root_dir, "services", "detection")
sys.path.append(service_dir)

try:
    from database import Base, engine
    # Import models to register them with Base.metadata
    from models import DetectionResult
except ImportError as e:
    print(f"Error: Could not import database/models. Ensure you are running from the project root. Detail: {e}")
    sys.exit(1)

async def run_init():
    print("Initializing database...")
    async with engine.begin() as conn:
        await conn.run_sync(Base.metadata.create_all)
    print("Database initialized successfully.")

if __name__ == "__main__":
    asyncio.run(run_init())
