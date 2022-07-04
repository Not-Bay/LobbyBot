import asyncio
import logging

log = logging.getLogger('LobbyBot.modules.utils')

class Colors:

    Red = 0xe62222
    Green = 0x2ee32b
    Blue = 0x2173c4
    Yellow = 0xd1c926

def get_future_result(future: asyncio.Future) -> any:

    if future.exception() != None:
        return future.exception()

    try:
        return future.result()

    except asyncio.CancelledError:
        return None