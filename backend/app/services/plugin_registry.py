"""Syncs plugins/<name>/plugin.yaml files into the `plugins` DB table.

The backend deliberately never imports plugin Python code (see docs/ARCHITECTURE.md)
— only training-service does that, inside the Slurm job. This module only reads the
declarative plugin.yaml manifest so the API/frontend can list plugins and validate
job configs against their schema.
"""

import logging
from pathlib import Path

import yaml
from sqlalchemy.orm import Session

from app.models.plugin import Plugin

logger = logging.getLogger(__name__)


def _load_manifests(plugins_dir: Path) -> list[dict]:
    manifests = []
    if not plugins_dir.exists():
        logger.warning("plugins dir %s does not exist, skipping registry sync", plugins_dir)
        return manifests

    for manifest_path in sorted(plugins_dir.glob("*/plugin.yaml")):
        with manifest_path.open() as f:
            data = yaml.safe_load(f)
        required = {"name", "version", "task_type", "entrypoint"}
        missing = required - data.keys()
        if missing:
            logger.error("skipping %s: missing required fields %s", manifest_path, missing)
            continue
        manifests.append(data)
    return manifests


def sync_plugin_registry(db: Session, plugins_dir: str) -> list[Plugin]:
    manifests = _load_manifests(Path(plugins_dir))
    synced: list[Plugin] = []

    for manifest in manifests:
        plugin = db.query(Plugin).filter(Plugin.name == manifest["name"]).one_or_none()
        if plugin is None:
            plugin = Plugin(name=manifest["name"])
            db.add(plugin)

        plugin.version = manifest["version"]
        plugin.description = manifest.get("description")
        plugin.task_type = manifest["task_type"]
        plugin.config_schema = manifest.get("config_schema", {})
        plugin.default_resources = manifest.get("default_resources", {})
        plugin.entrypoint = manifest["entrypoint"]
        synced.append(plugin)

    db.commit()
    logger.info("synced %d plugin(s) from %s", len(synced), plugins_dir)
    return synced
