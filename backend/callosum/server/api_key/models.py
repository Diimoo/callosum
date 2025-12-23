from pydantic import BaseModel

from callosum.auth.schemas import UserRole


class APIKeyArgs(BaseModel):
    name: str | None = None
    role: UserRole = UserRole.BASIC
