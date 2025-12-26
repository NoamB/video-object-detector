import asyncio
import sys
import os

# Add relevant paths to sys.path
sys.path.append("/app")
sys.path.append(os.path.join(os.getcwd(), "services", "detection"))

try:
    from database import Base, engine
    # Import models to register them with Base.metadata
    from models import DetectionResult
except ImportError as e:
    print(f"Error: Could not import database/models. Detail: {e}")
    sys.exit(1)

async def run_init():
    print("Initializing database...")
    async with engine.begin() as conn:
        await conn.run_sync(Base.metadata.create_all)
    print("Database initialized successfully.")

if __name__ == "__main__":
    asyncio.run(run_init())
