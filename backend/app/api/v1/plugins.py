from fastapi import APIRouter, Depends, HTTPException
from sqlalchemy.orm import Session

from app.api.deps import get_db
from app.core.config import get_settings
from app.models.plugin import Plugin
from app.schemas.plugin import PluginRead
from app.services.plugin_registry import sync_plugin_registry

router = APIRouter(prefix="/plugins", tags=["plugins"])


@router.get("", response_model=list[PluginRead])
def list_plugins(db: Session = Depends(get_db)):
    return db.query(Plugin).order_by(Plugin.name).all()


@router.get("/{name}", response_model=PluginRead)
def get_plugin(name: str, db: Session = Depends(get_db)):
    plugin = db.query(Plugin).filter(Plugin.name == name).one_or_none()
    if plugin is None:
        raise HTTPException(404, "plugin not found")
    return plugin


@router.post("/sync", response_model=list[PluginRead])
def resync_plugins(db: Session = Depends(get_db)):
    """Re-scan plugins/*/plugin.yaml on disk. Also runs automatically on backend
    startup; exposed here so adding a plugin doesn't require a restart."""
    return sync_plugin_registry(db, get_settings().PLUGINS_DIR)
