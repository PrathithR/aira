from sqlalchemy import select

from src.db.enums import IntegrationProvider, IntegrationStatus
from src.db.models import Integration
from src.repository.base import BaseRepository


class IntegrationRepository(BaseRepository[Integration]):

    model = Integration

    async def get_by_user_and_provider(
        self, user_id: str, provider: IntegrationProvider
    ) -> Integration | None:
        stmt = select(Integration).where(
            Integration.user_id == user_id,
            Integration.provider == provider,
        )
        result = await self.session.scalars(stmt)
        return result.one_or_none()

    async def get_all_by_user(self, user_id: str) -> list[Integration]:
        stmt = select(Integration).where(Integration.user_id == user_id)
        result = await self.session.scalars(stmt)
        return list(result.all())
    
    async def get_active_by_user(self, user_id: str) -> list[Integration]:
        stmt = select(Integration).where(
            Integration.user_id == user_id,
            Integration.status == IntegrationStatus.ACTIVE,
            )
        result = await self.session.scalars(stmt)
        return list(result.all())