FROM python:3.11-slim

WORKDIR /srv/mlopsforge

# training-service only talks to plugins/*/plugin.yaml (declarative metadata)
# and never imports plugin Python code itself — see docs/ARCHITECTURE.md — so
# the plugins/ tree isn't needed in this image.
COPY training-service ./training-service
RUN pip install --no-cache-dir ./training-service

WORKDIR /srv/mlopsforge/training-service

EXPOSE 8100
CMD ["uvicorn", "app.main:app", "--host", "0.0.0.0", "--port", "8100"]
