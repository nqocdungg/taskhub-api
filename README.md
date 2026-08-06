# TaskHub API

TaskHub là REST API quản lý công việc theo luồng `User → Workspace → Project →
Task`. Ứng dụng hỗ trợ xác thực JWT, phân quyền theo workspace, label, comment,
lọc/phân trang task, cache Redis và email thông báo khi giao task.

## Tech stack

- Python 3.12, FastAPI, Pydantic v2 và pydantic-settings.
- SQLAlchemy 2.x async, PostgreSQL 16 và Alembic.
- Redis 7, JWT, bcrypt và FastAPI BackgroundTasks.
- Docker Compose, Ruff, mypy và pytest.

## Kiến trúc

Project dùng Layered Architecture:

```text
app/
├── api/v1/        # Router, endpoint và dependency injection
├── core/          # Configuration, security, cache, exception, logging
├── db/            # Engine và AsyncSession
├── models/        # SQLAlchemy entities và enum
├── repositories/  # Truy cập dữ liệu
├── schemas/       # Pydantic request/response schemas
└── services/      # Business logic và authorization
```

Endpoint chỉ xử lý HTTP, service giữ business rule và repository làm việc với
database. Schema được quản lý duy nhất bằng Alembic, không dùng `create_all`.

## Chạy bằng Docker Compose

Yêu cầu: Docker Desktop và Docker Compose.

```powershell
Copy-Item .env.example .env
```

Đổi `JWT_SECRET_KEY` trong `.env` thành một chuỗi bí mật dài, sau đó chạy:

```powershell
docker compose up -d --build
docker compose ps
```

Container app chờ PostgreSQL và Redis healthy, tự chạy `alembic upgrade head`,
sau đó khởi động Uvicorn. Truy cập:

- Swagger UI: `http://localhost:8000/docs`
- ReDoc: `http://localhost:8000/redoc`
- OpenAPI JSON: `http://localhost:8000/openapi.json`

Dừng stack nhưng giữ dữ liệu bằng `docker compose down`. Chỉ thêm `-v` khi muốn
xóa cả dữ liệu PostgreSQL và Redis.

## Chạy local

Yêu cầu: Python 3.12, Docker Desktop và PowerShell.

```powershell
python -m venv venv
.\venv\Scripts\Activate.ps1
python -m pip install -r requirements-dev.txt
Copy-Item .env.example .env
docker compose up -d db redis
python -m alembic upgrade head
python -m uvicorn app.main:app --reload
```

## Cấu hình môi trường

Ứng dụng fail-fast khi thiếu hoặc sai cấu hình bắt buộc.

| Biến | Bắt buộc | Mặc định / ví dụ | Mục đích |
|---|---:|---|---|
| `APP_ENV` | Không | `local` | `local`, `development`, `test`, `staging`, `production` |
| `DATABASE_URL` | Có | URL trong `.env.example` | PostgreSQL async URL |
| `REDIS_URL` | Có | `redis://localhost:6379/0` | Cache task list |
| `JWT_SECRET_KEY` | Có | Không có mặc định an toàn | Ký JWT |
| `JWT_ALGORITHM` | Không | `HS256` | Thuật toán JWT |
| `ACCESS_TOKEN_EXPIRE_MINUTES` | Không | `30` | Thời hạn access token |
| `REFRESH_TOKEN_EXPIRE_DAYS` | Không | `7` | Thời hạn refresh token |
| `LOG_LEVEL` | Không | `INFO` | Mức log ứng dụng |
| `SMTP_ENABLED` | Không | `false` | Bật email thật |
| `SMTP_HOST` / `SMTP_PORT` | Không | `localhost` / `587` | SMTP server |
| `SMTP_USERNAME` / `SMTP_PASSWORD` | Không | Trống | Cấu hình cùng nhau nếu dùng |
| `SMTP_FROM_EMAIL` | Không | `noreply@example.com` | Địa chỉ gửi |
| `SMTP_USE_TLS` | Không | `true` | Dùng STARTTLS |
| `SMTP_TIMEOUT_SECONDS` | Không | `10` | SMTP timeout |

Mặc định app đọc `.env`. Có thể chọn file theo môi trường:

```powershell
$env:ENV_FILE = ".env.development"
python -m uvicorn app.main:app --reload
```

Với Docker Compose dùng `docker compose --env-file .env.development up -d
--build`. Các file `.env*` chứa bí mật được Git bỏ qua, trừ file `.example`.

## API overview

Tất cả route có prefix `/api/v1`.

| Resource | Chức năng chính |
|---|---|
| Auth | Register, login, refresh và logout |
| Users | Xem/cập nhật profile và đổi mật khẩu |
| Workspaces | CRUD workspace, list workspace và quản lý member |
| Projects | CRUD trong workspace và archive project |
| Tasks | CRUD, lọc theo status/priority/assignee và phân trang |
| Labels | CRUD theo project, gắn/gỡ label khỏi task |
| Comments | Thêm và xóa comment trên task |

Endpoint được bảo vệ dùng Bearer access token. Response lỗi có định dạng thống
nhất: `{"error": {"code": "...", "message": "..."}}`.

## Phân quyền RBAC

| Thao tác | ADMIN | OWNER | EDITOR | VIEWER |
|---|:---:|:---:|:---:|:---:|
| Xem resource trong workspace | ✓ | ✓ | ✓ | ✓ |
| Quản lý workspace/member | ✓ | ✓ | — | — |
| Tạo/sửa/xóa project, task, label | ✓ | ✓ | ✓ | — |
| Thêm comment | ✓ | ✓ | ✓ | — |
| Xóa comment | ✓ | Tác giả | Tác giả | — |

`ADMIN` bypass membership. Owner không thể bị xóa khỏi workspace khi chưa có
luồng chuyển quyền sở hữu.

## Cache, email và logging

- Danh sách task được cache trong Redis trong 60 giây theo project, filter và
  pagination; cache bị invalidate khi task hoặc project liên quan thay đổi.
- Email giao task chạy nền bằng `BackgroundTasks`. Mặc định
  `SMTP_ENABLED=false`; bật SMTP trong file môi trường để gửi thật.
- Log ghi ra stdout theo `LOG_LEVEL`, phù hợp để theo dõi bằng
  `docker compose logs -f app`. Dữ liệu nhạy cảm không được đưa vào log.

## Kiểm tra

Cài dependency development rồi chạy toàn bộ quy trình:

```powershell
python -m pip install -r requirements-dev.txt
.\scripts\test.ps1
```

Script dùng PostgreSQL/Redis test riêng, thực hiện Alembic downgrade/upgrade/check,
chạy 22 integration tests, Ruff và mypy, rồi dọn test containers cùng volumes.
Guard trong test chỉ cho phép database có tên kết thúc bằng `_test`.

Có thể chạy riêng từng kiểm tra khi các service test đã sẵn sàng:

```powershell
python -m pytest -q
python -m ruff check .
python -m mypy app
python -m alembic check
```
