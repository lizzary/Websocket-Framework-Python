import functools
import heapq
import threading
from collections import defaultdict
from typing import Callable, List, Dict, Set, Deque, Optional
import queue
from loguru import logger
from core.event.events import Event
from threading import Thread


class EventBus:
    # listener type enum
    NONE = 0
    IMMEDIATE = 1
    DELAY = 2
    JOINT = 3
    PATTERN = 4

    def __init__(self):
        self.is_install = False  # 该事件引擎是否被加载过
        self.event_count = 0  # 全局事件计数器
        self.event_bus = queue.Queue(maxsize=1000)

        # 立即触发监听器集，{<监听事件名>:[<可调用对象 1>, <可调用对象 2>, ... }
        self.immediate_listeners: Dict[Event, List[Callable]] = defaultdict(list)

        # 延迟触发集，[(触发事件计数, 回调)，(触发事件计数, 回调)，...】
        self.delayed_tasks: List[tuple] = []  # 最小堆: (触发事件计数, 回调)

        # 联合触发集
        self.joint_conditions: List['JointCondition'] = []

        # 模式触发集
        self.pattern_matchers: List['PatternMatcher'] = []

    def publish(self, event: Event):
        """发布事件以及事件信息，将事件放入队列末尾"""
        self.event_bus.put(event)

    def process_one_step(self):
        """从队列头开始处理事件"""
        if self.event_bus.empty():
            return True

        if self.event_bus.full():
            return False

        self.event_count += 1
        event = self.event_bus.get()

        # 立即触发
        for callback in self.immediate_listeners[event]:
            Thread(target=callback,args=(event,)).start()
            # callback(event)

        # 检查延迟触发任务
        while self.delayed_tasks and self.delayed_tasks[0][0] <= self.event_count:
            _, callback, original_event = heapq.heappop(self.delayed_tasks)
            Thread(target=callback, args=(original_event,)).start()

        # 联合触发
        for condition in self.joint_conditions:
            Thread(target=condition.on_event, args=(event,)).start()

        # 模式触发
        for matcher in self.pattern_matchers:
            Thread(target=matcher.on_event, args=(event,)).start()


        return False

    def process(self, maxStep=10000):
        for i in range(maxStep):
            is_done = self.process_one_step()
            if is_done:
                return

        logger.critical(f"EVENTBUS: reach step limit {maxStep}, check infinite event loop")

    def add_immediate_listener(self, source: Event, callback: Callable):
        self.immediate_listeners[source].append(callback)

    def add_delayed_listener(self, source: Event, delay: int, callback: Callable):
        # 当监听的事件发生时，这个包装器被调用,计算出任务应该在哪个事件计数时触发然后放进队列
        def delayed_callback_wrapper(original_event: Event):
            trigger_at = self.event_count + delay
            # 存储原始事件和回调
            heapq.heappush(self.delayed_tasks, (trigger_at, callback, original_event))

        # 重命名该回调函数，使其在日志中可见
        delayed_callback_wrapper.__name__ = f"delayed_wrapper_{callback.__name__}"

        self.add_immediate_listener(source, delayed_callback_wrapper)

    def add_joint_listener(self, sources: List[Event], callback: Callable):
        condition = JointCondition(set(sources), callback)
        self.joint_conditions.append(condition)

    def add_pattern_listener(self, pattern: List[Event], callback: Callable):
        matcher = PatternMatcher(pattern, callback)
        self.pattern_matchers.append(matcher)

    """以下是装饰器版本的实现，支持使用装饰器将一个函数绑定到一个监听器的回调"""

    def publish_event(self, event: Event):
        """
        事件发布的装饰器版本\n
        该装饰器须在监听器装饰器@listen_xxx之前调用（该装饰器在@listen_xx下方）
        :param event:
        :return:
        """

        def decorator(func: Callable):
            @functools.wraps(func)  # 保留原函数的元信息
            def wrapper(*args, **kwargs):
                func(*args, **kwargs)
                self.publish(event)

            return wrapper

        return decorator

    def listen_immediately(self, source: Event):
        """
        添加监听器的装饰器版本\n
        该装饰器须在@publish_event之后调用（该装饰器在@publish_event上方）
        """
        def decorator(callback: Callable):
            self.add_immediate_listener(source, callback)
            return callback

        return decorator

    def listen_delayed(self, source: Event, delay: int):
        """
        添加监听器的装饰器版本\n
        该装饰器须在@publish_event之后调用（该装饰器在@publish_event上方）
        """

        def decorator(callback: Callable):
            self.add_delayed_listener(source, delay, callback)
            return callback

        return decorator

    def listen_jointly(self, sources: List[Event]):
        """
        添加监听器的装饰器版本\n
        该装饰器须在@publish_event之后调用（该装饰器在@publish_event上方）
        """

        def decorator(callback: Callable):
            self.add_joint_listener(sources, callback)
            return callback

        return decorator

    def listen_pattern_matcher(self, pattern: List[Event]):
        """
        添加监听器的装饰器版本\n
        该装饰器须在@publish_event之后调用（该装饰器在@publish_event上方）
        """

        def decorator(callback: Callable):
            self.add_pattern_listener(pattern, callback)
            return callback

        return decorator

class JointCondition:
    def __init__(self, required_events: Set[Event], callback: Callable):
        self.required = required_events
        self.occurred: Set[Event] = set()
        self.callback = callback
        self.lock = threading.Lock()

    def reset(self):
        self.occurred = set()

    def on_event(self, event: Event):
        with self.lock:
            if event in self.required and event not in self.occurred:
                self.occurred.add(event)
                if self.occurred == self.required:
                    #logger.info(f"EVENTBUS: event callback <func: {self.callback.__name__}> is triggered")
                    self.callback(self.occurred)
                    self.reset()  # 触发后重置

class GlobalEventBus:
    bus = EventBus()

    @staticmethod
    def get():
        return GlobalEventBus.bus

class PatternMatcher:
    def __init__(self, pattern: List[Event], callback: Callable):
        self.pattern: List[Event] = pattern
        self.occurred: List[Event] = []
        self.state = 0  # 当前匹配位置
        self.callback = callback
        self.lock = threading.Lock()

    def reset(self):
        self.occurred = []
        self.state = 0

    def on_event(self, event: Event):
        with self.lock:
            if self.state < len(self.pattern):
                if self.pattern[self.state] == '*' or self.pattern[self.state] == event:
                    self.state += 1
                    self.occurred.append(event)
                    if self.state == len(self.pattern):
                        #logger.info(f"EVENTBUS: event callback <func: {self.callback.__name__}> is triggered")
                        self.callback(self.occurred)
                        self.reset()  # 触发后重置
                else:
                    self.reset()
                    if self.pattern[0] == '*' or self.pattern[0] == event:
                        self.state = 1
                        self.occurred.append(event)
                        if self.state == len(self.pattern):
                            #logger.info(f"EVENTBUS: event callback <func: {self.callback.__name__}> is triggered")
                            self.callback(self.occurred)
                            self.reset()