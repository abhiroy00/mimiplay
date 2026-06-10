#!/bin/bash

# Quick start script for optimized Mimi AI with Docker Compose

echo "========================================"
echo "Starting Mimi AI (Optimized Mode)"
echo "========================================"
echo ""

# Check if Docker is running
if ! docker info > /dev/null 2>&1; then
    echo "[ERROR] Docker is not running!"
    echo "Please start Docker and try again."
    exit 1
fi

echo "[1/4] Checking environment file..."
if [ ! -f .env ]; then
    echo "Creating .env from template..."
    cp .env.docker .env
    echo ""
    echo "IMPORTANT: Edit .env file and add your API keys!"
    echo "- OPENAI_API_KEY"
    echo "- MONGODB_URI"
    echo "- SECRET"
    echo ""
    read -p "Press Enter to continue after editing .env..."
fi

echo "[2/4] Starting Docker services..."
docker-compose up -d

echo ""
echo "[3/4] Waiting for services to be healthy..."
sleep 10

echo ""
echo "[4/4] Checking service status..."
docker-compose ps

echo ""
echo "========================================"
echo "Mimi AI is starting!"
echo "========================================"
echo ""
echo "Services:"
echo "- Flask App: http://localhost:5000"
echo "- Redis: localhost:6379"
echo "- PostgreSQL: localhost:5432"
echo "- Qdrant: http://localhost:6333"
echo ""
echo "Performance features enabled:"
echo " ✓ Response caching"
echo " ✓ Async tasks (Celery)"
echo " ✓ Parallel processing"
echo ""
echo "View logs: docker-compose logs -f"
echo "Stop all: docker-compose down"
echo ""
