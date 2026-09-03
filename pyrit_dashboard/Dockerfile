FROM python:3.11-slim

WORKDIR /app

RUN apt-get update && apt-get install -y --no-install-recommends gcc && rm -rf /var/lib/apt/lists/*

# Install uv
COPY --from=ghcr.io/astral-sh/uv:latest /uv /uvx /bin/

# Install dependencies from pyproject.toml
COPY pyrit_dashboard/pyproject.toml ./
RUN uv pip install --system "fastapi>=0.133.0" "uvicorn[standard]>=0.29.0" "httpx>=0.27.0" "redis[hiredis]>=5.0.4" "pyrit==0.14.0"

COPY pyrit_dashboard/main.py .

# In production: use gunicorn with multiple workers
CMD ["uvicorn", "main:app", "--host", "0.0.0.0", "--port", "8001"]
