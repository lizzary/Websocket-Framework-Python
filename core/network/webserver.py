import json
import threading
import random
from json import JSONDecodeError
import socket
from queue import Queue
from threading import Thread

from websockets.sync.server import serve

from core.constant.enum import UNKNOWN
from core.constant.events import PRE_SERVER_START, POST_SERVER_START
from core.event.eventbus import GlobalEventBus
from core.event.events import Event
from core.logger import logger

event_bus = GlobalEventBus.get()


class WebServer:
    """
    请求格式：
    {
        "event":"事件名",
        "data":"该事件要传递的数据，可以是任意数据类型，例如list或dict"
    }
    """

    def __init__(self, host: str = "localhost", port: int = 8765, enable_msg_logger:bool = True):
        self.host = host
        self.port = port
        self.client_websocket_ids = set()  #集合，储存已连接的ws实例的id，int型
        self.client_websocket:dict = dict() #{<ws_id: int>: <ws_instance>，, ... }
        self._lock = threading.Lock()  # 添加线程锁保证线程安全
        self.enable_msg_logger = enable_msg_logger

    def start(self):
        event_bus.publish(Event(PRE_SERVER_START, {"ws": self}))
        logger.START_SERVER(self.host, self.port)

        def onReceive(websocket):
            if self.enable_msg_logger: logger.PRINT_SOCKET_CONNECTED(websocket)
            with self._lock:
                self.client_websocket_ids.add(id(websocket))
                self.client_websocket.update({id(websocket):websocket})

            try:
                for msg in websocket:
                    if self.enable_msg_logger: logger.PRINT_SERVER_MSG(msg, websocket.remote_address, id(websocket))
                    msg = self.__parseMsg(msg,id(websocket))
                    event_bus.publish(Event(msg.get("event"), msg.get("data")))
            finally:
                with self._lock:
                    ws_id = id(websocket)
                    if ws_id in self.client_websocket_ids:
                        if self.enable_msg_logger: logger.PRINT_SOCKET_DISCONNECTED(websocket)
                        del self.client_websocket[ws_id]
                        self.client_websocket_ids.remove(ws_id)

        with serve(onReceive, self.host, self.port) as server:
            event_bus.publish(Event(POST_SERVER_START, {"ws": self}))
            server.serve_forever()

    def response(self, msg: str, socket_id_whitelist:set=None, socket_id_blacklist:set=None):
        """
        向符合条件的客户端发送消息。
        :param msg: 要发送的 JSON 字符串
        :param socket_id_whitelist: 允许接收的客户端 ID 集合（若为 None 则表示不限制）
        :param socket_id_blacklist: 排除的客户端 ID 集合（若为 None 则表示不排除）
        """
        # 获取当前所有连接的快照（线程安全）
        with self._lock:
            client_websocket_id = self.client_websocket_ids
            client_websocket = self.client_websocket

        if socket_id_blacklist is None:
            socket_id_blacklist = set()

        if socket_id_whitelist is not None:
            socket_ids_to_send = socket_id_whitelist - socket_id_blacklist
        else:
            socket_ids_to_send = client_websocket_id - socket_id_blacklist

        # 执行发送
        thread_list = []
        #print("socket_ids_to_send ",socket_ids_to_send," client_websocket_id ",client_websocket_id)
        for sid in socket_ids_to_send:
            t = Thread(target=self.__response,args=(msg,sid,client_websocket))
            t.start()
            thread_list.append(t)


    def isConnect(self, socket_id:int):
        with self._lock:
            current_socket_ids = self.client_websocket_ids
        if socket_id in current_socket_ids:
            try:
                socket = self.client_websocket[socket_id]
                socket.send(json.dumps({"checkAlive": socket_id}))
                return True
            except Exception as e:
                logger.PRINT_ERROR_WITH_TRACE(e)
                return False
        return False

    def __response(self,msg,sid:int,client_websocket:dict):
        try:
            #print(sid,client_websocket)
            sock = client_websocket.get(sid)
            sock.send(msg)
            if self.enable_msg_logger: logger.PRINT_SERVER_RESPONSE(msg, sock.remote_address, id(sock))
        except ConnectionResetError as e:
            logger.PRINT_ERROR_WITH_TRACE(e)
            with self._lock:
                if sid in self.client_websocket_ids:
                    self.client_websocket_ids.remove(sid)
                    del self.client_websocket[sid]
        except Exception as e:
            logger.PRINT_ERROR_WITH_TRACE(e)

    def __parseMsg(self, msg, ws_id:int):
        try:
            msg = json.loads(msg)
            if "event" not in msg or "data" not in msg:
                self.response(logger.MAKE_RESPONSE_MSG(False, "key 'event' or 'data' is missing"))
                return {"event": UNKNOWN, "data": None}
            msg["data"]["ws_id"] = ws_id
            return msg
        except (JSONDecodeError,) as e:
            self.response(logger.MAKE_RESPONSE_MSG(False, "not a json"))
            return {"event": UNKNOWN, "data": None}
        except Exception as e:
            logger.PRINT_ERROR_WITH_TRACE(e)
            return {"event": UNKNOWN, "data": None}

def get_host_ip():
    try:
        s = socket.socket(socket.AF_INET, socket.SOCK_DGRAM)
        s.connect(('8.8.8.8', 80))
        ip = s.getsockname()[0]
        s.close()
        return ip
    except Exception:
        return '127.0.0.1'


class GlobalWebServer:
    ws = WebServer(host=get_host_ip(),enable_msg_logger=True)

    @staticmethod
    def get():
        return GlobalWebServer.ws
