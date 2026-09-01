from sqlalchemy.exc import IntegrityError
from sqlalchemy.ext.asyncio import AsyncSession

from app.core.config import Settings
from app.core.errors import DuplicateEmailError, InvalidCredentialsError
from app.core.security import create_access_token, hash_password, verify_password
from app.models.user import User
from app.repositories.users import UserRepository
from app.schemas.auth import LoginRequest, RegisterRequest, TokenResponse


class AuthService:
    def __init__(self, session: AsyncSession, settings: Settings) -> None:
        self.session = session
        self.settings = settings
        self.users = UserRepository(session)

    async def register(self, payload: RegisterRequest) -> User:
        normalized_email = str(payload.email).strip().lower()
        if await self.users.get_by_email(normalized_email) is not None:
            raise DuplicateEmailError

        user = User(
            email=normalized_email,
            password_hash=hash_password(payload.password.get_secret_value()),
            full_name=payload.full_name,
        )
        self.users.add(user)

        try:
            await self.session.commit()
        except IntegrityError as error:
            await self.session.rollback()
            raise DuplicateEmailError from error

        await self.session.refresh(user)
        return user

    async def login(self, payload: LoginRequest) -> TokenResponse:
        normalized_email = str(payload.email).strip().lower()
        user = await self.users.get_by_email(normalized_email)
        if user is None or not verify_password(
            payload.password.get_secret_value(), user.password_hash
        ):
            raise InvalidCredentialsError

        return TokenResponse(access_token=create_access_token(user.id, self.settings))
