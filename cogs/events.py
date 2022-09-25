from discord.ext import commands
import logging
import discord

log = logging.getLogger('LobbyBot.cogs.events')

class Events(commands.Cog):

    def __init__(self, bot: discord.Bot):
        self.bot = bot

    @commands.Cog.listener()
    async def on_connect(self):

        log.debug('dispatched on_connect')

    @commands.Cog.listener()
    async def on_ready(self):

        log.info('Discord bot is ready.')

def setup(bot: discord.Bot):
    bot.add_cog(Events(bot))
