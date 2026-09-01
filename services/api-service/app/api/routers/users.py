from fastapi import APIRouter

from app.api.dependencies import CurrentUserDependency
from app.schemas.users import UserResponse

router = APIRouter(prefix="/api/v1/users", tags=["users"])


@router.get("/me", response_model=UserResponse)
async def get_me(current_user: CurrentUserDependency) -> UserResponse:
    return UserResponse.model_validate(current_user)
