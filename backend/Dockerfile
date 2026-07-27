FROM python:3.11-slim

WORKDIR /srv/mlopsforge

# The backend reads plugins/*/plugin.yaml at startup to populate the plugin
# registry (see app/services/plugin_registry.py) — it never imports plugin
# Python code, but the plugins/ tree itself needs to be mounted/copied in.
COPY backend ./backend
RUN pip install --no-cache-dir ./backend
COPY plugins ./plugins

WORKDIR /srv/mlopsforge/backend
ENV PLUGINS_DIR=/srv/mlopsforge/plugins

EXPOSE 8000
CMD ["sh", "-c", "alembic upgrade head && uvicorn app.main:app --host 0.0.0.0 --port 8000"]
