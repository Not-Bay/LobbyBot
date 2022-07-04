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
            return await ctx.respond(
                embed = discord.Embed(
                    description = 'You are not allowed to use this command.',
                    color = utils.Colors.Red
                ),
                ephemeral = True
            )

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

            embed = discord.Embed(
                description = f'Saved account `{client.user.display_name}` correctly.',
                color = utils.Colors.Green
            )
            embed.set_footer(text = f'ID {data.get("accountId")}')

            await ctx.respond(embed = embed)
            
            asyncio.create_task(client.close())

        except asyncio.TimeoutError:

            asyncio.create_task(client.close())

            return await ctx.respond(
                embed = discord.Embed(
                    description = f'Timeout adding the account. {utils.get_future_result(task)}',
                    color = utils.Colors.Red
                ),
                ephemeral = True
            )

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
            return await ctx.respond(
                embed = discord.Embed(
                    description = 'You are not allowed to use this command.',
                    color = utils.Colors.Red
                ),
                ephemeral = True
            )

        accounts = await self.bot.database.get_collection('accounts')

        result = await accounts.find_one(
            filter = {
                'account_id': account_id
            }
        )

        if result == None:
            return await ctx.respond(
                embed = discord.Embed(
                    description = f'No matching account found with `{account_id}`',
                    color = utils.Colors.Red
                ),
            )

        client = fortnite.AuthClient(
            config = self.bot.config.get('fortnite'),
            device_id = result.get('device_id'),
            account_id = result.get('account_id'),
            secret = result.get('secret')
        )

        task = asyncio.create_task(client.start())

        log.debug('waiting for client ready...')

        await ctx.defer()

        deleted_flag = False

        try:
            await asyncio.wait_for(client.wait_until_ready(), timeout=10)

            await client.auth.delete_device_auth(device_id = result.get('device_id'))
            deleted_flag = True

            log.debug('deleted device auth correctly')

            asyncio.create_task(client.close())

        except asyncio.TimeoutError:

            asyncio.create_task(client.close())

            log.error(f'Timeout logging into the account. `{utils.get_future_result(task)}`')

        log.debug('Removing account from database...')

        delete = await accounts.delete_one(
            filter = {
                'account_id': result.get('account_id')
            }
        )

        if delete != True:
            embed = discord.Embed(
                description = 'Unable to remove account from database.',
                color = utils.Colors.Red
            )
            if deleted_flag == True:
                embed.description += ' Device auth was deleted anyway.'
            
            return await ctx.respond(embed = embed)

        embed = discord.Embed(
            description = f'Removed account `{result.get("display_name")}` correctly.',
            color = utils.Colors.Green
        )
        if deleted_flag == False:
            embed.set_footer(text = 'Device auth wasn\'t deleted!')

        await ctx.respond(embed = embed)


def setup(bot: discord.Bot):
    bot.add_cog(Admin(bot))
