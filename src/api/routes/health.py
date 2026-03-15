from fastapi import APIRouter, Depends
from sqlalchemy import text
from sqlalchemy.ext.asyncio import AsyncSession

from src.db.session import get_session

router = APIRouter()

@router.get("/health")
async def health(session: AsyncSession = Depends(get_session)) -> dict:
    # Perform a simple database query to check connectivity
    await session.execute(text("SELECT 1"))
    return {"status": "ok"}
