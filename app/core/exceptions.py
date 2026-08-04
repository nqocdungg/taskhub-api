from collections.abc import Mapping

from fastapi import FastAPI, Request, status
from fastapi.exceptions import RequestValidationError
from fastapi.responses import JSONResponse
from starlette.exceptions import HTTPException as StarletteHTTPException

ERROR_CODES = {
    status.HTTP_400_BAD_REQUEST: "BAD_REQUEST",
    status.HTTP_401_UNAUTHORIZED: "UNAUTHORIZED",
    status.HTTP_403_FORBIDDEN: "FORBIDDEN",
    status.HTTP_404_NOT_FOUND: "NOT_FOUND",
    status.HTTP_405_METHOD_NOT_ALLOWED: "METHOD_NOT_ALLOWED",
    status.HTTP_409_CONFLICT: "CONFLICT",
    status.HTTP_422_UNPROCESSABLE_ENTITY: "VALIDATION_ERROR",
    status.HTTP_500_INTERNAL_SERVER_ERROR: "INTERNAL_SERVER_ERROR",
}


def _error_code(status_code: int) -> str:
    return ERROR_CODES.get(status_code, "HTTP_ERROR")


def _error_response(
    *,
    status_code: int,
    code: str,
    message: str,
    headers: Mapping[str, str] | None = None,
) -> JSONResponse:
    return JSONResponse(
        status_code=status_code,
        content={"error": {"code": code, "message": message}},
        headers=headers,
    )


class AppError(Exception):
    def __init__(
        self,
        *,
        status_code: int,
        message: str,
        code: str | None = None,
        headers: Mapping[str, str] | None = None,
    ) -> None:
        super().__init__(message)
        self.status_code = status_code
        self.code = code or _error_code(status_code)
        self.message = message
        self.headers = headers


async def _app_error_handler(_: Request, error: Exception) -> JSONResponse:
    if not isinstance(error, AppError):
        raise TypeError("AppError handler received an invalid exception.")
    return _error_response(
        status_code=error.status_code,
        code=error.code,
        message=error.message,
        headers=error.headers,
    )


async def _validation_error_handler(
    _: Request,
    error: Exception,
) -> JSONResponse:
    if not isinstance(error, RequestValidationError):
        raise TypeError("Validation handler received an invalid exception.")
    return _error_response(
        status_code=status.HTTP_422_UNPROCESSABLE_ENTITY,
        code="VALIDATION_ERROR",
        message="Dữ liệu đầu vào không hợp lệ.",
    )


async def _http_error_handler(
    _: Request,
    error: Exception,
) -> JSONResponse:
    if not isinstance(error, StarletteHTTPException):
        raise TypeError("HTTP handler received an invalid exception.")
    message = (
        error.detail
        if isinstance(error.detail, str)
        else "Yêu cầu không thể được xử lý."
    )
    return _error_response(
        status_code=error.status_code,
        code=_error_code(error.status_code),
        message=message,
        headers=error.headers,
    )


async def _unexpected_error_handler(_: Request, __: Exception) -> JSONResponse:
    return _error_response(
        status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
        code="INTERNAL_SERVER_ERROR",
        message="Đã xảy ra lỗi nội bộ.",
    )


def register_exception_handlers(app: FastAPI) -> None:
    app.add_exception_handler(AppError, _app_error_handler)
    app.add_exception_handler(RequestValidationError, _validation_error_handler)
    app.add_exception_handler(StarletteHTTPException, _http_error_handler)
    app.add_exception_handler(Exception, _unexpected_error_handler)
