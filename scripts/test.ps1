$ErrorActionPreference = "Stop"

$env:APP_ENV = "test"
$env:ENV_FILE = ".env.test"
$env:DATABASE_URL = "postgresql+asyncpg://taskhub:taskhub@localhost:5434/taskhub_test"
$env:REDIS_URL = "redis://localhost:6380/0"
$env:JWT_SECRET_KEY = "automated-test-secret-key"
$env:LOG_LEVEL = "WARNING"
$env:SMTP_ENABLED = "false"

$composeFile = "docker-compose.test.yml"
$python = ".\venv\Scripts\python.exe"
$exitCode = 0

try {
    docker compose -f $composeFile up -d --wait
    if ($LASTEXITCODE -ne 0) { throw "Test containers failed to start." }

    & $python -m alembic downgrade base
    if ($LASTEXITCODE -ne 0) { throw "Alembic downgrade failed." }

    & $python -m alembic upgrade head
    if ($LASTEXITCODE -ne 0) { throw "Alembic upgrade failed." }

    & $python -m alembic check
    if ($LASTEXITCODE -ne 0) { throw "Alembic check failed." }

    & $python -m pytest
    if ($LASTEXITCODE -ne 0) { throw "Pytest failed." }

    & ".\venv\Scripts\ruff.exe" check .
    if ($LASTEXITCODE -ne 0) { throw "Ruff failed." }

    & $python -m mypy app
    if ($LASTEXITCODE -ne 0) { throw "Mypy failed." }
}
catch {
    Write-Host "Test run failed: $_" -ForegroundColor Red
    $exitCode = 1
}
finally {
    docker compose -f $composeFile down -v
}

exit $exitCode
