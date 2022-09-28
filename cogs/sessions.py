from discord.commands import slash_command
from discord.ext import commands
import logging
import discord
import asyncio

from modules import crypto, sessions, utils

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

        if self.bot.sessions.get_session(ctx.author.id) != None:
            return await ctx.respond(
                embed = discord.Embed(
                    description = 'Seems like you already have an bot running. Use `/stop` before starting a new one.',
                    color = utils.Colors.Yellow
                )
            )

        collection = await self.bot.database.get_collection('users')
        user = await collection.find_one(
            filter = {
                'id': crypto.sha1(str(ctx.author.id))
            }
        )

        if user == None:

            await ctx.respond(
                embed = discord.Embed(
                    title = 'Oops!',
                    description = 'You need to register with `/account register` first.',
                    color = discord.Color.red()
                )
            )
            return

        if len(user['bots']) == 0:
            
            await ctx.respond(
                embed = discord.Embed(
                    title = 'Oops!',
                    description = 'You do not have any account added yet, use `/add-bot` to add one.',
                    color = discord.Color.red()
                )
            )
            return

        elif len(user['bots']) == 1:

            account_index = list(user['bots'].keys())[0]
            selected_account = user['bots'][account_index]

            await ctx.respond(
                embed = discord.Embed(
                    title = 'Start Bot',
                    description = 'Starting...'
                )
            )

        else:

            options = []

            for account in user['bots']:

                options.append(
                    discord.SelectOption(
                        label = crypto.decrypt_user_string(ctx.author.id, self.bot.ekey, user['bots'][account]['display_name']),
                        value = account
                    )
                )

            view = discord.ui.View(
                discord.ui.Select(
                    options = options,
                    custom_id = 'select_start'
                ),
                timeout = 120,
                disable_on_timeout = True
            )

            await ctx.respond(
                embed = discord.Embed(
                    title = 'Start Bot',
                    description = 'Select the bot you want to start:',
                    color = discord.Color.blue()
                ),
                view = view
            )

            try:
                interaction = await self.bot.wait_for(
                    'interaction',
                    check = lambda i: i.user == ctx.author and i.custom_id in 'select_start',
                    timeout = 120
                )
            except asyncio.TimeoutError:
                return

            selected_account = user['bots'][view.children[0].values[0]]

            await interaction.edit_original_message(
                embed = discord.Embed(
                    title = 'Start Bot',
                    description = 'Starting...'
                )
            )
        
        session = sessions.Session(
            ctx = ctx,
            account = {
                'device_id': crypto.decrypt_user_string(ctx.author.id, self.bot.ekey, selected_account['device_id']),
                'account_id': crypto.decrypt_user_string(ctx.author.id, self.bot.ekey, selected_account['account_id']),
                'secret': crypto.decrypt_user_string(ctx.author.id, self.bot.ekey, selected_account['secret']),
            }
        )
        add_session = self.bot.sessions.add_session(session)

        if add_session != True:
            await ctx.interaction.edit_original_message(
                embed = discord.Embed(
                    title = 'Start Bot',
                    description = 'An error ocurred registering your session, please try again later.',
                    color = discord.Color.red()
                ),
                view = None
            )
            return

        start = await session.start()

        if start == True:

            await ctx.interaction.edit_original_message(
                embed = discord.Embed(
                    title = 'Start Bot',
                    description = 'Your bot has been started.',
                    color = discord.Color.green()
                ),
                view = None
            )

        else:

            await ctx.interaction.edit_original_message(
                embed = discord.Embed(
                    title = 'Start Bot',
                    description = f'An error ocurred starting your bot: `{start}`',
                    color = discord.Color.red()
                ),
                view = None
            )

    @slash_command(
        name = 'stop',
        description = 'Stops a lobby bot'
    )
    async def stop(
        self,
        ctx: discord.ApplicationContext
    ):

        user_session = self.bot.sessions.get_session(ctx.author.id)
        if user_session == None:
            await ctx.respond(
                embed = discord.Embed(
                    description = 'Seems like you don\'t have any active bot right now.',
                    color = utils.Colors.Red
                )
            )
            return

        await ctx.defer()

        accounts = await self.bot.database.get_collection('accounts')

        # stop session
        await user_session.stop()

        # delete session from SessionManager
        self.bot.sessions.remove_session(user_session)

        await ctx.respond(
            embed = discord.Embed(
                description = 'Your bot was stopped correctly.',
                color = utils.Colors.Green
            )
        )

def setup(bot: discord.Bot):
    bot.add_cog(Sessions(bot))
