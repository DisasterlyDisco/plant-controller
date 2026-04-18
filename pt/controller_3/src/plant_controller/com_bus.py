import random

import anyio

class Bus:
    def __init__(self):
        self.lock = anyio.Lock()
    
    async def query(self, command: str):
        async with self.lock:
            await anyio.sleep(0.1)
            return random.uniform(0, 100)