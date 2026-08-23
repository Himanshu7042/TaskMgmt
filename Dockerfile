FROM python:3.11-slim

# Set environment variables
ENV PYTHONDONTWRITEBYTECODE=1
ENV PYTHONUNBUFFERED=1

# Install system dependencies for MySQL client
RUN apt-get update \
    && apt-get install -y default-libmysqlclient-dev build-essential pkg-config \
    && rm -rf /var/lib/apt/lists/*

WORKDIR /app

# Install uv for fast dependency resolution
RUN pip install uv

# Copy dependency files first to leverage Docker cache
COPY backend/pyproject.toml backend/uv.lock ./backend/

# Install dependencies system-wide using uv
WORKDIR /app/backend
RUN uv pip install --system -r pyproject.toml

# Copy the entire project
WORKDIR /app
COPY . /app/

# Set working directory to where manage.py is
WORKDIR /app/backend

# Expose port for Django
EXPOSE 8080

# Run migrations, create a default superuser if it doesn't exist, and start the server
# Using a small shell script to wrap the setup process safely
CMD ["sh", "-c", "python manage.py migrate && python manage.py runserver 0.0.0.0:8080"]
