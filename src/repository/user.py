from sqlalchemy import select

from src.db.models import User
from src.repository.base import BaseRepository


class UserRepository(BaseRepository[User]):

    model = User

    async def get_by_email(self, email: str) -> User | None:
        """Return a user by email or None if not found."""
        stmt = select(User).where(User.email == email)
        result = await self.session.scalars(stmt)
        return result.one_or_none()
    
    async def get_by_username(self, username: str) -> User | None:
        """Return a user by username or None if not found."""
        stmt = select(User).where(User.username == username)
        result = await self.session.scalars(stmt)
        return result.one_or_none()
    
    def __repr__(self) -> str:
        return f"User(id={self.id}, username={self.username})"
    