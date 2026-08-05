# TaskHub API

## Cấu hình môi trường

Ứng dụng đọc cấu hình bằng `pydantic-settings`. Các biến bắt buộc gồm
`DATABASE_URL`, `REDIS_URL` và `JWT_SECRET_KEY`; ứng dụng sẽ dừng ngay khi một
biến bị thiếu hoặc không hợp lệ.

Tạo file cấu hình local từ file mẫu:

```powershell
Copy-Item .env.example .env
```

Mặc định ứng dụng đọc `.env`. Để dùng file riêng cho từng môi trường, đặt
`ENV_FILE` trước khi chạy ứng dụng hoặc Alembic:

```powershell
$env:ENV_FILE = ".env.development"
.\venv\Scripts\python.exe -m uvicorn app.main:app --reload
```

Mỗi file môi trường cần khai báo `APP_ENV` bằng một trong các giá trị `local`,
`development`, `test`, `staging`, `production` và đầy đủ các biến trong
`.env.example`. Các file `.env.*` chứa bí mật được Git bỏ qua; chỉ các file có
hậu tố `.example` được phép commit.

Khi dùng Docker Compose, có thể chọn file biến môi trường bằng tùy chọn
`--env-file`:

```powershell
docker compose --env-file .env.development up -d --build
```

## Email thông báo khi giao Task

Feature gửi email chạy bằng `BackgroundTasks`, vì vậy request tạo/cập nhật Task
không phải chờ SMTP. Email được lên lịch khi Task có assignee lúc tạo mới hoặc
khi `assignee_id` được đổi sang một thành viên khác.

Mặc định `SMTP_ENABLED=false`. Để gửi email thật, cập nhật các biến `SMTP_*`
trong file môi trường đang sử dụng và đặt `SMTP_ENABLED=true`. Có thể bỏ trống
`SMTP_USERNAME` và `SMTP_PASSWORD` nếu SMTP server không yêu cầu đăng nhập.

## Phân quyền

- `ADMIN`: truy cập và quản lý mọi workspace cùng các resource bên trong.
- `OWNER`: quản lý workspace, member, project, task, label và comment.
- `EDITOR`: xem và chỉnh sửa project, task, label; thêm/xóa comment của mình.
- `VIEWER`: chỉ xem project, task và label.

Comment chỉ được xóa bởi tác giả hoặc `ADMIN`. Owner của workspace không thể bị
xóa khỏi danh sách member nếu chưa có luồng chuyển quyền sở hữu.

## API documentation

- Swagger UI: `http://localhost:8000/docs`
- ReDoc: `http://localhost:8000/redoc`

Các endpoint được bảo vệ sử dụng Bearer access token. Toàn bộ response lỗi được
mô tả theo định dạng `{"error": {"code": "...", "message": "..."}}`.
