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
