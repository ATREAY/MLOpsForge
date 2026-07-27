FROM python:3.11-slim

# The full 'mlflow' package (not mlflow-skinny) is needed here to actually run
# the tracking server + UI; backend and training-service only need the client
# and use mlflow-skinny instead — see their pyproject.toml comments.
RUN pip install --no-cache-dir mlflow psycopg2-binary boto3

EXPOSE 5000

CMD mlflow server \
    --host 0.0.0.0 \
    --port 5000 \
    --backend-store-uri "${MLFLOW_BACKEND_STORE_URI}" \
    --default-artifact-root "${MLFLOW_ARTIFACT_ROOT}" \
    --serve-artifacts
