from typing import Any

from app.schemas.error import ErrorResponse


def _error_response(
    description: str,
    code: str,
    message: str,
) -> dict[str, Any]:
    return {
        "model": ErrorResponse,
        "description": description,
        "content": {
            "application/json": {
                "example": {
                    "error": {
                        "code": code,
                        "message": message,
                    }
                }
            }
        },
    }


ERROR_RESPONSES: dict[int | str, dict[str, Any]] = {
    400: _error_response(
        "Yêu cầu không hợp lệ",
        "BAD_REQUEST",
        "Yêu cầu không hợp lệ.",
    ),
    401: _error_response(
        "Thiếu hoặc sai access token",
        "UNAUTHORIZED",
        "Access token không hợp lệ hoặc đã hết hạn.",
    ),
    403: _error_response(
        "Không đủ quyền truy cập resource",
        "FORBIDDEN",
        "Bạn không có quyền thực hiện thao tác này.",
    ),
    404: _error_response(
        "Không tìm thấy resource",
        "NOT_FOUND",
        "Resource không tồn tại.",
    ),
    405: _error_response(
        "HTTP method không được hỗ trợ",
        "METHOD_NOT_ALLOWED",
        "Method Not Allowed",
    ),
    409: _error_response(
        "Resource bị trùng hoặc xung đột",
        "CONFLICT",
        "Resource đã tồn tại.",
    ),
    422: _error_response(
        "Dữ liệu đầu vào không hợp lệ",
        "VALIDATION_ERROR",
        "Dữ liệu đầu vào không hợp lệ.",
    ),
    500: _error_response(
        "Lỗi nội bộ",
        "INTERNAL_SERVER_ERROR",
        "Đã xảy ra lỗi nội bộ.",
    ),
}
