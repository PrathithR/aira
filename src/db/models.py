"""
AIRA — Database Models

Tables: users, integrations, credentials
Encrypted fields: access_token, refresh_token, api_key, password, webhook_secret
All timestamps UTC.
"""

import uuid
from datetime import datetime, timezone

from sqlalchemy import (
    JSON,
    Boolean,
    DateTime,
    Enum,
    ForeignKey,
    Index,
    String,
    Text,
    UniqueConstraint,
)
from sqlalchemy.orm import Mapped, mapped_column, relationship

from src.db.base import Base
from src.db.enums import (
    AuthType,
    CredentialStatus,
    IntegrationProvider,
    IntegrationStatus,
)


def _utcnow() -> datetime:
    return datetime.now(timezone.utc)


# ──────────────────────────────────────────────
#  Users
# ──────────────────────────────────────────────

class User(Base):
    __tablename__ = "users"

    id: Mapped[str] = mapped_column(
        String(36), primary_key=True, default=lambda: str(uuid.uuid4()),
    )
    email: Mapped[str] = mapped_column(String(255), unique=True, nullable=False)
    display_name: Mapped[str | None] = mapped_column(String(100), nullable=True)
    timezone: Mapped[str] = mapped_column(String(50), nullable=False, default="UTC")
    created_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True), nullable=False, default=_utcnow,
    )
    updated_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True), nullable=False, default=_utcnow, onupdate=_utcnow,
    )

    # Relationships
    integrations: Mapped[list["Integration"]] = relationship(
        back_populates="user", cascade="all, delete-orphan", lazy="selectin",
    )


# ──────────────────────────────────────────────
#  Integrations
# ──────────────────────────────────────────────

class Integration(Base):
    """
    Logical connection between a user and an external service.
    Separated from credentials because:
    - integration lifecycle (connect/disconnect)
    - credential lifecycle (expire/refresh)
    """
    __tablename__ = "integrations"
    __table_args__ = (
        UniqueConstraint("user_id", "provider", name="uq_user_provider"),
        Index("ix_integrations_user_provider", "user_id", "provider"),
    )

    id: Mapped[str] = mapped_column(
        String(36), primary_key=True, default=lambda: str(uuid.uuid4()),
    )
    user_id: Mapped[str] = mapped_column(
        String(36), ForeignKey("users.id", ondelete="CASCADE"), nullable=False,
    )
    provider: Mapped[IntegrationProvider] = mapped_column(
        Enum(IntegrationProvider, name="integration_provider",
             values_callable=lambda e: [m.value for m in e]),
        nullable=False,
    )
    auth_type: Mapped[AuthType] = mapped_column(
        Enum(AuthType, name="auth_type",
             values_callable=lambda e: [m.value for m in e]),
        nullable=False,
    )
    scopes: Mapped[str | None] = mapped_column(String(500), nullable=True)
    status: Mapped[IntegrationStatus] = mapped_column(
        Enum(IntegrationStatus, name="integration_status",
             values_callable=lambda e: [m.value for m in e]),
        nullable=False,
        default=IntegrationStatus.ACTIVE,
    )
    config: Mapped[dict | None] = mapped_column(JSON, nullable=True)
    created_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True), nullable=False, default=_utcnow,
    )
    updated_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True), nullable=False, default=_utcnow, onupdate=_utcnow,
    )

    # Relationships
    user: Mapped["User"] = relationship(back_populates="integrations")
    credentials: Mapped[list["Credential"]] = relationship(
        back_populates="integration", cascade="all, delete-orphan", lazy="selectin",
    )


# ──────────────────────────────────────────────
#  Credentials
# ──────────────────────────────────────────────

class Credential(Base):
    """
    Authentication secrets for an integration.

    ENCRYPTED at rest (Fernet AES-128-CBC + HMAC):
        access_token, refresh_token, api_key, password, webhook_secret

    NOT encrypted (not secrets):
        username, webhook_url

    Which fields are populated depends on parent integration's auth_type:
        oauth2   → access_token, refresh_token, token_expiry
        api_key  → api_key
        user_pwd → username, password
        webhook  → webhook_url, webhook_secret

    No direct FK to users. Ownership chain: credential → integration → user.
    """
    __tablename__ = "credentials"
    __table_args__ = (
        Index("ix_credentials_integration_primary", "integration_id", "is_primary"),
    )

    id: Mapped[str] = mapped_column(
        String(36), primary_key=True, default=lambda: str(uuid.uuid4()),
    )
    integration_id: Mapped[str] = mapped_column(
        String(36), ForeignKey("integrations.id", ondelete="CASCADE"), nullable=False,
    )

    # OAuth2 (access_token + refresh_token encrypted)
    access_token: Mapped[str | None] = mapped_column(Text, nullable=True)
    refresh_token: Mapped[str | None] = mapped_column(Text, nullable=True)
    token_expiry: Mapped[datetime | None] = mapped_column(
        DateTime(timezone=True), nullable=True,
    )

    # API key (encrypted)
    api_key: Mapped[str | None] = mapped_column(Text, nullable=True)

    # Username/password (password encrypted, username not)
    username: Mapped[str | None] = mapped_column(Text, nullable=True)
    password: Mapped[str | None] = mapped_column(Text, nullable=True)

    # Webhook (webhook_secret encrypted, webhook_url not)
    webhook_url: Mapped[str | None] = mapped_column(Text, nullable=True)
    webhook_secret: Mapped[str | None] = mapped_column(Text, nullable=True)

    # State
    status: Mapped[CredentialStatus] = mapped_column(
        Enum(CredentialStatus, name="credential_status",
             values_callable=lambda e: [m.value for m in e]),
        nullable=False,
        default=CredentialStatus.ACTIVE,
    )
    is_primary: Mapped[bool] = mapped_column(Boolean, nullable=False, default=True)
    created_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True), nullable=False, default=_utcnow,
    )
    updated_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True), nullable=False, default=_utcnow, onupdate=_utcnow,
    )

    # Relationships
    integration: Mapped["Integration"] = relationship(back_populates="credentials")

    #Override repr to avoid accidentally logging secrets
    def __repr__(self) -> str:
        return (
            f"Credential(id={self.id}, integration_id={self.integration_id}, "
            f"status={self.status}, is_primary={self.is_primary}, "
            f"created_at={self.created_at}, updated_at={self.updated_at})"
        )