from abc import ABC, abstractmethod
import random

import anyio

class Bus(ABC):
    def __init__(self):
        self.lock = anyio.Lock()
    
    @abstractmethod
    async def query(self, *args):
        pass

class DummmyI2CBus(Bus):
    async def query(self, *args):
        async with self.lock:
            await anyio.sleep(0.001)
            return random.uniform(0, 100)

class DummyMODBUS(Bus):
    async def query(self, *args):
        async with self.lock:
            await anyio.sleep(0.001)
            return random.uniform(0, 100)