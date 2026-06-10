@echo off
REM Quick start script for optimized Mimi AI with Docker Compose

echo ========================================
echo Starting Mimi AI (Optimized Mode)
echo ========================================
echo.

REM Check if Docker is running
docker info >nul 2>&1
if errorlevel 1 (
    echo [ERROR] Docker is not running!
    echo Please start Docker Desktop and try again.
    pause
    exit /b 1
)

echo [1/4] Checking environment file...
if not exist .env (
    echo Creating .env from template...
    copy .env.docker .env
    echo.
    echo IMPORTANT: Edit .env file and add your API keys!
    echo - OPENAI_API_KEY
    echo - MONGODB_URI
    echo - SECRET
    echo.
    pause
)

echo [2/4] Starting Docker services...
docker-compose up -d

echo.
echo [3/4] Waiting for services to be healthy...
timeout /t 10 /nobreak >nul

echo.
echo [4/4] Checking service status...
docker-compose ps

echo.
echo ========================================
echo Mimi AI is starting!
echo ========================================
echo.
echo Services:
echo - Flask App: http://localhost:5000
echo - Redis: localhost:6379
echo - PostgreSQL: localhost:5432
echo - Qdrant: http://localhost:6333
echo.
echo Performance features enabled:
echo  ✓ Response caching
echo  ✓ Async tasks (Celery)
echo  ✓ Parallel processing
echo.
echo View logs: docker-compose logs -f
echo Stop all: docker-compose down
echo.
pause
