import asyncio
import logging

log = logging.getLogger('LobbyBot.modules.utils')

def get_future_result(future: asyncio.Future) -> any:

    if future.exception() != None:
        return future.exception()

    try:
        return future.result()

    except asyncio.CancelledError:
        return None