from core.event.eventbus import GlobalEventBus
from core.network.webserver import GlobalWebServer


class PluginContext:
    webserver = GlobalWebServer.get()
    event_bus = GlobalEventBus.get()