from typing import Any

import pytest
from httpx import AsyncClient

from app.core.cache import redis_client
from app.services.notification import EmailNotificationService

pytestmark = pytest.mark.asyncio(loop_scope="session")
API_PREFIX = "/api/v1"


async def test_task_crud_and_created_by(client: AsyncClient, factory) -> None:
    owner = await factory.create_user(full_name="Owner")
    workspace = await factory.create_workspace(owner)
    project = await factory.create_project(owner, workspace["id"])

    create_response = await client.post(
        f"{API_PREFIX}/projects/{project['id']}/tasks",
        headers=owner.headers,
        json={
            "title": "CRUD Task",
            "created_by": 9999,
            "priority": "HIGH",
        },
    )
    assert create_response.status_code == 201
    task = create_response.json()
    assert task["created_by"] == owner.id

    get_response = await client.get(
        f"{API_PREFIX}/tasks/{task['id']}",
        headers=owner.headers,
    )
    update_response = await client.patch(
        f"{API_PREFIX}/tasks/{task['id']}",
        headers=owner.headers,
        json={"title": "Updated Task", "status": "IN_PROGRESS"},
    )
    delete_response = await client.delete(
        f"{API_PREFIX}/tasks/{task['id']}",
        headers=owner.headers,
    )
    missing_response = await client.get(
        f"{API_PREFIX}/tasks/{task['id']}",
        headers=owner.headers,
    )

    assert get_response.status_code == 200
    assert update_response.status_code == 200
    assert update_response.json()["title"] == "Updated Task"
    assert update_response.json()["status"] == "IN_PROGRESS"
    assert delete_response.status_code == 204
    assert missing_response.status_code == 404


async def test_task_assignee_and_role_permissions(
    client: AsyncClient,
    factory,
) -> None:
    owner = await factory.create_user(full_name="Owner")
    editor = await factory.create_user(full_name="Editor")
    viewer = await factory.create_user(full_name="Viewer")
    outsider = await factory.create_user(full_name="Outsider")
    workspace = await factory.create_workspace(owner)
    workspace_id = workspace["id"]
    await factory.invite_member(owner, workspace_id, editor, "EDITOR")
    await factory.invite_member(owner, workspace_id, viewer, "VIEWER")
    project = await factory.create_project(owner, workspace_id)
    task = await factory.create_task(
        editor,
        project["id"],
        assignee_id=viewer.id,
    )

    viewer_list = await client.get(
        f"{API_PREFIX}/projects/{project['id']}/tasks",
        headers=viewer.headers,
    )
    viewer_update = await client.patch(
        f"{API_PREFIX}/tasks/{task['id']}",
        headers=viewer.headers,
        json={"title": "Forbidden"},
    )
    outsider_list = await client.get(
        f"{API_PREFIX}/projects/{project['id']}/tasks",
        headers=outsider.headers,
    )
    invalid_assignee = await client.patch(
        f"{API_PREFIX}/tasks/{task['id']}",
        headers=owner.headers,
        json={"assignee_id": outsider.id},
    )

    assert viewer_list.status_code == 200
    assert viewer_update.status_code == 403
    assert outsider_list.status_code == 403
    assert invalid_assignee.status_code == 400


async def test_task_filtering_and_pagination(
    client: AsyncClient,
    factory,
) -> None:
    owner = await factory.create_user(full_name="Owner")
    assignee = await factory.create_user(full_name="Assignee")
    workspace = await factory.create_workspace(owner)
    await factory.invite_member(owner, workspace["id"], assignee, "EDITOR")
    project = await factory.create_project(owner, workspace["id"])

    await factory.create_task(
        owner,
        project["id"],
        title="High todo",
        assignee_id=assignee.id,
        status="TODO",
        priority="HIGH",
    )
    await factory.create_task(
        owner,
        project["id"],
        title="Low done",
        status="DONE",
        priority="LOW",
    )
    await factory.create_task(
        owner,
        project["id"],
        title="Medium todo",
        status="TODO",
        priority="MEDIUM",
    )

    filtered_response = await client.get(
        f"{API_PREFIX}/projects/{project['id']}/tasks",
        headers=owner.headers,
        params={
            "status": "TODO",
            "priority": "HIGH",
            "assignee_id": assignee.id,
        },
    )
    first_page = await client.get(
        f"{API_PREFIX}/projects/{project['id']}/tasks",
        headers=owner.headers,
        params={"page": 1, "limit": 2},
    )
    second_page = await client.get(
        f"{API_PREFIX}/projects/{project['id']}/tasks",
        headers=owner.headers,
        params={"page": 2, "limit": 2},
    )

    assert [task["title"] for task in filtered_response.json()] == ["High todo"]
    assert len(first_page.json()) == 2
    assert len(second_page.json()) == 1


async def test_task_cache_is_invalidated_by_task_and_project_changes(
    client: AsyncClient,
    factory,
) -> None:
    owner = await factory.create_user(full_name="Owner")
    workspace = await factory.create_workspace(owner)
    project = await factory.create_project(owner, workspace["id"])
    task = await factory.create_task(owner, project["id"])
    pattern = f"taskhub:projects:{project['id']}:tasks:*"

    list_response = await client.get(
        f"{API_PREFIX}/projects/{project['id']}/tasks",
        headers=owner.headers,
    )
    keys_after_list = [key async for key in redis_client.scan_iter(match=pattern)]

    update_response = await client.patch(
        f"{API_PREFIX}/tasks/{task['id']}",
        headers=owner.headers,
        json={"title": "Invalidate cache"},
    )
    keys_after_update = [
        key async for key in redis_client.scan_iter(match=pattern)
    ]

    await client.get(
        f"{API_PREFIX}/projects/{project['id']}/tasks",
        headers=owner.headers,
    )
    delete_project_response = await client.delete(
        f"{API_PREFIX}/projects/{project['id']}",
        headers=owner.headers,
    )
    keys_after_project_delete = [
        key async for key in redis_client.scan_iter(match=pattern)
    ]

    assert list_response.status_code == 200
    assert len(keys_after_list) == 1
    assert update_response.status_code == 200
    assert keys_after_update == []
    assert delete_project_response.status_code == 204
    assert keys_after_project_delete == []


async def test_assignment_email_runs_only_when_assignee_changes(
    client: AsyncClient,
    factory,
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    sent_messages: list[dict[str, Any]] = []

    def fake_send(
        _service: EmailNotificationService,
        **message: Any,
    ) -> None:
        sent_messages.append(message)

    monkeypatch.setattr(
        EmailNotificationService,
        "send_task_assignment_email",
        fake_send,
    )

    owner = await factory.create_user(full_name="Owner")
    first_assignee = await factory.create_user(full_name="First Assignee")
    second_assignee = await factory.create_user(full_name="Second Assignee")
    workspace = await factory.create_workspace(owner)
    await factory.invite_member(
        owner,
        workspace["id"],
        first_assignee,
        "EDITOR",
    )
    await factory.invite_member(
        owner,
        workspace["id"],
        second_assignee,
        "EDITOR",
    )
    project = await factory.create_project(owner, workspace["id"])
    task = await factory.create_task(
        owner,
        project["id"],
        assignee_id=first_assignee.id,
    )
    assert len(sent_messages) == 1
    assert sent_messages[0]["recipient_email"] == first_assignee.email

    title_update = await client.patch(
        f"{API_PREFIX}/tasks/{task['id']}",
        headers=owner.headers,
        json={"title": "No new notification"},
    )
    same_assignee_update = await client.patch(
        f"{API_PREFIX}/tasks/{task['id']}",
        headers=owner.headers,
        json={"assignee_id": first_assignee.id},
    )
    new_assignee_update = await client.patch(
        f"{API_PREFIX}/tasks/{task['id']}",
        headers=owner.headers,
        json={"assignee_id": second_assignee.id},
    )

    assert title_update.status_code == 200
    assert same_assignee_update.status_code == 200
    assert new_assignee_update.status_code == 200
    assert len(sent_messages) == 2
    assert sent_messages[1]["recipient_email"] == second_assignee.email


async def test_task_validation_and_not_found_errors(
    client: AsyncClient,
    factory,
) -> None:
    user = await factory.create_user()
    missing_response = await client.get(
        f"{API_PREFIX}/tasks/99999",
        headers=user.headers,
    )
    invalid_query_response = await client.get(
        f"{API_PREFIX}/projects/1/tasks",
        headers=user.headers,
        params={"page": 0, "limit": 101},
    )

    assert missing_response.status_code == 404
    assert missing_response.json()["error"]["code"] == "NOT_FOUND"
    assert invalid_query_response.status_code == 422
    assert invalid_query_response.json()["error"]["code"] == "VALIDATION_ERROR"
