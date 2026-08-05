from app.models.entities import User
from app.models.enums import UserRole, WorkspaceMemberRole

EDIT_ROLES = frozenset(
    {WorkspaceMemberRole.OWNER, WorkspaceMemberRole.EDITOR}
)


def is_admin(user: User) -> bool:
    return user.role is UserRole.ADMIN
