import pytest
from httpx import AsyncClient

pytestmark = pytest.mark.asyncio(loop_scope="session")
API_PREFIX = "/api/v1"


async def test_workspace_access_matrix(client: AsyncClient, factory) -> None:
    owner = await factory.create_user(full_name="Owner")
    editor = await factory.create_user(full_name="Editor")
    viewer = await factory.create_user(full_name="Viewer")
    outsider = await factory.create_user(full_name="Outsider")
    admin = await factory.create_user(full_name="Admin")
    await factory.promote_admin(admin)

    workspace = await factory.create_workspace(owner)
    workspace_id = workspace["id"]
    await factory.invite_member(owner, workspace_id, editor, "EDITOR")
    await factory.invite_member(owner, workspace_id, viewer, "VIEWER")

    viewer_get = await client.get(
        f"{API_PREFIX}/workspaces/{workspace_id}",
        headers=viewer.headers,
    )
    outsider_get = await client.get(
        f"{API_PREFIX}/workspaces/{workspace_id}",
        headers=outsider.headers,
    )
    editor_update = await client.patch(
        f"{API_PREFIX}/workspaces/{workspace_id}",
        headers=editor.headers,
        json={"name": "Forbidden update"},
    )
    owner_update = await client.patch(
        f"{API_PREFIX}/workspaces/{workspace_id}",
        headers=owner.headers,
        json={"name": "Owner update"},
    )
    admin_get = await client.get(
        f"{API_PREFIX}/workspaces/{workspace_id}",
        headers=admin.headers,
    )
    admin_list = await client.get(
        f"{API_PREFIX}/workspaces",
        headers=admin.headers,
    )

    assert viewer_get.status_code == 200
    assert outsider_get.status_code == 403
    assert editor_update.status_code == 403
    assert owner_update.status_code == 200
    assert admin_get.status_code == 200
    assert [item["id"] for item in admin_list.json()] == [workspace_id]


async def test_only_owner_or_admin_can_manage_members(
    client: AsyncClient,
    factory,
) -> None:
    owner = await factory.create_user(full_name="Owner")
    editor = await factory.create_user(full_name="Editor")
    target = await factory.create_user(full_name="Target")
    workspace = await factory.create_workspace(owner)
    workspace_id = workspace["id"]
    await factory.invite_member(owner, workspace_id, editor, "EDITOR")

    forbidden_invite = await client.post(
        f"{API_PREFIX}/workspaces/{workspace_id}/members",
        headers=editor.headers,
        json={"user_id": target.id, "role": "VIEWER"},
    )
    owner_invite = await client.post(
        f"{API_PREFIX}/workspaces/{workspace_id}/members",
        headers=owner.headers,
        json={"user_id": target.id, "role": "VIEWER"},
    )
    remove_owner = await client.delete(
        f"{API_PREFIX}/workspaces/{workspace_id}/members/{owner.id}",
        headers=owner.headers,
    )
    remove_target = await client.delete(
        f"{API_PREFIX}/workspaces/{workspace_id}/members/{target.id}",
        headers=owner.headers,
    )

    assert forbidden_invite.status_code == 403
    assert owner_invite.status_code == 201
    assert remove_owner.status_code == 400
    assert remove_target.status_code == 204


async def test_project_permissions(client: AsyncClient, factory) -> None:
    owner = await factory.create_user(full_name="Owner")
    editor = await factory.create_user(full_name="Editor")
    viewer = await factory.create_user(full_name="Viewer")
    outsider = await factory.create_user(full_name="Outsider")
    admin = await factory.create_user(full_name="Admin")
    await factory.promote_admin(admin)

    workspace = await factory.create_workspace(owner)
    workspace_id = workspace["id"]
    await factory.invite_member(owner, workspace_id, editor, "EDITOR")
    await factory.invite_member(owner, workspace_id, viewer, "VIEWER")
    project = await factory.create_project(owner, workspace_id)
    project_id = project["id"]

    viewer_get = await client.get(
        f"{API_PREFIX}/projects/{project_id}",
        headers=viewer.headers,
    )
    viewer_create = await client.post(
        f"{API_PREFIX}/workspaces/{workspace_id}/projects",
        headers=viewer.headers,
        json={"name": "Viewer Project"},
    )
    editor_update = await client.patch(
        f"{API_PREFIX}/projects/{project_id}",
        headers=editor.headers,
        json={"name": "Editor update"},
    )
    editor_archive = await client.patch(
        f"{API_PREFIX}/projects/{project_id}/archive",
        headers=editor.headers,
    )
    outsider_get = await client.get(
        f"{API_PREFIX}/projects/{project_id}",
        headers=outsider.headers,
    )
    admin_create = await client.post(
        f"{API_PREFIX}/workspaces/{workspace_id}/projects",
        headers=admin.headers,
        json={"name": "Admin Project"},
    )

    assert viewer_get.status_code == 200
    assert viewer_create.status_code == 403
    assert editor_update.status_code == 200
    assert editor_archive.status_code == 200
    assert editor_archive.json()["status"] == "ARCHIVED"
    assert outsider_get.status_code == 403
    assert admin_create.status_code == 201
