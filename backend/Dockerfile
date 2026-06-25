# Python pinned to 3.12 to match CI.
FROM python:3.12-slim

ENV PYTHONUNBUFFERED=1 \
    PYTHONDONTWRITEBYTECODE=1 \
    PIP_NO_CACHE_DIR=1

# System libraries for GeoDjango (GDAL/GEOS/PROJ). Geometry models arrive in
# issue #5; installing here so the image is ready and matches the CI toolchain.
RUN apt-get update && apt-get install -y --no-install-recommends \
        gdal-bin \
        libgdal-dev \
        libgeos-dev \
        libproj-dev \
        binutils \
        postgresql-client \
    && rm -rf /var/lib/apt/lists/*

WORKDIR /app

# Dev image: install runtime + dev deps so `make test` runs inside the container.
COPY requirements.txt requirements-dev.txt ./
RUN pip install -r requirements-dev.txt

COPY . .

EXPOSE 8000

CMD ["gunicorn", "config.wsgi:application", "--bind", "0.0.0.0:8000", "--workers", "3"]
