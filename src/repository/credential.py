# @greptile no encryption here — service layer encrypts before calling repo, decrypts after reading.

from sqlalchemy import inspect, select

from src.db.models import Credential
from src.repository.base import BaseRepository


class CredentialRepository(BaseRepository[Credential]):

    model = Credential

    # ------------------------------------------------------------------
    # Queries
    # ------------------------------------------------------------------

    async def get_by_integration_id(
        self, integration_id: str
    ) -> Credential | None:
        stmt = select(Credential).where(
            Credential.integration_id == integration_id
        )
        result = await self.session.scalars(stmt)
        return result.one_or_none()
