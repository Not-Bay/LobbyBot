# pylint: disable=maybe-no-member
from discord.ext import commands
from discord_components import *
import discord

import time
import traceback
import crayons
import util


boot_timestamp = time.time()
util.discord_log('Booting...')

util.log(f'{crayons.cyan("Starting LobbyBot")}')
util.log(f'Debug enabled', 'debug')

intents = discord.Intents.default()
intents.members = True

bot = commands.AutoShardedBot(
    command_prefix = util.get_prefix,
    intents = intents
)
bot.remove_command('help')

@bot.event
async def on_connect():
    util.log('Connected to discord', 'debug')
    await bot.change_presence(activity=discord.Activity(type=discord.ActivityType.playing, name=f"Booting..."), status=discord.Status.idle)

@bot.event
async def on_ready():
    DiscordComponents(bot)

    for guild in bot.guilds:
        util.store_guild(guild)

    util.log('Loading cogs...')
    cogs = util.get_config()['cogs']
    for i in cogs:
        try:
            bot.load_extension(f'cogs.{i}')
            util.log(f'Loaded "{i}"', 'debug')
        except Exception:
            util.log(f'Could not load cog "{i}": {crayons.red(traceback.format_exc())}', 'error')

    util.log('Starting status...')
    bot.loop.create_task(util.discord_bot_status_loop(bot))

    util.log('Setting accounts as unused...')
    while True:
        account = util.database.credentials.find_one_and_update({"active": True}, {"$set": {"active": False}})
        if account == None:
            break

    util.log(f'{crayons.white("|", bold=True)} Discord bot is ready as {crayons.green(bot.user, bold=True)} - {bot.user.id} {crayons.white("|", bold=True)}')

    util.discord_log(f'LobbyBot is ready!')

super_secret_token = util.get_config()['token']
bot.run(super_secret_token)