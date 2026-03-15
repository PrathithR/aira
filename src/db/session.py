# Async database engine and session management.


from collections.abc import AsyncGenerator

from sqlalchemy.ext.asyncio import (
    AsyncSession,
    async_sessionmaker,
    create_async_engine,
)

from src.settings import settings

# ---------------------------------------------------------------------------
# Engine
# ---------------------------------------------------------------------------
# connect_args is SQLite-specific; ignored by other dialects.
_connect_args = (
    {"check_same_thread": False}
    if settings.database_url.startswith("sqlite")
    else {}
)

engine = create_async_engine(
    settings.database_url,
    echo=settings.db_echo,          # set DB_ECHO=true in .env to see SQL logging
    connect_args=_connect_args,
)

# ---------------------------------------------------------------------------
# Session factory
# ---------------------------------------------------------------------------
# expire_on_commit=False means ORM objects remain usable after commit,
# which is important for async patterns where lazy-loading is unavailable.
AsyncSessionLocal = async_sessionmaker(
    bind=engine,
    class_=AsyncSession,
    expire_on_commit=False,
    autocommit=False,
    autoflush=False,
)


# ---------------------------------------------------------------------------
# FastAPI dependency
# ---------------------------------------------------------------------------
async def get_session() -> AsyncGenerator[AsyncSession, None]:
    """
    Yield a session that auto-rolls back on error.
    """
    async with AsyncSessionLocal() as session:
        try:
            yield session
            await session.commit()
        except Exception:
            await session.rollback()
            raise

# NOTE:
# If we introduce background jobs / scheduled tasks,
# add an async session_scope() context manager here.
