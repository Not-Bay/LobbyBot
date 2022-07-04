from discord.commands import slash_command, Option
from discord.ext import commands
import logging
import asyncio
import discord
import time

from modules import utils, fortnite

log = logging.getLogger('LobbyBot.cogs.admin')

class Admin(commands.Cog):

    def __init__(self, bot: discord.Bot):
        self.bot = bot

    @slash_command(
        name = 'add-account',
        description = 'Adds an account to the database'
    )
    async def add_account(
        self,
        ctx: discord.ApplicationContext,
        code: Option(
            input_type = str,
            description = '32 digit code',
            required = True
        )
    ):

        if await self.bot.is_owner(ctx.author) != True:
            return await ctx.respond('You are not allowed to use this command.', ephemeral = True)

        log.debug(f'adding account with code "{code}"')

        client = fortnite.AuthClient(
            config = self.bot.config.get('fortnite'),
            authorization_code = code
        )

        task = asyncio.create_task(client.start())

        log.debug('waiting for client ready...')

        await ctx.defer()

        try:
            await asyncio.wait_for(client.wait_until_ready(), timeout=10)

            data = await client.auth.generate_device_auth()

            log.debug(f'generated device auths correctly: "{data}"')

            accounts = await self.bot.database.get_collection('accounts')

            await accounts.insert_one(
                document = {
                    'in_use': False,
                    'added': int(time.time()),
                    'display_name': client.user.display_name,
                    'device_id': data.get('deviceId'),
                    'account_id': data.get('accountId'),
                    'secret': data.get('secret')
                }
            )
            log.debug('saved credentials in the database correctly.')

            await ctx.respond(f'Saved account `{client.user.display_name}` correctly.')
            
            asyncio.create_task(client.close())

        except asyncio.TimeoutError:
            
            await ctx.respond(f'Timeout adding the account. `{utils.get_future_result(task)}`')

    @slash_command(
        name = 'remove-account',
        description = 'Removes an account from the database'
    )
    async def remove_account(
        self,
        ctx: discord.ApplicationContext,
        account_id: Option(
            input_type = str,
            description = 'Account ID',
            required = True
        )
    ):

        if await self.bot.is_owner(ctx.author) != True:
            return await ctx.respond('You are not allowed to use this command.', ephemeral = True)

        accounts = await self.bot.database.get_collection('accounts')

        result = await accounts.find_one(
            filter = {
                'account_id': account_id
            }
        )

        if result == None:
            await ctx.respond(f'No matching accounts found with `{account_id}`')
            return

        client = fortnite.AuthClient(
            config = self.bot.config.get('fortnite'),
            device_id = result.get('device_id'),
            account_id = result.get('account_id'),
            secret = result.get('secret')
        )

        task = asyncio.create_task(client.start())

        log.debug('waiting for client ready...')

        await ctx.defer()

        try:
            await asyncio.wait_for(client.wait_until_ready(), timeout=10)

            await client.auth.delete_device_auth(device_id = result.get('device_id'))
            log.debug('deleted device auth correctly')

            asyncio.create_task(client.close())

        except asyncio.TimeoutError:

            log.error(f'Timeout logging into the account. `{utils.get_future_result(task)}`')

        log.debug('Removing account from database...')

        delete = await accounts.delete_one(
            filter = {
                'account_id': result.get('account_id')
            }
        )

        if delete != True:
            await ctx.respond(f'Unable to remove account from database.')
            return

        await ctx.respond(f'Removed account `{result.get("display_name")}` correctly.')


def setup(bot: discord.Bot):
    bot.add_cog(Admin(bot))
