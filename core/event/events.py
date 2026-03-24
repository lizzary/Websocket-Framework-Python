class Event:

    def __init__(self, event_name: str, event_data=None):

        self.__name = event_name
        self.__data = event_data

    def getName(self) -> str:
        return self.__name

    def getData(self):
        return self.__data

    def __hash__(self) -> int:
        return hash(self.__name)

    def __eq__(self, other) -> bool:
        if isinstance(other, Event):
            return self.__name == other.getName()
        elif isinstance(other, str):
            return self.__name == other
        else:
            return False

    def __str__(self) -> str:
        return f"Event('{self.__name}', {self.__data})"

    def __repr__(self) -> str:
        return f"Event('{self.__name}', {self.__data})"