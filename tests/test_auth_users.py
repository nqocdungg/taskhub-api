import pytest
from httpx import AsyncClient

pytestmark = pytest.mark.asyncio(loop_scope="session")
API_PREFIX = "/api/v1"


async def test_register_login_profile_and_update(client: AsyncClient) -> None:
    register_response = await client.post(
        f"{API_PREFIX}/auth/register",
        json={
            "email": " USER@Example.com ",
            "full_name": "Test User",
            "password": "Password123!",
        },
    )
    assert register_response.status_code == 201
    registered_user = register_response.json()
    assert registered_user["email"] == "user@example.com"
    assert registered_user["role"] == "MEMBER"
    assert "hashed_password" not in registered_user

    login_response = await client.post(
        f"{API_PREFIX}/auth/login",
        json={"email": "user@example.com", "password": "Password123!"},
    )
    assert login_response.status_code == 200
    token = login_response.json()["access_token"]
    headers = {"Authorization": f"Bearer {token}"}

    profile_response = await client.get(
        f"{API_PREFIX}/users/me",
        headers=headers,
    )
    assert profile_response.status_code == 200
    assert profile_response.json()["id"] == registered_user["id"]

    update_response = await client.patch(
        f"{API_PREFIX}/users/me",
        headers=headers,
        json={"full_name": "Updated User"},
    )
    assert update_response.status_code == 200
    assert update_response.json()["full_name"] == "Updated User"


async def test_duplicate_email_and_invalid_payload_use_standard_errors(
    client: AsyncClient,
) -> None:
    payload = {
        "email": "duplicate@example.com",
        "full_name": "Duplicate User",
        "password": "Password123!",
    }
    first_response = await client.post(
        f"{API_PREFIX}/auth/register",
        json=payload,
    )
    duplicate_response = await client.post(
        f"{API_PREFIX}/auth/register",
        json=payload,
    )
    invalid_response = await client.post(
        f"{API_PREFIX}/auth/register",
        json={**payload, "email": "not-an-email"},
    )

    assert first_response.status_code == 201
    assert duplicate_response.status_code == 409
    assert duplicate_response.json()["error"]["code"] == "CONFLICT"
    assert invalid_response.status_code == 422
    assert invalid_response.json()["error"]["code"] == "VALIDATION_ERROR"


async def test_refresh_rotation_and_logout(client: AsyncClient, factory) -> None:
    user = await factory.create_user()

    refresh_response = await client.post(
        f"{API_PREFIX}/auth/refresh",
        json={"refresh_token": user.refresh_token},
    )
    assert refresh_response.status_code == 200
    rotated_refresh_token = refresh_response.json()["refresh_token"]
    assert rotated_refresh_token != user.refresh_token

    reused_response = await client.post(
        f"{API_PREFIX}/auth/refresh",
        json={"refresh_token": user.refresh_token},
    )
    assert reused_response.status_code == 401

    logout_response = await client.post(
        f"{API_PREFIX}/auth/logout",
        json={"refresh_token": rotated_refresh_token},
    )
    assert logout_response.status_code == 204

    revoked_response = await client.post(
        f"{API_PREFIX}/auth/refresh",
        json={"refresh_token": rotated_refresh_token},
    )
    assert revoked_response.status_code == 401


async def test_change_password_revokes_refresh_token(
    client: AsyncClient,
    factory,
) -> None:
    user = await factory.create_user()
    change_response = await client.post(
        f"{API_PREFIX}/users/me/change-password",
        headers=user.headers,
        json={
            "current_password": user.password,
            "new_password": "NewPassword123!",
        },
    )
    assert change_response.status_code == 204

    old_login_response = await client.post(
        f"{API_PREFIX}/auth/login",
        json={"email": user.email, "password": user.password},
    )
    new_login_response = await client.post(
        f"{API_PREFIX}/auth/login",
        json={"email": user.email, "password": "NewPassword123!"},
    )
    revoked_refresh_response = await client.post(
        f"{API_PREFIX}/auth/refresh",
        json={"refresh_token": user.refresh_token},
    )

    assert old_login_response.status_code == 401
    assert new_login_response.status_code == 200
    assert revoked_refresh_response.status_code == 401


async def test_protected_endpoint_requires_bearer_token(
    client: AsyncClient,
) -> None:
    response = await client.get(f"{API_PREFIX}/users/me")

    assert response.status_code == 401
    assert response.headers["www-authenticate"] == "Bearer"
    assert response.json()["error"]["code"] == "UNAUTHORIZED"
