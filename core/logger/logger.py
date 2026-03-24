import json
import sys

from loguru import logger as loguruLog

# 移除默认的同步处理器
loguruLog.remove()
# 添加异步队列处理器
loguruLog.add(sys.stderr, enqueue=True)  #启用异步
def START_SERVER(host, port):
    try:
        loguruLog.success(f'WebServer Start! Use ws://{host}:{port} to connect')
    finally:
        return

def PRINT_SOCKET_CONNECTED(websocket):
    try:
        loguruLog.info(f"新连接建立:")
        loguruLog.info(f"  客户端地址: {websocket.remote_address[0]}:{websocket.remote_address[1]}")
        loguruLog.info(f"  连接ID: {id(websocket)}")
        loguruLog.info(f"  连接状态: {websocket.state}")
    finally:
        return

def PRINT_SOCKET_DISCONNECTED(websocket):
    try:
        loguruLog.warning(f"连接断开")
        loguruLog.warning(f"  客户端地址: {websocket.remote_address[0]}:{websocket.remote_address[1]}")
        loguruLog.warning(f"  连接ID: {id(websocket)}")
    finally:
        return


def PRINT_SERVER_MSG(msg, remote_address ="unknown", ws_id ="unknown"):
    try:
        loguruLog.info(f'[{remote_address[0]}:{remote_address[1]}] Say:  {msg} (ws_id:{ws_id})')
    finally:
        return

def PRINT_SERVER_RESPONSE(msg, response_to ="unknown", ws_id ="unknown"):
    try:
        loguruLog.info(f'Response to [{response_to[0]}:{response_to[1]}]:  {msg} (ws_id:{ws_id})')
    finally:
        return

def PRINT_ERROR_MSG(__message: str,*args,**kwargs):
    loguruLog.error(__message,*args,**kwargs)

def PRINT_ERROR_WITH_TRACE(e: Exception):
    loguruLog.exception(e)

def PRINT_LOAD_PLUGIN(name):
    try:
        loguruLog.success(f'loading plugin "{name}"')
    finally:
        return

def PRINT_DEBUG_MSG(__message: str,*args,**kwargs):
    loguruLog.debug(__message,*args,**kwargs)

def PRINT_INFO_MSG(__message: str,*args,**kwargs):
    loguruLog.info(__message,*args,**kwargs)

def MAKE_RESPONSE_MSG(state:bool, msg):
    state = "success" if state else "fail"
    return json.dumps({"state":state,"msg":msg})





    