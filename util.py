import fortnitepy
import requests
import datetime
import crayons
import discord
import asyncio
import pymongo
import string
import random
import json
import ast

bot_version = '1.7'

premium_requirement = False
allow_new_sessions = True
allow_new_custom_sessions = True
status_loop = True
active_sessions = []
used_ids = []

def custom_account_base():
    custom_account_base = {
        "configurated": False,
        "display_name": "",
        "outfit": "CID_028_Athena_Commando_F",
        "outfit_variants": [],
        "emote": "EID_KpopDance03",
        "backpack": "BID_138_Celestial",
        "backpack_variants": [],
        "pickaxe": "Pickaxe_ID_013_Teslacoil",
        "pickaxe_variants": [],
        "status": f"LobbyBot Custom",
        "level": 500,
        "platform": "pc",
        "privacy": "private",
        "device_id": "",
        "account_id": "",
        "secret": ""
    }
    return custom_account_base

def get_config():
    return json.load(open('configuration.json', 'r', encoding='utf-8'))

database = pymongo.MongoClient(get_config()['db_connectionstr']).lobbybot

def discord_log(content=None, embeds=None):

    webhook_url = get_config()['webhook']

    if webhook_url != "":

        payload = {
            "content": f"`{datetime.datetime.now().strftime('%H:%M:%S')}` {content}",
            "embeds": embeds,
            "username": "LobbyBot Logs",
            "avatar_url": "https://cdn.discordapp.com/avatars/761360995117170748/02c9a2ba3b4cafed2d05c690f9ea3bdb.webp"
        }
        requests.post(webhook_url, json=payload)

def log(content: str, level='normal'):

    now = datetime.datetime.now().strftime('%d/%m/%y %H:%M:%S')

    if level == 'normal':
        print(f'{crayons.green(f"[{now}]")} {content}')

    elif level == 'error':
        print(f'{crayons.green(f"[{now}]")} {crayons.red("[ERROR]")} {content}')

    elif level == 'debug':
        if get_config()['debug']:
            print(f'{crayons.green(f"[{now}]")} {crayons.yellow("[DEBUG]")} {content}')


def store_guild(guild):

    result = database.guilds.find_one({"guild_id": guild.id})

    if result == None:
        data = {
            "guild_id": guild.id,
            "lb_channel": None,
            "prefix": get_config()['prefix']
        }
        return database.guilds.insert_one(data)
    else:
        return result

def remove_guild(guild):

    database.guilds.find_one_and_delete({"guild_id": guild.id})


def update_guild(guild, config, value):

    store_guild(guild)
    return database.guilds.find_one_and_update({"guild_id": guild.id}, {"$set": {config: value}})


def get_prefix(bot, message):

    if isinstance(message.guild, discord.Guild):
        return store_guild(message.guild)['prefix']
    else:
        return get_config()['prefix']


def store_user(id_):

    user = database.users.find_one({"user_id": id_})
    if user == None:
        data = {
            "user_id": id_,
            "premium": False,
            "premium_since": None,
            "custom_account": custom_account_base()
        }
        return database.users.insert_one(data)
    else:
        return user


def remove_user(user):

    return database.users.find_one_and_delete({"user_id": user.id})

def gen_id():
    while True:
        chars = []
        chars.extend(string.ascii_lowercase)
        chars.extend(string.digits)
        
        id_ = ''.join(random.choice(chars) for i in range(5))
        if id_ not in used_ids:
            used_ids.append(id_)
            return id_
        else:
            continue

def get_friend_status_emoji(friend):

    if friend.is_online() == True:
        if friend.last_presence:
            if friend.last_presence.away in [fortnitepy.AwayStatus.AWAY, fortnitepy.AwayStatus.EXTENDED_AWAY]:
                return '<:away:856373088219037748>'
            else:
                return '<:online:856373054107025429>'
        else:
            return '<:online:856373054107025429>'
    else:
        return '<:offline:856373113319456778>'

async def discord_bot_status_loop(bot):
    while bot.is_ready():
        if status_loop:
            if allow_new_sessions != True:
                status = discord.Status.idle
            else:
                status = discord.Status.online
            await bot.change_presence(status=status, activity=discord.Activity(type=discord.ActivityType.watching, name=f'{len(active_sessions)} active bots!'))
            await asyncio.sleep(30)
            await bot.change_presence(status=status, activity=discord.Activity(type=discord.ActivityType.watching, name=f'{len(bot.guilds)} servers'))
            await asyncio.sleep(30)
            await bot.change_presence(activity=discord.Game(name=f'beta {bot_version}!'))
            await asyncio.sleep(30)
        else:
            await asyncio.sleep(1)

class Cosmetics:

    def __init__(self):

        self.outfits = []
        self.emotes = []
        self.backpacks = []
        self.pickaxes = []

    def _load_cosmetics(self):

        response = requests.get('https://fortnite-api.com/v2/cosmetics/br')

        if response.status_code != 200:
            return

        for cosmetic in response.json()['data']:

            if cosmetic['type']['value'] == 'outfit':
                self.outfits.append(cosmetic)
            elif cosmetic['type']['value'] == 'emote':
                self.emotes.append(cosmetic)
            elif cosmetic['type']['value'] == 'backpack':
                self.backpacks.append(cosmetic)
            elif cosmetic['type']['value'] == 'pickaxe':
                self.pickaxes.append(cosmetic)
        
        return True

    async def get(self, type_: str, name=None, id_=None):

        if len(self.outfits) == 0:
            self._load_cosmetics()

        if type_ == 'outfit':
            data = self.outfits
        elif type_ == 'emote':
            data = self.emotes
        elif type_ == 'backpack':
            data = self.backpacks
        elif type_ == 'pickaxe':
            data = self.pickaxes

        results = []

        for cosmetic in data:
            if id_ != None:
                if cosmetic['id'].lower() == id_.lower():
                    return cosmetic
            
            if name != None:
                if cosmetic['name'].lower().startswith(name.lower()):
                    results.append(cosmetic)
        
        return results

async def get_variants(client, type_, variant_channel=None, selected_int=None, selected=None):
    # idk how i get this working but it works ¯\_(ツ)_/¯
    config_overrides = {"item": type_, variant_channel: selected['tag']}
    if variant_channel != None:
        if variant_channel == 'pattern':
            variants = client.party.me.create_variant(config_overrides=config_overrides, pattern=str(selected_int))
        if variant_channel == 'numeric':
            variants = client.party.me.create_variant(config_overrides=config_overrides, numeric=str(selected_int))
        if variant_channel == 'clothingcolor':
            variants = client.party.me.create_variant(config_overrides=config_overrides, clothing_color=str(selected_int))
        if variant_channel == 'jerseycolor':
            variants = client.party.me.create_variant(config_overrides=config_overrides, jersey_color=str(selected_int))
        if variant_channel == 'parts':
            variants = client.party.me.create_variant(config_overrides=config_overrides, parts=str(selected_int))
        if variant_channel == 'progressive':
            variants = client.party.me.create_variant(config_overrides=config_overrides, progressive=str(selected_int))
        if variant_channel == 'particle':
            variants = client.party.me.create_variant(config_overrides=config_overrides, particle=str(selected_int))
        if variant_channel == 'material':
            variants = client.party.me.create_variant(config_overrides=config_overrides, material=str(selected_int))
        if variant_channel == 'emissive':
            variants = client.party.me.create_variant(config_overrides=config_overrides, emissive=str(selected_int))
        if variant_channel == 'hair':
            variants = client.party.me.create_variant(config_overrides=config_overrides, hair=str(selected_int))
        if variant_channel == 'mesh':
            variants = client.party.me.create_variant(config_overrides=config_overrides, mesh=str(selected_int))

        return variants

def insert_returns(body):

    if isinstance(body[-1], ast.Expr):
        body[-1] = ast.Return(body[-1].value)
        ast.fix_missing_locations(body[-1])

    if isinstance(body[-1], ast.If):
        insert_returns(body[-1].body)
        insert_returns(body[-1].orelse)

    if isinstance(body[-1], ast.With):
        insert_returns(body[-1].body)
