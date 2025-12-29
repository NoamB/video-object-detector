from sqlalchemy.ext.asyncio import create_async_engine, AsyncSession, async_sessionmaker
from sqlalchemy.orm import declarative_base
import os

# Default to Docker Compose service name 'postgres'
DATABASE_URL = os.getenv("DATABASE_URL", "postgresql+asyncpg://user:bg_password@postgres:5432/videodb")

engine = create_async_engine(DATABASE_URL, echo=False)
AsyncSessionLocal = async_sessionmaker(engine, expire_on_commit=False, class_=AsyncSession)
Base = declarative_base()

async def init_db():
    """
    Initialize database tables.
    """
    try:
        from shared import models # Ensure models are loaded so Base.metadata is populated
    except ImportError:
        import models
        
    async with engine.begin() as conn:
        await conn.run_sync(Base.metadata.create_all)
