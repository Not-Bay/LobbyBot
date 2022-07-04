import fortnitepy
import logging

log = logging.getLogger('LobbyBot.modules.fortnite.events')

async def event_ready(self: fortnitepy.Client) -> None:

    log.debug(f'{self.identifier()} dispatched "event_ready"')

async def event_before_close(self: fortnitepy.Client) -> None:

    log.debug(f'[{self.identifier()}] dispatched "event_before_close".')