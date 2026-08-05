FROM python:3.11-slim

WORKDIR /srv/mlopsforge

# Unlike backend/training-service, this service actually imports and runs
# plugin code (see app/main.py), so plugins/ has to be present in the image.
COPY inference-service ./inference-service
RUN pip install --no-cache-dir ./inference-service
COPY plugins ./plugins

WORKDIR /srv/mlopsforge/inference-service
ENV PYTHONPATH=/srv/mlopsforge/inference-service:/srv/mlopsforge

EXPOSE 8200
CMD ["uvicorn", "app.main:app", "--host", "0.0.0.0", "--port", "8200"]
