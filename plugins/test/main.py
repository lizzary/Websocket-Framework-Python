import time
from time import sleep

from core.constant.events import POST_SERVER_START, PRE_SERVER_START
from core.event.eventbus import GlobalEventBus
from core.network.webserver import GlobalWebServer
from loguru import logger

server = GlobalWebServer.get()
event_bus = GlobalEventBus.get()


@event_bus.listen_immediately("hello")
def sendSomething(event):
    server.response("hello world from test1")
    sleep(10)

# 在顶层的代码会在插件加载时立即执行
# time.sleep(5)
# print("this code will be run")

# 或者可以监听webserver启动时的事件作为插件入口
# @event_bus.listen_immediately(PRE_SERVER_START)
# def server_start(event):
#     print("this is the plugin entry")
