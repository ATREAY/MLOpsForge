import importlib

from plugins.base.interface import BaseModelPlugin


def load_plugin(entrypoint: str) -> BaseModelPlugin:
    """Resolves a plugin.yaml `entrypoint` string like
    'plugins.samamba.plugin:SAMambaPlugin' into an instantiated plugin. This is
    the only place plugin code gets imported dynamically — training-service and
    run_train.py both go through this rather than importing plugins directly."""
    module_path, sep, class_name = entrypoint.partition(":")
    if not sep:
        raise ValueError(f"invalid plugin entrypoint '{entrypoint}', expected 'module.path:ClassName'")

    module = importlib.import_module(module_path)
    try:
        plugin_cls = getattr(module, class_name)
    except AttributeError as exc:
        raise ValueError(f"module '{module_path}' has no class '{class_name}'") from exc

    if not issubclass(plugin_cls, BaseModelPlugin):
        raise TypeError(f"{entrypoint} does not implement BaseModelPlugin")

    return plugin_cls()
