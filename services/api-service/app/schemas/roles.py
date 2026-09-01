from pydantic import BaseModel

from app.core.enums import Level, Role


class RoleResponse(BaseModel):
    slug: Role
    title: str
    levels: list[Level]
