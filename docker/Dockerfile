FROM python:3.12-slim

# ====== ENV ======
ENV PYTHONDONTWRITEBYTECODE=1 \
    PYTHONUNBUFFERED=1 \
    POETRY_VERSION=1.8.3 \
    POETRY_NO_INTERACTION=1 \
    POETRY_VIRTUALENVS_CREATE=false

# ====== SYSTEM DEPS ======
RUN apt-get update && apt-get install -y --no-install-recommends \
    curl \
    build-essential \
    libpq-dev \
    && rm -rf /var/lib/apt/lists/*

# ====== POETRY ======
RUN pip install --no-cache-dir "poetry==$POETRY_VERSION"

# ====== WORKDIR ======
WORKDIR /app

# ====== DEPENDENCIES (LAYER CACHE) ======
COPY pyproject.toml poetry.lock ./
RUN poetry install --no-root

# ====== COPY PROJECT ======
COPY . .

# ====== DJANGO ======
ENV DJANGO_SETTINGS_MODULE=config.settings

# ====== CMD (dev) ======
CMD ["python", "manage.py", "runserver", "0.0.0.0:8000"]