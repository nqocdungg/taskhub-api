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
