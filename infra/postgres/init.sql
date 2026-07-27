-- Runs once, on first container creation (docker-entrypoint-initdb.d). MLflow
-- needs its own database, not the app's ${POSTGRES_DB} — MLflow's internal
-- table names (experiments, runs, model_versions, ...) would otherwise
-- collide with MLOpsForge's own Alembic-managed tables of the same name.
CREATE DATABASE mlflow;
