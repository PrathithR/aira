from sqlalchemy import inspect, select

from src.db.models import Credential
from src.encryption import decrypt_value, encrypt_value
from src.repository.base import BaseRepository

_ENCRYPTED_FIELDS = (
    "access_token",
    "refresh_token",
    "api_key",
    "password",
    "webhook_secret",
)


class CredentialRepository(BaseRepository[Credential]):

    model = Credential

    # ------------------------------------------------------------------
    # Encryption helpers
    # ------------------------------------------------------------------

    @staticmethod
    def _encrypt(credential: Credential) -> None:
        for field in _ENCRYPTED_FIELDS:
            value = getattr(credential, field)
            if value is not None:
                setattr(credential, field, encrypt_value(value))

    @staticmethod
    def _decrypt(credential: Credential) -> None:
        for field in _ENCRYPTED_FIELDS:
            value = getattr(credential, field)
            if value is not None:
                setattr(credential, field, decrypt_value(value))

    def _expunge_and_decrypt(self, credential: Credential) -> None:
        self.session.expunge(credential)
        self._decrypt(credential)

    # ------------------------------------------------------------------
    # Overrides
    # ------------------------------------------------------------------

    async def get_by_id(self, entity_id: str) -> Credential | None:
        credential = await super().get_by_id(entity_id)
        if credential is not None:
            self._expunge_and_decrypt(credential)
        return credential

    async def get_all(self, limit: int | None = 100) -> list[Credential]:
        credentials = await super().get_all(limit)
        for cred in credentials:
            self._expunge_and_decrypt(cred)
        return credentials

    async def create(self, entity: Credential) -> Credential:
        self._encrypt(entity)
        try:
            await super().create(entity)
        except Exception:
            self._decrypt(entity)  # in case of error, restore to plaintext
            raise
        self._expunge_and_decrypt(entity)
        return entity

    async def delete(self, credential_id: str) -> None:  # type: ignore[override]
        credential = await self.session.get(Credential, credential_id)
        if credential is None:
            raise ValueError(f"Credential {credential_id} not found")
        await self.session.delete(credential)

    # ------------------------------------------------------------------
    # Queries
    # ------------------------------------------------------------------

    async def get_by_integration_id(
        self, integration_id: str
    ) -> list[Credential]:
        stmt = select(Credential).where(
            Credential.integration_id == integration_id
        )
        result = await self.session.scalars(stmt)
        credentials = list(result.all())
        for cred in credentials:
            self._expunge_and_decrypt(cred)
        return credentials

    async def get_primary_for_integration(
        self, integration_id: str
    ) -> Credential | None:
        stmt = select(Credential).where(
            Credential.integration_id == integration_id,
            Credential.is_primary.is_(True),
        )
        result = await self.session.scalars(stmt)
        credential = result.one_or_none()
        if credential is not None:
            self._expunge_and_decrypt(credential)
        return credential

    async def update_encrypted(self, credential_id: str, **fields) -> None:
        credential = await self.session.get(Credential, credential_id)
        if credential is None:
            raise ValueError(f"Credential {credential_id} not found")
        for key, value in fields.items():
            if key not in _ENCRYPTED_FIELDS:
                raise ValueError(f"Use update for {key}")
        for key, value in fields.items():
            setattr(credential, key, encrypt_value(value))

    async def update(self, credential_id: str, **fields) -> None:
        credential = await self.session.get(Credential, credential_id)
        if credential is None:
            raise ValueError(f"Credential {credential_id} not found")
        columns = {c.key for c in inspect(Credential).mapper.column_attrs}
        for key, value in fields.items():
            if key in _ENCRYPTED_FIELDS:
                raise ValueError(f"Use update_encrypted for {key}")
            if key not in columns:
                raise ValueError(f"Unknown field: {key}")
        for key, value in fields.items():    
            setattr(credential, key, value)
