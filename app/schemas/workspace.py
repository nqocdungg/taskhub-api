from datetime import datetime

from pydantic import BaseModel, ConfigDict, Field

from app.models.enums import WorkspaceMemberRole


class WorkspaceCreate(BaseModel):
    name: str = Field(min_length=1, max_length=255)


class WorkspaceUpdate(BaseModel):
    name: str | None = Field(default=None, min_length=1, max_length=255)


class WorkspaceResponse(BaseModel):
    model_config = ConfigDict(from_attributes=True)

    id: int
    name: str
    owner_id: int
    created_at: datetime


class WorkspaceMemberCreate(BaseModel):
    user_id: int = Field(gt=0)
    role: WorkspaceMemberRole = WorkspaceMemberRole.VIEWER


class WorkspaceMemberResponse(BaseModel):
    model_config = ConfigDict(from_attributes=True)

    workspace_id: int
    user_id: int
    role: WorkspaceMemberRole
