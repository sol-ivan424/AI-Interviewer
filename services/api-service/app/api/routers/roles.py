from fastapi import APIRouter

from app.core.enums import Level, Role
from app.schemas.roles import RoleResponse

router = APIRouter(prefix="/api/v1/roles", tags=["roles"])

ROLE_TITLES = {
    Role.BACKEND: "Backend-разработчик",
    Role.ML_ENGINEER: "ML-инженер",
    Role.LLM_ENGINEER: "LLM-инженер",
}


@router.get("", response_model=list[RoleResponse])
async def list_roles() -> list[RoleResponse]:
    levels = list(Level)
    return [
        RoleResponse(slug=role, title=title, levels=levels) for role, title in ROLE_TITLES.items()
    ]
