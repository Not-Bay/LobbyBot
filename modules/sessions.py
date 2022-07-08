import fortnitepy
import discord
import logging
import asyncio
import time

from .fortnite import FortniteClient
from .utils import get_future_result

log = logging.getLogger('LobbyBot.modules.session')

class Session:

    def __init__(self, ctx: discord.ApplicationContext, account: dict, **kwargs):

        self.start_timestamp = int(time.time())

        self.override_config = kwargs.get('override_config', None)
        self.config = ctx.bot.config.get('fortnite')
        self.auth = account
        self.user = ctx.user
        self.bot = ctx.bot
        self.ctx = ctx

        self.handler = None # message handler
        self.client = None # fortnite client
        self.task = None # fortnite client task

    def identifier(self):
        try:
            return self.user.id
        except:
            return self

    async def initialize(self):

        log.debug(f'[{self.identifier()}] initializing...')

        # check if there is config to override (custom config)
        if self.override_config != None:
            self.config.update(self.override_config)
            log.debug(f'[{self.identifier()}] default config overrided')

        client = FortniteClient(self)
        task = asyncio.create_task(client.start())

        log.debug(f'[{self.identifier()}] waiting for event_ready...')

        login_timeout = self.config.get('login_timeout', 10)
        try:
            await asyncio.wait_for(client.wait_until_ready(), timeout=login_timeout)

            self.client = client
            self.task = task

            self.handler = asyncio.create_task(self.message_handler())

            return True

        except asyncio.TimeoutError:
            task.cancel()

            task_result = get_future_result(task)

            log.error(f'[{self.identifier()}] event_ready was never dispatched after {login_timeout} seconds. {task_result}')
            return task_result

    async def stop(self):

        log.debug(f'[{self.identifier()}] stopping...')

        close_task = asyncio.create_task(self.client.close())

        logout_timeout = self.config.get('logout_timeout', 5)
        try:
            await asyncio.wait_for(self.client.event_before_close(), timeout=logout_timeout)

            self.client = None
            self.task = None

            return True
        
        except asyncio.TimeoutError:

            self.handler.cancel()
            self.task.cancel()
            close_task.cancel()

            task_result = get_future_result(close_task)

            log.error(f'[{self.identifier()}] event_before_close was never dispatched after {logout_timeout} seconds. {task_result}')
            return task_result

    async def message_handler(self):

        log.debug(f'[{self.identifier()}] Message handler started.')

        # process only private messages from user
        def check(message: discord.Message):
            return (message.author.id == self.user.id) and (message.channel.is_private() == True)

        message_timeout = self.config.get('message_timeout', 300)

        while self.task != None:

            try:
                message = await self.bot.wait_for(
                    event = 'message',
                    check = check,
                    timeout = message_timeout
                )
                log.debug(f'[{self.identifier()}] received message, sending to client message_handler...')
                asyncio.create_task(self.client.handle_message(message))

            except asyncio.TimeoutError:

                log.debug(f'[{self.identifier()}] no messages received after {message_timeout} seconds.')
                await self.stop()

                break