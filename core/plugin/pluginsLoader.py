import importlib
from core.logger import logger

def loadPluginList():
    import tomllib  # Python 3.11+
    with open("./plugins/plugins.toml", "rb") as f:
        config = tomllib.load(f)

    for plugin_path in config["plugins"]:
        try:
            logger.PRINT_LOAD_PLUGIN(plugin_path)
            module = importlib.import_module(f'{plugin_path}.main')
        except Exception as e:
            logger.PRINT_ERROR_WITH_TRACE(e)
