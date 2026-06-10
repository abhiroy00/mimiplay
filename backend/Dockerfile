FROM python:3.11-slim
ENV PYTHONUNBUFFERED=1

RUN apt-get update && apt-get install -y \
    build-essential \
    cmake \
    libgl1 \
    libglib2.0-0 \
    libsm6 \
    libxext6 \
    libxrender1 \
    ffmpeg \
    && rm -rf /var/lib/apt/lists/*

WORKDIR /app

# Copy requirements first for better caching
COPY requirements.txt requirements_advanced_memory.txt ./

RUN pip install --upgrade pip
RUN pip install -r requirements.txt

# Install Celery and performance packages
RUN pip install celery redis gunicorn gevent

# Optionally install advanced memory requirements (comment out if not needed)
# RUN pip install -r requirements_advanced_memory.txt

COPY . .

# Remove .env so Railway's injected env vars are always used in production
RUN rm -f .env .env.* 

# Expose port
EXPOSE 8080

# Use gunicorn with gevent for better async performance
CMD ["gunicorn", "app:app", "--bind", "0.0.0.0:8080", "--workers", "2", "--worker-class", "gevent", "--worker-connections", "1000", "--timeout", "60", "--keep-alive", "5"]