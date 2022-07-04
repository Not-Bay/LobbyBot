import fortnitepy
import logging

log = logging.getLogger('LobbyBot.modules.fortnite.utils')

class MyClientParty(fortnitepy.ClientParty):

    def __init__(self, client: fortnitepy.Client, data: dict) -> None:
        super().__init__(client, data)
        self._hides = []
        self.party_chat = []

    @property
    def voice_chat_enabled(self) -> bool:
        return self.meta.get_prop('VoiceChat:implementation_s') in [
            'VivoxVoiceChat',
            'EOSVoiceChat'
        ]

    def update_hide_users(self, user_ids: list) -> None:
        self._hides = user_ids

    def add_hide_user(self, user_id: str) -> bool:
        if user_id not in self._hides:
            self._hides.append(user_id)
            return True
        return False

    def remove_hide_user(self, user_id: str) -> bool:
        if user_id in self._hides:
            self._hides.remove(user_id)
            return True
        return False

    async def hide(self, member: fortnitepy.PartyMember) -> None:
        if self.me is not None and not self.me.leader:
            raise fortnitepy.Forbidden('You have to be leader for this action to work.')

        self.add_hide_user(member.id)
        if member.id in self._members.keys():
            await self.refresh_squad_assignments()

    async def show(self, member: fortnitepy.PartyMember) -> None:
        if self.me is not None and not self.me.leader:
            raise fortnitepy.Forbidden('You have to be leader for this action to work.')

        self.remove_hide_user(member.id)
        if member.id in self._members.keys():
            await self.refresh_squad_assignments()

    def _convert_squad_assignments(self, assignments):
        results = []
        sub = 0
        for member, assignment in assignments.items():
            if assignment.hidden or member.id in self._hides:
                sub += 1
                continue

            results.append({
                'memberId': member.id,
                'absoluteMemberIdx': assignment.position - sub,
            })

        return results

    async def disable_voice_chat(self) -> None:
        if self.me is not None and not self.me.leader:
            raise fortnitepy.Forbidden('You have to be leader for this action to work.')

        prop = self.meta.set_voicechat_implementation('None')
        if not self.edit_lock.locked():
            await self.patch(updated=prop)

    async def enable_voice_chat(self) -> None:
        if self.me is not None and not self.me.leader:
            raise fortnitepy.Forbidden('You have to be leader for this action to work.')

        prop = self.meta.set_voicechat_implementation('EOSVoiceChat')
        if not self.edit_lock.locked():
            await self.patch(updated=prop)


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

    if platform == 'ps':
        return fortnitepy.Platform.PLAYSTATION_4

    if platform == 'xbox':
        return fortnitepy.Platform.XBOX_ONE

    if platform == 'nintendo':
        return fortnitepy.Platform.SWITCH