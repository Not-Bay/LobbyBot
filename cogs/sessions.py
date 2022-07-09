from discord.commands import slash_command
from discord.ext import commands
import traceback
import logging
import discord
import asyncio

from modules import sessions, utils

log = logging.getLogger('LobbyBot.cogs.sessions')

class Sessions(commands.Cog):

    def __init__(self, bot: discord.Bot):
        self.bot = bot

    @slash_command(
        name = 'start',
        description = 'Starts a lobby bot'
    )
    async def start(
        self,
        ctx: discord.ApplicationContext
    ):

        for session in self.bot.sessions:
            if session.user.id == ctx.atuhor.id:
                return await ctx.respond(
                    embed = discord.Embed(
                        description = 'Seems like you already have an bot running. Use `/stop` before starting a new one.',
                        color = utils.Colors.Yellow
                    )
                )

        accounts = await self.bot.database.get_collection('accounts')

        result = await accounts.find_one(
            filter = {
                'in_use': False
            }
        )

        if result == None:
            return await ctx.respond(
                embed = discord.Embed(
                    description = 'All bots are currently in use, try again later.',
                    color = utils.Colors.Yellow
                )
            )

        log.debug(f'creating session with account {result.get("account_id")}...')

        try:

            update = await accounts.update_one(
                filter = {
                    'account_id': result['account_id']
                },
                update = {
                    'in_use': True
                }
            )

            if update == False:
                return await ctx.respond(
                    embed = discord.Embed(
                        description = 'Unable to lock assigned bot, try again later.',
                        color = utils.Colors.Red
                    )
                )

            session = sessions.Session(
                ctx = ctx,
                account = result
            )

            embed = discord.Embed(
                title = 'Starting',
                description = f'Your bot will be ready in a few seconds {utils.Emojis.Loading}',
                color = utils.Colors.Blue
            )

            try:
                # loading message in user dm
                message = await ctx.author.send(
                    embed = embed
                )

                self.bot.sessions.append(session)

                await ctx.respond(
                    embed = discord.Embed(
                        description = 'Your bot should be starting, check your direct messages.',
                        color = utils.Colors.Blue
                    ),
                    ephemeral = True
                )

            except discord.errors.Forbidden:

                embed = discord.Embed(
                    description = 'Seems like your direct messages are closed. Open them first to be able to start a bot.',
                    color = utils.Colors.Red
                )
                embed.set_footer(text = 'Settings > Privacy & Safety > Allow direct messages from server members')

                await accounts.update_one(
                    filter = {
                        'account_id': session.auth['account_id']
                    },
                    update = {
                        'in_use': False
                    }
                )

                return await ctx.respond(
                    embed = embed   
                )

            initialize = await session.initialize()

            if initialize != True:

                await accounts.update_one(
                    filter = {
                        'account_id': session.auth['account_id']
                    },
                    update = {
                        'in_use': False
                    }
                )

                return await message.edit(
                    embed = discord.Embed(
                        title = 'Unable to start',
                        description = f'An error ocurred starting your bot. {initialize}',
                        color = utils.Colors.Red
                    )
                )

            embed = discord.Embed(
                title = 'Your bot is ready!',
                description = f'Your bot `{session.client.user.display_name}` is ready.',
                color = utils.Colors.Green
            )
            embed.set_footer(text = 'Type help for a list of commands')

            await message.edit(embed = embed)

        except:

            log.error(f'Unable to start bot. {traceback.format_exc()}')

            await accounts.update_one(
                filter = {
                    'account_id': session.auth['account_id']
                },
                update = {
                    'in_use': False
                }
            )

            return await ctx.respond(
                embed = discord.Embed(
                    description = 'An unknown error ocurred, check logs for more info.',
                    color = utils.Colors.Red
                )
            )


    @slash_command(
        name = 'stop',
        description = 'Stops a lobby bot'
    )
    async def stop(
        self,
        ctx: discord.ApplicationContext
    ):

        for session in self.bot.sessions:
            if session.user.id == ctx.author.id:

                await ctx.defer()

                accounts = await self.bot.database.get_collection('accounts')

                # stop session
                await session.stop()

                # remove from global cache
                self.bot.sessions.remove(session)

                # make the account usable again
                await accounts.update_one(
                    filter = {
                        'account_id': session.auth['account_id']
                    },
                    update = {
                        'in_use': False
                    }
                )

                return await ctx.respond(
                    embed = discord.Embed(
                        description = 'Your bot was stopped correctly.',
                        color = utils.Colors.Green
                    )
                )

        await ctx.respond(
            embed = discord.Embed(
                description = 'Seems like you don\'t have any active bot right now.',
                color = utils.Colors.Red
            )
        )

def setup(bot: discord.Bot):
    bot.add_cog(Sessions(bot))
