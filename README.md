
## 1. 框架概述

本项目是一个基于 **事件驱动** 的 WebSocket 服务器框架。  
核心组件包括：

- **EventBus**：全局事件总线，负责事件的发布与监听。
- **WebServer**：WebSocket 服务器，负责与前端建立连接、收发消息。
- **PluginContext**：为插件提供便捷的 `webserver` 和 `event_bus` 访问入口。
- **PluginsLoader**：自动加载 `plugins.toml` 中配置的插件模块。

插件通过监听特定事件来响应前端请求，并可主动向客户端推送消息。

---

## 2. 快速开始

### 2.1 创建插件目录结构

在项目根目录下的 `plugins/` 文件夹中，为每个插件创建一个独立子目录，例如：

```
plugins/
├── my_plugin/
│   └── main.py
├── plugins.toml
```

插件目录名即插件名，`main.py` 是插件的入口文件。

---

### 2.2 编写插件代码

在 `main.py` 中，你可以：

- 导入 `PluginContext` 以获取事件总线和 WebSocket 服务器实例。
- 使用装饰器或手动添加事件监听器。
- 定义处理函数，解析事件数据，并执行相应逻辑。

#### 示例：一个简单的“问候”插件

```python
# plugins/my_plugin/main.py

from core.plugin.pluginsContext import PluginContext

# 获取全局事件总线和 WebSocket 服务器
event_bus = PluginContext.event_bus
webserver = PluginContext.webserver

@event_bus.listen_immediately("greet")
def on_greet(event):
    """
    监听前端发送的 "greet" 事件
    该事件结构：
    {
        "name": "Alice",
        "ws_id": 12345
    }
    """

    #从event中获取需要的信息
    data = event.getData()
    name = data.get("name", "Guest")
    ws_id = data.get("ws_id")

    # 构造响应消息
    response_msg = f"Hello, {name}! Welcome to the server."

    # 向对应客户端发送消息
    webserver.response(
        msg=response_msg,
        socket_id_whitelist={ws_id}  # 仅回复给发送该请求的客户端
    )
```

---

### 2.3 配置插件加载

在 `plugins/plugins.toml` 中添加插件路径：

```toml
plugins = [
    "plugins.my_plugin",   # 注意：这里是 Python 模块路径
    # 其他插件...
]
```

插件路径需与目录结构一致，使用点号分隔。

---

## 3. 事件与数据格式

### 3.1 前端发送请求

前端通过 WebSocket 发送 JSON 格式的消息：

```json
{
    "event": "事件名",
    "data": {
        // 任意数据，可以是字符串、数字、对象等
        "ws_id": 12345   // 服务端会自动注入 ws_id，无需前端传递
    }
}
```

**注意**：  
- `event` 字段为必填，用于匹配插件监听的事件。  
- `data` 字段为必填，即使不需要数据，也需传 `{}`。  
- `ws_id` 由服务端自动注入，前端无需关心。

### 3.2 插件处理事件

插件通过 `event.getData()` 获取前端发送的数据，其中会自动包含 `ws_id`，可用于标识客户端连接。

---

## 4. 向客户端发送消息

使用 `webserver.response(msg, socket_id_whitelist, socket_id_blacklist)` 方法：

- `msg`：要发送的字符串（建议为 JSON 格式）。
- `socket_id_whitelist`：允许接收的客户端 ID 集合。
- `socket_id_blacklist`：排除的客户端 ID 集合。

示例：

```python
# 仅回复给特定客户端
webserver.response("Hello!", socket_id_whitelist={12345})

# 回复给所有客户端
webserver.response("Broadcast message")

# 排除某些客户端
webserver.response("Private message", socket_id_blacklist={67890})
```

---

## 5. 事件监听器类型

事件总线支持四种监听器，可根据需求选择：

### 5.1 立即监听器 (`listen_immediately`)

事件发布后立即执行回调。  
适用于需要实时响应的场景。

```python
@event_bus.listen_immediately("some_event")
def handler(event):
    # 立即执行
    pass
```

### 5.2 延迟监听器 (`listen_delayed`)

事件发布后，延迟若干事件计数后再执行。

```python
@event_bus.listen_delayed("some_event", delay=10)
def handler(event):
    # 10个事件后执行
    pass
```

### 5.3 联合监听器 (`listen_jointly`)

等待一组事件都发生后才执行回调。

```python
@event_bus.listen_jointly(["event_a", "event_b"])
def handler(events):
    # events 是一个包含已触发事件的集合
    pass
```

### 5.4 模式监听器 (`listen_pattern_matcher`)

按顺序匹配事件序列，支持 `'*'` 作为通配符。

```python
@event_bus.listen_pattern_matcher(["start", "*", "end"])
def handler(events):
    # 匹配 start -> 任意事件 -> end 序列
    pass
```

---

## 6. 完整示例：一个计算器插件

假设前端发送 `calc` 事件，携带表达式，后端计算后返回结果。

```python
# plugins/calculator/main.py

import json
from core.plugin.pluginsContext import PluginContext

event_bus = PluginContext.event_bus
webserver = PluginContext.webserver

@event_bus.listen_immediately("calc")
def on_calc(event):
    data = event.getData()
    expression = data.get("expression", "")
    ws_id = data.get("ws_id")

    try:
        # 简单计算器（仅演示，实际应使用更安全的方式）
        result = eval(expression)
        response = json.dumps({"result": result})
    except Exception as e:
        response = json.dumps({"error": str(e)})

    webserver.response(response, socket_id_whitelist={ws_id})
```

---

## 7. 调试与日志

框架使用 `loguru` 进行日志记录。你可以在插件中直接使用：

```python
from core.logger import logger

logger.PRINT_INFO_MSG("Plugin loaded")
logger.PRINT_ERROR_MSG("Something went wrong")
```

WebSocket 连接状态、收发的消息也会自动打印（可通过 `enable_msg_logger` 控制）。

---

## 8. 运行与测试

1. 启动服务器：
   ```bash
   python runCore.py
   ```
2. 使用 WebSocket 客户端（如浏览器、Postman、websocat）连接：
   ```
   ws://localhost:8765
   ```
3. 发送 JSON 消息：
   ```json
   {"event": "greet", "data": {"name": "Alice"}}
   ```
4. 观察服务端日志和客户端响应。

---

