from discord import Message
import fortnitepy
import logging

from .events import *
from .client_utils import *

log = logging.getLogger('LobbyBot.modules.fortnite.client')

# Used for adding/removing accounts
class AuthClient(fortnitepy.Client):

    def __init__(self, config: dict, **kwargs):

        if kwargs.get('authorization_code', None) != None:
            log.debug(f'[{self}] using authorization_code authentication')
            selected_auth = fortnitepy.AuthorizationCodeAuth(
                code = kwargs.get('authorization_code'),
                ios_token = config.get('ios_token')
            )
        
        else:
            log.debug(f'[{self}] using device_auth authentication')
            selected_auth = fortnitepy.DeviceAuth(
                device_id = kwargs.get('device_id'),
                account_id = kwargs.get('account_id'),
                secret = kwargs.get('secret'),
                ios_token = config.get('ios_token')
            )

        super().__init__(
            auth = selected_auth,
            build = config.get('build'),
            os = config.get('os'),
            cache_users = False
        )

        self.add_event_handler('event_ready', event_ready)

    def identifier(self):
        try:
            return self.user.id
        except:
            return self

# Used for normal clients
class FortniteClient(fortnitepy.Client):

    def __init__(self, session):

        self.session = session

        super().__init__(
            auth = fortnitepy.DeviceAuth(
                device_id = session.auth.get('device_id'),
                account_id = session.auth.get('account_id'),
                secret = session.auth.get('secret'),
                ios_token = session.config.get('ios_token')
            ),
            default_party_config = fortnitepy.DefaultPartyConfig(
                privacy = get_privacy(session.config.get('party')['privacy']),
                max_size = session.config.get('party')['max_size'],
                chat_enabled = session.config.get('party')['chat_enabled'],
                cls = MyClientParty
            ),
            build = session.config.get('build'),
            os = session.config.get('os'),
            platform = get_platform(session.config.get('platform')),
            cache_users = False
        )

        self.add_event_handler('event_ready', event_ready)
        self.add_event_handler('event_before_close', event_before_close)

    def identifier(self):
        try:
            return self.user.id
        except:
            return self
