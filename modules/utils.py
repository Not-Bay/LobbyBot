import asyncio
import logging

log = logging.getLogger('LobbyBot.modules.utils')

def user_base():
    return {
        'id': '',
        'added': 0,
        'banned': False,
        'config': {
            'status': 'LobbyBot v2.0',
            'platform': 'pc',
            'party_chat_enabled': True,
            'party_privacy': 'public',
            'party_max_size': 16
        },
        'bots': {}
    }

def bot_base():
    return {
        'added': 0,
        'device_id': '',
        'account_id': '',
        'secret': ''
    }

class Colors:

    Red = 0xe62222
    Green = 0x2ee32b
    Blue = 0x2173c4
    Yellow = 0xd1c926

class Emojis:

    Loading = '<a:loading:815646116154310666>'
