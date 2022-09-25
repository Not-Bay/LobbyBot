from discord import Message
import fortnitepy
import logging

log = logging.getLogger('LobbyBot.clients.fortniteclient')

class Client(fortnitepy.Client):

    def __init__(self, session) -> None:
        super().__init__(
            auth = fortnitepy.DeviceAuth(
                device_id = session.auth.get('device_id'),
                account_id = session.auth.get('account_id'),
                secret = session.auth.get('secret'),
                ios_token = session.config.get('ios_token')
            ),
            default_party_config = fortnitepy.DefaultPartyConfig(
                privacy = get_privacy(session.config.get('party_privacy', 'PUBLIC')),
                max_size = session.config.get('party_max_size', 16),
                chat_enabled = session.config.get('party_chat_enabled', True)
            ),
            platform = get_platform(session.config.get('platform')),
            build = session.config.get('build'),
            os = session.config.get('os'),
            cache_users = False
        )

    @property
    def identifier(self):
        try:
            return self.user.id
        except:
            return self

    async def event_ready(self: fortnitepy.Client) -> None:

        log.debug(f'{self.identifier()} dispatched "event_ready"')

    async def event_before_close(self: fortnitepy.Client) -> None:

        log.debug(f'[{self.identifier()}] dispatched "event_before_close".')

    async def handle_message(self: fortnitepy.Client, message: Message) -> None:

        log.debug(f'[{self.identifier()}] handling message "{message.content}"...')

def get_privacy(privacy: str) -> fortnitepy.PartyPrivacy:

    if privacy == 'public':
        return fortnitepy.PartyPrivacy.PUBLIC
    if privacy == 'friends':
        return fortnitepy.PartyPrivacy.FRIENDS
    if privacy == 'private':
        return fortnitepy.PartyPrivacy.PRIVATE

def get_platform(platform: str) -> fortnitepy.Platform:

    if platform == 'pc':
        return fortnitepy.Platform.WINDOWS
    if platform == 'mobile':
        return fortnitepy.Platform.ANDROID
    if platform == 'psn':
        return fortnitepy.Platform.PLAYSTATION_4
    if platform == 'xbox':
        return fortnitepy.Platform.XBOX_ONE
    if platform == 'nintendo':
        return fortnitepy.Platform.SWITCH