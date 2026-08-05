import pytest
from httpx import AsyncClient

from app.main import app

pytestmark = pytest.mark.asyncio(loop_scope="session")
API_PREFIX = "/api/v1"


async def test_openapi_documents_bearer_and_standard_errors() -> None:
    schema = app.openapi()
    task_operation = schema["paths"]["/api/v1/tasks/{task_id}"]["get"]
    login_operation = schema["paths"]["/api/v1/auth/login"]["post"]

    assert "BearerAuth" in schema["components"]["securitySchemes"]
    assert task_operation["security"] == [{"BearerAuth": []}]
    assert "security" not in login_operation
    assert all(
        str(status_code) in task_operation["responses"]
        for status_code in (400, 401, 403, 404, 405, 409, 422, 500)
    )
    assert "ErrorResponse" in schema["components"]["schemas"]


async def test_framework_404_and_405_use_standard_error_format(
    client: AsyncClient,
) -> None:
    not_found_response = await client.get("/missing-route")
    method_not_allowed_response = await client.delete(
        f"{API_PREFIX}/auth/login"
    )

    assert not_found_response.status_code == 404
    assert not_found_response.json()["error"]["code"] == "NOT_FOUND"
    assert method_not_allowed_response.status_code == 405
    assert (
        method_not_allowed_response.json()["error"]["code"]
        == "METHOD_NOT_ALLOWED"
    )


async def test_wrong_bearer_token_uses_standard_error_format(
    client: AsyncClient,
) -> None:
    response = await client.get(
        f"{API_PREFIX}/users/me",
        headers={"Authorization": "Bearer invalid-token"},
    )

    assert response.status_code == 401
    assert response.json() == {
        "error": {
            "code": "UNAUTHORIZED",
            "message": "Access token không hợp lệ hoặc đã hết hạn.",
        }
    }
