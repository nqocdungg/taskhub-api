import pytest
from httpx import AsyncClient

pytestmark = pytest.mark.asyncio(loop_scope="session")
API_PREFIX = "/api/v1"


async def test_label_crud_and_task_assignment(
    client: AsyncClient,
    factory,
) -> None:
    owner = await factory.create_user(full_name="Owner")
    editor = await factory.create_user(full_name="Editor")
    viewer = await factory.create_user(full_name="Viewer")
    workspace = await factory.create_workspace(owner)
    await factory.invite_member(owner, workspace["id"], editor, "EDITOR")
    await factory.invite_member(owner, workspace["id"], viewer, "VIEWER")
    project = await factory.create_project(owner, workspace["id"])
    task = await factory.create_task(owner, project["id"])

    create_response = await client.post(
        f"{API_PREFIX}/projects/{project['id']}/labels",
        headers=editor.headers,
        json={"name": "Backend", "color": "#3366FF"},
    )
    assert create_response.status_code == 201
    label = create_response.json()

    viewer_list = await client.get(
        f"{API_PREFIX}/projects/{project['id']}/labels",
        headers=viewer.headers,
    )
    viewer_create = await client.post(
        f"{API_PREFIX}/projects/{project['id']}/labels",
        headers=viewer.headers,
        json={"name": "Forbidden", "color": "#000000"},
    )
    update_response = await client.patch(
        f"{API_PREFIX}/labels/{label['id']}",
        headers=editor.headers,
        json={"color": "#FF6633"},
    )
    attach_response = await client.post(
        f"{API_PREFIX}/tasks/{task['id']}/labels/{label['id']}",
        headers=editor.headers,
    )
    duplicate_attach = await client.post(
        f"{API_PREFIX}/tasks/{task['id']}/labels/{label['id']}",
        headers=editor.headers,
    )
    remove_response = await client.delete(
        f"{API_PREFIX}/tasks/{task['id']}/labels/{label['id']}",
        headers=editor.headers,
    )

    assert viewer_list.status_code == 200
    assert viewer_list.json()[0]["id"] == label["id"]
    assert viewer_create.status_code == 403
    assert update_response.status_code == 200
    assert update_response.json()["color"] == "#FF6633"
    assert attach_response.status_code == 201
    assert duplicate_attach.status_code == 409
    assert remove_response.status_code == 204


async def test_label_and_task_must_belong_to_same_project(
    client: AsyncClient,
    factory,
) -> None:
    owner = await factory.create_user(full_name="Owner")
    workspace = await factory.create_workspace(owner)
    first_project = await factory.create_project(
        owner,
        workspace["id"],
        name="First Project",
    )
    second_project = await factory.create_project(
        owner,
        workspace["id"],
        name="Second Project",
    )
    task = await factory.create_task(owner, first_project["id"])
    label_response = await client.post(
        f"{API_PREFIX}/projects/{second_project['id']}/labels",
        headers=owner.headers,
        json={"name": "Other project", "color": "#000000"},
    )
    label = label_response.json()

    attach_response = await client.post(
        f"{API_PREFIX}/tasks/{task['id']}/labels/{label['id']}",
        headers=owner.headers,
    )

    assert attach_response.status_code == 400
    assert attach_response.json()["error"]["code"] == "BAD_REQUEST"


async def test_comment_permissions(client: AsyncClient, factory) -> None:
    owner = await factory.create_user(full_name="Owner")
    first_editor = await factory.create_user(full_name="First Editor")
    second_editor = await factory.create_user(full_name="Second Editor")
    viewer = await factory.create_user(full_name="Viewer")
    admin = await factory.create_user(full_name="Admin")
    await factory.promote_admin(admin)
    workspace = await factory.create_workspace(owner)
    for member, role in (
        (first_editor, "EDITOR"),
        (second_editor, "EDITOR"),
        (viewer, "VIEWER"),
    ):
        await factory.invite_member(owner, workspace["id"], member, role)
    project = await factory.create_project(owner, workspace["id"])
    task = await factory.create_task(owner, project["id"])

    create_response = await client.post(
        f"{API_PREFIX}/tasks/{task['id']}/comments",
        headers=first_editor.headers,
        json={"content": "Please review this task."},
    )
    assert create_response.status_code == 201
    comment = create_response.json()

    viewer_create = await client.post(
        f"{API_PREFIX}/tasks/{task['id']}/comments",
        headers=viewer.headers,
        json={"content": "Viewer comment"},
    )
    other_editor_delete = await client.delete(
        f"{API_PREFIX}/comments/{comment['id']}",
        headers=second_editor.headers,
    )
    admin_delete = await client.delete(
        f"{API_PREFIX}/comments/{comment['id']}",
        headers=admin.headers,
    )

    assert viewer_create.status_code == 403
    assert other_editor_delete.status_code == 403
    assert admin_delete.status_code == 204


async def test_comment_author_can_delete_own_comment(
    client: AsyncClient,
    factory,
) -> None:
    owner = await factory.create_user(full_name="Owner")
    workspace = await factory.create_workspace(owner)
    project = await factory.create_project(owner, workspace["id"])
    task = await factory.create_task(owner, project["id"])
    create_response = await client.post(
        f"{API_PREFIX}/tasks/{task['id']}/comments",
        headers=owner.headers,
        json={"content": "Owner comment"},
    )

    delete_response = await client.delete(
        f"{API_PREFIX}/comments/{create_response.json()['id']}",
        headers=owner.headers,
    )

    assert delete_response.status_code == 204
