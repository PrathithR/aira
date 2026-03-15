from typing import Generic, TypeVar

from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

from src.db.base import Base

T = TypeVar("T", bound=Base)


class BaseRepository(Generic[T]):
    """
    Typed base repository. Concrete repos inherit and get CRUD for free.

    Transaction rules:
    - Never commit. Only get_db (or equivalent session owner) commits.
    - create() explicitly flushes for IDs. No other repo method explicitly flushes.
    """

    model: type[T]

    def __init_subclass__(cls, **kwargs: object) -> None:
        super().__init_subclass__(**kwargs)
        if not hasattr(cls, "model") or cls.model is None:
            raise TypeError(f"{cls.__name__} must define a 'model' class attribute")

    def __init__(self, session: AsyncSession) -> None:
        self.session = session

    async def get_by_id(self, entity_id: str) -> T | None:
        return await self.session.get(self.model, entity_id)

    async def get_all(self, limit: int | None = None) -> list[T]:
        stmt = select(self.model)
        if limit is not None:
            stmt = stmt.limit(limit)
        result = await self.session.scalars(stmt)
        return list(result)

    async def create(self, entity: T) -> T:
        self.session.add(entity)
        await self.session.flush()
        return entity

    async def delete(self, entity: T) -> None:
        await self.session.delete(entity)
        