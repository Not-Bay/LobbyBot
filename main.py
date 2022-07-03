import coloredlogs
import traceback
import discord
import asyncio
import logging
import orjson
import sys

from modules import database

if '--debug' in sys.argv:
    log_level = logging.DEBUG
else:
    log_level = logging.INFO

__version__ = '2.0alpha'

if __name__ == '__main__':

    log = logging.getLogger('LobbyBot.main')

    for logger in list(logging.Logger.manager.loggerDict):
        if logger.startswith('LobbyBot') == False:
            logging.getLogger(logger).disabled = True

    # file output
    file_handler = logging.FileHandler('logs.log')
    file_handler.setLevel(log_level)
    
    formatter = logging.Formatter('%(asctime)s | %(levelname)s | %(message)s')
    file_handler.setFormatter(formatter)

    logging.getLogger('LobbyBot').addHandler(file_handler)

    # Colored output
    coloredlogs.install(level = log_level)

    # initialization
    try:
        log.debug('loading configuration...')
        with open('config.json', 'r', encoding='utf-8') as f:
            config = orjson.loads(f.read())
    except:
        log.critical(f'Unable to load config file. {traceback.format_exc()}')
        sys.exit(1)

    bot = discord.Bot(
        debug_guilds = config.get('debug_guilds', None),
        auto_sync_commands = config.get('auto_sync_commands', False),
        intents = discord.Intents.default()
    )
    bot.database = database.DatabaseClient(config.get('database'))
    bot.config = config
    bot.version = __version__

    log.debug('loading cogs...')
    for cog in config.get('cogs', []):
        try:
            bot.load_extension(f'cogs.{cog}')
            log.debug(f'loaded cog "{cog}".')
        except:
            log.error(f'Unable to load cog "{cog}". {traceback.format_exc()}')
    
    log.debug(f'{len(bot.extensions)}/{len(config.get("cogs", []))} cogs loaded.')

    # setup uvloop
    try:
        import uvloop # type: ignore
        asyncio.set_event_loop_policy(uvloop.EventLoopPolicy())
        log.debug('using uvloop event loop policy.')
    except:
        log.debug('unable to setup uvloop, using default event loop policy.')

    # start

    log.info('Starting...')

    loop = asyncio.get_event_loop()

    try:
        loop.run_until_complete(bot.start(config.get('bot_token')))

    except KeyboardInterrupt:
        log.info('KeyboardInterrupt, exiting...')
        loop.run_until_complete(bot.close())

    except Exception:
        log.critical(f'An unknown error ocurred: {traceback.format_exc()}')
        loop.run_until_complete(bot.close())

    finally:
        loop.close()
        sys.exit()
