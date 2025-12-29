import asyncio
import sys
import os

# Add relevant paths to sys.path
sys.path.append("/app")
sys.path.append(os.path.join(os.getcwd(), "services", "detection"))

try:
    from shared.database import Base, engine
    # Import models to ensure metadata is aware of tables
    from shared.models import DetectionResult
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
