FROM python:3.11-slim

ENV PYTHONUNBUFFERED=1

WORKDIR /app

# Copy project files and install package
COPY pyproject.toml README.md /app/
COPY src /app/src
RUN pip install --upgrade pip && pip install .

# Copy numbered camera manifest
COPY data/manifests/corridor_cameras_numbered.json /app/data/manifests/corridor_cameras_numbered.json

# Copy entrypoint
COPY infra/cloudrun/entrypoint.sh /app/entrypoint.sh
RUN chmod +x /app/entrypoint.sh

ENTRYPOINT ["/app/entrypoint.sh"]
