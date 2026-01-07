"""Shared application dependencies."""

from collections.abc import AsyncIterator
from typing import Optional
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy.orm import sessionmaker

AsyncSessionLocal: Optional[sessionmaker] = None
SESSION_NOT_INITIALIZED_ERROR = "Database session maker has not been initialized"


def init_session_maker(session_maker: sessionmaker) -> None:
    """Initialize the session maker used by dependency injection."""
    global AsyncSessionLocal
    AsyncSessionLocal = session_maker


async def get_session() -> AsyncIterator[AsyncSession]:
    """Provide a scoped async database session."""
    if AsyncSessionLocal is None:
        raise RuntimeError(SESSION_NOT_INITIALIZED_ERROR)
    async with AsyncSessionLocal() as session:
        yield session
