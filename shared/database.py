from sqlalchemy.ext.asyncio import create_async_engine, AsyncSession, async_sessionmaker, AsyncEngine
from sqlalchemy.orm import declarative_base, DeclarativeMeta
import os
from typing import Any

# Default to Docker Compose service name 'postgres'
DATABASE_URL: str = os.getenv("DATABASE_URL", "postgresql+asyncpg://user:bg_password@postgres:5432/videodb")

engine: AsyncEngine = create_async_engine(DATABASE_URL, echo=False)
AsyncSessionLocal: async_sessionmaker[AsyncSession] = async_sessionmaker(engine, expire_on_commit=False, class_=AsyncSession)
Base: Any = declarative_base()

async def init_db() -> None:
    """
    Initialize database tables.
    """
    try:
        from shared import models # Ensure models are loaded so Base.metadata is populated
    except ImportError:
        import models
        
    async with engine.begin() as conn:
        await conn.run_sync(Base.metadata.create_all)
