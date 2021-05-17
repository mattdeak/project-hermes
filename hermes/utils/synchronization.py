import asyncio

class SingletonTradeLock:
    _instance = None

    @classmethod
    def instance(cls, event_loop=None):
        if cls._instance is None:
            cls._instance = asyncio.Lock(loop=event_loop)

        return cls._instance

class SingletonResetEvent:
    _instance = None

    @classmethod
    def instance(cls, event_loop=None):
        if cls._instance is None:
            cls._instance = asyncio.Event(loop=event_loop)

        return cls._instance




