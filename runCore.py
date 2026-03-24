from core.event.eventbus import GlobalEventBus
from core.network.webserver import GlobalWebServer
from threading import Thread
from core.plugin.pluginsLoader import loadPluginList
server = GlobalWebServer.get()
event_bus = GlobalEventBus.get()
loadPluginList()

def start_event_bus():
    while True:
        event_bus.process_one_step()

if __name__ == '__main__':
    server_thread = Thread(target=server.start)
    server_thread.start()
    event_thread = Thread(target=start_event_bus)
    event_thread.start()

    while True:
        pass
