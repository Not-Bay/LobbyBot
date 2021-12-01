import datetime
from discord.ext import commands
import fortnitepy
import traceback
import discord
import string
import random
import crayons
import asyncio
import time

import util
import ast

from util import Cosmetics, insert_returns, log, database, get_config, get_variants
from functools import partial

from typing import (TYPE_CHECKING, Any, Awaitable, Callable, Dict, List,
                    Optional, Tuple, Type, Union)

class MyClientParty(fortnitepy.ClientParty): ## From https://github.com/gomashio1596/Fortnite-LobbyBot-v2
    def __init__(self, client: 'Client', data: dict) -> None:
        super().__init__(client, data)
        self._hides = []
        self.party_chat = []

    @property
    def voice_chat_enabled(self) -> bool:
        return self.meta.get_prop('VoiceChat:implementation_s') in [
            'VivoxVoiceChat',
            'EOSVoiceChat'
        ]

    def update_hide_users(self, user_ids: List[str]) -> None:
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

    def construct_presence(self, text: Optional[str] = None) -> dict:
        perm = self.config['privacy']['presencePermission']
        if perm == 'Noone' or (perm == 'Leader' and (self.me is not None
                                                     and not self.me.leader)):
            join_data = {
                'bInPrivate': True
            }
        else:
            join_data = {
                'sourceId': self.client.user.id,
                'sourceDisplayName': self.client.user.display_name,
                'sourcePlatform': self.client.platform.value,
                'partyId': self.id,
                'partyTypeId': 286331153,
                'key': 'k',
                'appId': 'Fortnite',
                'buildId': self.client.party_build_id,
                'partyFlags': -2024557306,
                'notAcceptingReason': 0,
                'pc': self.member_count,
            }

        status = text or self.client.status
        kairos_profile = self.client.avatar.to_dict()
        kairos_profile['avatar'] = kairos_profile['avatar'].format(
            bot=self.me.outfit
        )

        try:
            status  = self.client.eval_format(
                status,
                self.client.variables
            )
        except Exception:
            status = None

        _default_status = {
            'Status': status,
            'bIsPlaying': False,
            'bIsJoinable': False,
            'bHasVoiceSupport': False,
            'SessionId': '',
            'ProductName': 'Fortnite',
            'Properties': {
                'KairosProfile_j': kairos_profile,
                'party.joininfodata.286331153_j': join_data,
                'FortBasicInfo_j': {
                    'homeBaseRating': 1,
                },
                'FortLFG_I': '0',
                'FortPartySize_i': 1,
                'FortSubGame_i': 1,
                'InUnjoinableMatch_b': False,
                'FortGameplayStats_j': {
                    'state': '',
                    'playlist': 'None',
                    'numKills': 0,
                    'bFellToDeath': False,
                },
                'GamePlaylistName_s': self.meta.playlist_info[0],
                'Event_PlayersAlive_s': '0',
                'Event_PartySize_s': str(len(self._members)),
                'Event_PartyMaxSize_s': str(self.max_size),
            },
        }
        return _default_status


class Session:

    def __init__(self, ctx, account, session_id, **kwargs):
        
        self.is_custom = kwargs.get('custom', False)
        self.custom_config = kwargs.get('custom_config', False)
        self.active = True
        self.ready = False
        self._id = session_id
        self._startTime = time.time()
        self.ctx = ctx
        self.account = account
        self.client = Client(account, ctx.bot, ctx.message, session_id, account, kwargs.get('custom', False))
        database.credentials.find_one_and_update({"display_name": self.account["display_name"]}, {"$set": {"active": True}})

    async def start_client(self):
        log(f'{self.account["display_name"]} starting...', 'debug')
        try:
            start = asyncio.create_task(self.client.start())
            try:
                await asyncio.wait_for(self.client.wait_until_ready(), timeout=10)
                log(f'{self.account["display_name"]} started!', 'debug')
                self.ready = True
                return True
            except Exception:
                log(f'Could not start account {self.account["display_name"]}: {start.result()}', 'error')
                await asyncio.create_task(self.stop_client())
                return start.exception()
        except:
            return Exception


    async def stop_client(self):

        self.active = False
        self.ctx = None
        log(f'{self.account["display_name"]} stopping...', 'debug')
        asyncio.create_task(self.client.close())
        try:
            util.active_sessions.remove(self)
            util.used_ids.remove(self._id)
        except:
            pass
        log(f'{self.account["display_name"]} stopped!', 'debug')
        database.credentials.find_one_and_update({"display_name": self.account["display_name"]}, {"$set": {"active": False}})
        return True

    async def restart_client(self):

        log(f'{self.account["display_name"]} restarting...', 'debug')
        try:
            await asyncio.wait_for(self.client.restart(), timeout=10)
            log(f'{self.account["display_name"]} restarted!', 'debug')
            return True
        except asyncio.TimeoutError:
            return False

    async def handle_messages(self):

        self.ready = True

        log(f'{crayons.blue(self.account["display_name"])} message handling started', 'debug')
        
        def check(message):
                return message.author == self.ctx.author and message.channel == self.ctx.channel

        while self.active:

            try:
                message = await self.ctx.bot.wait_for('message', check=check, timeout=util.get_config()['session_timeout'] if self.is_custom == False else util.get_config()['custom_session_timeout'])
                asyncio.create_task(self.client.handle_command(message=message))

            except asyncio.TimeoutError:


                if self.ctx != None:

                    await self.ctx.send(embed=discord.Embed(
                        description = 'Finished due to inactivity.',
                        color = 0xff2929
                    ).set_author(name=f'{self.client.user.display_name} - {self._id}'))
                    asyncio.create_task(self.stop_client())
                    break

        log(f'{crayons.blue(self.account["display_name"])} message handling finished.', 'debug')


class Client(fortnitepy.Client):

    def __init__(self, deviceauths, bot, message, session_id, account, is_custom):
        self.is_custom = is_custom
        self.account = account
        self.bot = bot
        self.message = message
        self.cosmetics = Cosmetics()
        self.session_id = session_id
        self.platform = util.database.users.find_one({"user_id": self.message.author.id})['custom_account']['platform'] if is_custom == True else 'pc'
        self.privacy = util.database.users.find_one({"user_id": self.message.author.id})['custom_account']['privacy'] if is_custom == True else 'public'
        self.defaultoutfit = random.choice(get_config()['default_config']['outfits'])
        self.init_connect = True
        self.in_match_timestamp = None

        super().__init__(
            auth=fortnitepy.AdvancedAuth(
                device_id=deviceauths['device_id'],
                account_id=deviceauths['account_id'],
                secret=deviceauths['secret']
            ),
            cache_users=False,
            default_party_config=fortnitepy.DefaultPartyConfig(
                cls=MyClientParty,
                privacy=fortnitepy.PartyPrivacy.PUBLIC if self.privacy == 'public' else fortnitepy.PartyPrivacy.FRIENDS if self.privacy == 'friends' else fortnitepy.PartyPrivacy.PRIVATE
            ),
            platform=fortnitepy.Platform.WINDOWS if self.platform == 'pc' else fortnitepy.Platform.PLAYSTATION_4 if self.platform == 'psn' else fortnitepy.Platform.XBOX_ONE if self.platform == 'xbox' else fortnitepy.Platform.SWITCH if self.platform == 'switch' else fortnitepy.Platform.ANDROID
        )

    async def get_outfit_icon(self, outfit):
        result = await self.cosmetics.get(type_='outfit', id_=outfit)
        return result['images']['smallIcon']

    async def event_before_close(self):

        if self.is_custom == True:
            return

        self.message == None

        for friend in self.friends:
            await friend.remove()

        for user in self.pending_friends:

            if isinstance(user, fortnitepy.IncomingPendingFriend):
                await user.decline()
            else:
                await user.cancel()

    async def event_ready(self):

        await self.set_presence(status=get_config()['default_config']['status'] if self.is_custom == False else util.database.users.find_one({"user_id": self.message.author.id})['custom_account']['status'])

        defaultconfig = get_config()['default_config']

        if self.is_custom == True:
            await self.party.me.edit_and_keep(partial(self.party.me.set_outfit, asset=self.account['outfit'], variants=self.account['outfit_variants']))
            await self.party.me.edit_and_keep(partial(self.party.me.set_emote, asset=self.account['emote']))
            await self.party.me.edit_and_keep(partial(self.party.me.set_backpack, asset=self.account['backpack'], variants=self.account['backpack_variants']))
            await self.party.me.edit_and_keep(partial(self.party.me.set_pickaxe, asset=self.account['pickaxe'], variants=self.account['pickaxe_variants']))
            await self.party.me.edit_and_keep(partial(self.party.me.set_banner, icon=defaultconfig['banner'], color=defaultconfig['bannercolor'], season_level=self.account['level']))
            await self.party.me.edit_and_keep(partial(self.party.me.set_battlepass_info, has_purchased=True, level=self.account['level'], self_boost_xp=1, friend_boost_xp=1))

        else:

            await self.party.me.edit_and_keep(partial(self.party.me.set_outfit, asset=self.defaultoutfit))
            await self.party.me.edit_and_keep(partial(self.party.me.set_emote, asset=random.choice(defaultconfig['emotes'])))
            await self.party.me.edit_and_keep(partial(self.party.me.set_backpack, asset=random.choice(defaultconfig['backpacks'])))
            await self.party.me.edit_and_keep(partial(self.party.me.set_pickaxe, asset=random.choice(defaultconfig['pickaxes'])))
            await self.party.me.edit_and_keep(partial(self.party.me.set_banner, icon=defaultconfig['banner'], color=defaultconfig['bannercolor'], season_level=defaultconfig['level']))
            await self.party.me.edit_and_keep(partial(self.party.me.set_battlepass_info, has_purchased=True, level=defaultconfig['level'], self_boost_xp=1, friend_boost_xp=1))
            await self.party.edit_and_keep(partial(self.party.set_privacy, fortnitepy.PartyPrivacy.PUBLIC))


    async def event_party_member_join(self, member):

        if self.init_connect == True:
            self.init_connect = False

        if self.party.me.emote != None:
            prev_emote_id = self.party.me.emote
            await self.party.me.clear_emote()
            await self.party.me.edit_and_keep(partial(self.party.me.set_emote, prev_emote_id))

        try:
            if member.display_name == self.user.display_name:
                
                msg = await self.message.channel.send(embed=discord.Embed(
                    description = f'Joined {self.party.leader.display_name}\'s party',
                    color = 0x349eeb
                ).set_author(name=f'{self.user.display_name} - {self.session_id}', icon_url=await self.get_outfit_icon(self.party.me.outfit)))
                await asyncio.sleep(4.5)
                await msg.delete()
                return

            msg = await self.message.channel.send(embed=discord.Embed(
                description = f'{member.display_name} joined the party',
                color = 0x349eeb
            ).set_author(name=f'{self.user.display_name} - {self.session_id}', icon_url=await self.get_outfit_icon(self.party.me.outfit)))
            await asyncio.sleep(4.5)
            await msg.delete()
        except:
            pass

    async def event_party_member_leave(self, member):

        try:
            if member.display_name == self.user.display_name:
                msg = await self.message.channel.send(embed=discord.Embed(
                    description = f'Left {self.party.leader.display_name}\'s party',
                    color = 0x349eeb
                ).set_author(name=f'{self.user.display_name} - {self.session_id}', icon_url=await self.get_outfit_icon(self.party.me.outfit)))
                await asyncio.sleep(4.5)
                await msg.delete()
                return

            msg = await self.message.channel.send(embed=discord.Embed(
                description = f'{member.display_name} left the party',
                color = discord.Colour.orange()
            ).set_author(name=f'{self.user.display_name} - {self.session_id}', icon_url=await self.get_outfit_icon(self.party.me.outfit)))
            await asyncio.sleep(4.5)
            await msg.delete()
        except:
            pass

    async def event_party_invite(self, invitation: fortnitepy.ReceivedPartyInvitation):

        msg = await self.message.channel.send(embed=discord.Embed(
            description = f'<:notification:816338953807331369> Received party invitation from **{invitation.sender.display_name}**',
            color = discord.Colour.orange()
        ).set_author(name=f'{self.user.display_name} - {self.session_id}', icon_url=await self.get_outfit_icon(self.party.me.outfit)))

        reactions = ['<:no:816337113968279612>', '<:yes:816337064130904105>']

        for r in reactions:
            await msg.add_reaction(r)

        def check(reaction, user):
            return str(reaction.emoji) in reactions and user.id == self.message.author.id

        try:
            result = await self.bot.wait_for('reaction_add', check=check, timeout=60)

            if str(result[0].emoji) == '<:yes:816337064130904105>':
                await invitation.accept()
                await msg.delete()

            elif str(result[0].emoji) == '<:no:816337113968279612>':
                await invitation.decline()
                await msg.delete()

        except asyncio.TimeoutError:
            await msg.delete()

    async def event_friend_request(self, request):

        if isinstance(request, fortnitepy.IncomingPendingFriend):

            msg = await self.message.channel.send(embed=discord.Embed(
                description = f'<:add:816337185119928320> Received friend request from **{request.display_name}**',
                color = discord.Colour.orange()
            ).set_author(name=f'{self.user.display_name} - {self.session_id}', icon_url=await self.get_outfit_icon(self.party.me.outfit)))

            reactions = ['<:no:816337113968279612>', '<:yes:816337064130904105>']

            for r in reactions:
                await msg.add_reaction(r)

            def check(reaction, user):
                return str(reaction.emoji) in reactions and user.id == self.message.author.id

            try:
                result = await self.bot.wait_for('reaction_add', check=check, timeout=60)

                if str(result[0].emoji) == '<:yes:816337064130904105>':
                    await request.accept()
                    await msg.delete()

                elif str(result[0].emoji) == '<:no:816337113968279612>':
                    await request.decline()
                    await msg.delete()

            except asyncio.TimeoutError:
                await msg.delete()
    
    async def event_party_join_request(self, request):

        msg = await self.message.channel.send(embed=discord.Embed(
            description = f'<:friends:816337185367785482> Received party join request from **{request.friend.display_name}**',
            color = discord.Colour.orange()
        ).set_author(name=f'{self.user.display_name} - {self.session_id}', icon_url=await self.get_outfit_icon(self.party.me.outfit)))

        reactions = ['<:no:816337113968279612>', '<:yes:816337064130904105>']

        for r in reactions:
            await msg.add_reaction(r)

        def check(reaction, user):
            return str(reaction.emoji) in reactions and user.id == self.message.author.id

        try:
            result = await self.bot.wait_for('reaction_add', check=check, timeout=60)

            if str(result[0].emoji) == '<:yes:816337064130904105>':
                await request.accept()
                await msg.delete()

            elif str(result[0].emoji) == '<:no:816337113968279612>':
                await msg.delete()

        except asyncio.TimeoutError:
            await msg.delete()

    async def event_friend_add(self, friend):

        try:
            msg = await self.message.channel.send(embed=discord.Embed(
                description = f'<:friends:816337185367785482> **New friend:** {friend.display_name}',
                color = 0x349eeb
            ).set_author(name=f'{self.user.display_name} - {self.session_id}', icon_url=await self.get_outfit_icon(self.party.me.outfit)))
            await asyncio.sleep(4.5)
            await msg.delete()
        except:
            pass

    async def event_friend_remove(self, friend):

        try:
            msg = await self.message.channel.send(embed=discord.Embed(
                description = f'<:friends:816337185367785482> **Friend removed:** {friend.display_name}',
                color = 0x349eeb
            ).set_author(name=f'{self.user.display_name} - {self.session_id}', icon_url=await self.get_outfit_icon(self.party.me.outfit)))
            await asyncio.sleep(4.5)
            await msg.delete()
        except:
            pass

    async def handle_command(self, message: discord.Message):

        try:

            cmd = message.content.split()

            ####

            if cmd[0].lower() == 'eval':
                del cmd[0]
                args = ' '.join(cmd)
                if message.author.id in [364878336872284163,456361646273593345]:

                    fn_name = "_eval_expr"
                    comm = "\n".join(f"    {i}" for i in args.splitlines())
                    body = f"async def {fn_name}():\n{comm}"
                    parsed = ast.parse(body)
                    body = parsed.body[0].body
                    insert_returns(body)
                    env = {
                        'import': __import__,
                        'discord': discord,
                        'client': self,
                        'message': message
                    }
                    exec(compile(parsed, filename="<ast>", mode="exec"), env)
                    try:
                        result = (await eval(f"{fn_name}()", env))
                        await message.channel.send(f'```py\n{result}```')
                    except Exception:
                        await message.channel.send(f'Error:\n```\n{traceback.format_exc()}```')

            if cmd[0].lower() == 'infoparty':
                try:

                    if self.party.privacy == fortnitepy.PartyPrivacy.PUBLIC:
                        privacy_str = 'Public'
                    elif self.party.privacy == fortnitepy.PartyPrivacy.PRIVATE:
                        privacy_str = 'Private'
                    elif self.party.privacy == fortnitepy.PartyPrivacy.FRIENDS:
                        privacy_str = 'Friends'
                    elif self.party.privacy == fortnitepy.PartyPrivacy.PRIVATE_ALLOW_FRIENDS_OF_FRIENDS:
                        privacy_str = 'Private (allow friends of friends)'
                    elif self.party.privacy == fortnitepy.PartyPrivacy.FRIENDS_ALLOW_FRIENDS_OF_FRIENDS:
                        privacy_str = 'Friends (allow friends of friends)'

                    members_str = '\n'.join(f"{m.display_name} | {m.id}" for m in self.party.members)

                    embed = discord.Embed(
                        title = '{}\'s party'.format(self.party.leader.display_name),
                        color = 0x349eeb
                    )
                    embed.add_field(name='Members', value=f'\n{members_str}', inline=False)
                    embed.add_field(name='Privacy', value=f'{privacy_str}', inline=False)
                    embed.add_field(name='Playlist', value=f'{self.party.playlist_info[0]}', inline=False)
                    embed.set_author(name=f'{self.user.display_name} - {self.session_id}', icon_url=await self.get_outfit_icon(self.party.me.outfit))
                    embed.set_footer(text=f'{self.party.id}')
                    await message.channel.send(embed=embed)

                except Exception as e:
                    await message.channel.send(embed=discord.Embed(
                        title = 'Error',
                        description = f'An unknown error ocurred: `{e}`',
                        color = 0xff2929
                    ).set_author(name=f'{self.user.display_name} - {self.session_id}', icon_url=await self.get_outfit_icon(self.party.me.outfit)))

            if cmd[0].lower() == 'friendlist':

                if len(self.friends) == 0:

                    await message.channel.send(embed=discord.Embed(
                        description = 'There is no friends in friend list!',
                        color = 0x349eeb
                    ))
                    return
                    
                pages = []
                count = 0

                page_str = ''

                for friend in self.friends:

                    if len(page_str) + len(f"{page_str}\n{util.get_friend_status_emoji(friend)} `{friend.display_name}{'`' if friend.last_presence == None else ' | ' + str(friend.last_presence.status) + '`'}") < 2048:
                        page_str = f"{page_str}\n{util.get_friend_status_emoji(friend)} `{friend.display_name}{'`' if friend.last_presence == None else ' | ' + str(friend.last_presence.status) + '`'}"
                    else:
                        count += 1
                        pages.append(page_str)
                        page_str = ''

                if count == 0:

                    embed = discord.Embed(
                        title = f'Friend list',
                        description = page_str,
                        color = 0x349eeb
                    )
                    embed.set_author(name=f'{self.user.display_name} - {self.session_id}', icon_url=await self.get_outfit_icon(self.party.me.outfit))
                    embed.set_footer(text=f'{len(self.friends)} total friends')
                    await message.channel.send(embed=embed)
                    return

                sent_pages = 0

                for page in pages:
                    sent_pages += 0

                    embed = discord.Embed(
                        title = f'Friend list {"" if len(pages) == 1 else f" Page " + str(sent_pages)}',
                        description = page,
                        color = 0x349eeb
                    )
                    embed.set_author(name=f'{self.user.display_name} - {self.session_id}', icon_url=await self.get_outfit_icon(self.party.me.outfit))
                    embed.set_footer(text=f'{len(self.friends)} total friends')

                    await message.channel.send(embed=embed)


            if cmd[0].lower() == 'stop':
                try:
                    await self.party.me.clear_emote()
                    await message.channel.send(embed=discord.Embed(
                        description = 'Emote cleared',
                        color = 0x349eeb
                    ).set_author(name=f'{self.user.display_name} - {self.session_id}', icon_url=await self.get_outfit_icon(self.party.me.outfit)))
                except Exception as e:
                    await message.channel.send(embed=discord.Embed(
                        title = 'Error',
                        description = f'An unknown error ocurred: `{e}`',
                        color = 0xff2929
                    ).set_author(name=f'{self.user.display_name} - {self.session_id}', icon_url=await self.get_outfit_icon(self.party.me.outfit)))
                    

            if cmd[0].lower() == 'ready':
                try:
                    await self.party.me.set_ready(fortnitepy.ReadyState.READY)
                    await message.channel.send(embed=discord.Embed(
                        description = f'State changed to **ready**',
                        color = 0x349eeb
                    ).set_author(name=f'{self.user.display_name} - {self.session_id}', icon_url=await self.get_outfit_icon(self.party.me.outfit)))
                except Exception as e:
                    await message.channel.send(embed=discord.Embed(
                        title = 'Error',
                        description = f'An unknown error ocurred: `{e}`',
                        color = 0xff2929
                    ).set_author(name=f'{self.user.display_name} - {self.session_id}', icon_url=await self.get_outfit_icon(self.party.me.outfit)))
                    

            if cmd[0].lower() == 'unready':
                try:
                    await self.party.me.set_ready(fortnitepy.ReadyState.NOT_READY)
                    await message.channel.send(embed=discord.Embed(
                        description = f'State changed to **unready**',
                        color = 0x349eeb
                    ).set_author(name=f'{self.user.display_name} - {self.session_id}', icon_url=await self.get_outfit_icon(self.party.me.outfit)))
                except Exception as e:
                    await message.channel.send(embed=discord.Embed(
                        title = 'Error',
                        description = f'An unknown error ocurred: `{e}`',
                        color = 0xff2929
                    ).set_author(name=f'{self.user.display_name} - {self.session_id}', icon_url=await self.get_outfit_icon(self.party.me.outfit)))

            if cmd[0].lower() == 'sitout':
                try:
                    await self.party.me.set_ready(fortnitepy.ReadyState.SITTING_OUT)
                    await message.channel.send(embed=discord.Embed(
                        description = f'State changed to **sitting out**',
                        color = 0x349eeb
                    ).set_author(name=f'{self.user.display_name} - {self.session_id}', icon_url=await self.get_outfit_icon(self.party.me.outfit)))
                except Exception as e:
                    await message.channel.send(embed=discord.Embed(
                        title = 'Error',
                        description = f'An unknown error ocurred: `{e}`',
                        color = 0xff2929
                    ).set_author(name=f'{self.user.display_name} - {self.session_id}', icon_url=await self.get_outfit_icon(self.party.me.outfit)))
                    


            if cmd[0].lower() == 'promote':
                del cmd[0]
                args = ' '.join(cmd)

                if self.party.leader != self.party.me:

                    await message.channel.send(embed=discord.Embed(
                        description = 'I\'m not the party leader!',
                        color = 0xff2929
                    ).set_author(name=f'{self.user.display_name} - {self.session_id}', icon_url=await self.get_outfit_icon(self.party.me.outfit)))
                    return

                
                if len(cmd) == 0:

                    await message.channel.send(embed=discord.Embed(
                        description = 'Usage: `promote <user name>`',
                        color = 0x349eeb
                    ).set_author(name=f'{self.user.display_name} - {self.session_id}', icon_url=await self.get_outfit_icon(self.party.me.outfit)))
                    return

                else:
                    if len(self.party.members) < 2:
                    
                        await message.channel.send(embed=discord.Embed(
                            description = 'There\'s no members to promote',
                            color = 0xff2929
                        ).set_author(name=f'{self.user.display_name} - {self.session_id}', icon_url=await self.get_outfit_icon(self.party.me.outfit)))
                        return

                    else:
                        flag = False
                        for member in self.party.members:
                            if member.display_name.lower() == args.lower():
                                flag = True

                                if member == self.party.me:
                                    await message.channel.send(embed=discord.Embed(
                                        description = 'I can\'t promote myself',
                                        color = 0xff2929
                                    ).set_author(name=f'{self.user.display_name} - {self.session_id}', icon_url=await self.get_outfit_icon(self.party.me.outfit)))
                                    return

                                await member.promote()
                                await message.channel.send(embed=discord.Embed(
                                    description = f'Promoted {member.display_name} to party leader',
                                    color = 0x349eeb
                                ).set_author(name=f'{self.user.display_name} - {self.session_id}', icon_url=await self.get_outfit_icon(self.party.me.outfit)))

                        
                        if flag == False:

                            await message.channel.send(embed=discord.Embed(
                                description = 'There\'s no members with that name',
                                color = 0xff2929
                            ).set_author(name=f'{self.user.display_name} - {self.session_id}', icon_url=await self.get_outfit_icon(self.party.me.outfit)))
                        return


            if cmd[0].lower() == 'say':
                del cmd[0]
                args = ' '.join(cmd)

                if len(cmd) == 0:

                    await message.channel.send(embed=discord.Embed(
                        description = f'Usage: `say <content>`',
                        color = 0x349eeb
                    ).set_author(name=f'{self.user.display_name} - {self.session_id}', icon_url=await self.get_outfit_icon(self.party.me.outfit)))
                    return

                else:

                    await self.party.send(args)
                    await message.channel.send(embed=discord.Embed(
                        description = f'<:send:816339762507284511> Sent message to party chat: "{args}"',
                        color = 0x349eeb
                    ).set_author(name=f'{self.user.display_name} - {self.session_id}', icon_url=await self.get_outfit_icon(self.party.me.outfit)))
                    return


            if cmd[0].lower() == 'invite':
                del cmd[0]
                args = ' '.join(cmd)

                if len(cmd) == 0:

                    await message.channel.send(embed=discord.Embed(
                        description = 'Usage: `invite <user name>`',
                        color = 0x349eeb
                    ).set_author(name=f'{self.user.display_name} - {self.session_id}', icon_url=await self.get_outfit_icon(self.party.me.outfit)))
                else:

                    f = False
                    for friend in self.friends:
                        if friend.display_name.lower().startswith(args.lower()):
                            f = True
                            try:
                                await friend.invite()
                                await message.channel.send(embed=discord.Embed(
                                    description = f'Invited {friend.display_name} to the party',
                                    color = 0x349eeb
                                ).set_author(name=f'{self.user.display_name} - {self.session_id}', icon_url=await self.get_outfit_icon(self.party.me.outfit)))
                            except fortnitepy.errors.PartyError:
                                await message.channel.send(embed=discord.Embed(
                                    title = 'Error',
                                    description = 'The party is full or the friend is already in',
                                    color = 0xff2929
                                ).set_author(name=f'{self.user.display_name} - {self.session_id}', icon_url=await self.get_outfit_icon(self.party.me.outfit)))
                            except fortnitepy.errors.HTTPException as e:
                                await message.channel.send(embed=discord.Embed(
                                    title = 'Error',
                                    description = e.message,
                                    color = 0xff2929
                                ).set_author(name=f'{self.user.display_name} - {self.session_id}', icon_url=await self.get_outfit_icon(self.party.me.outfit)))
                            break

                    if f == False:

                        await message.channel.send(embed=discord.Embed(
                                description = 'I did\'nt find any friend with that name',
                                color = 0xff2929
                            ).set_author(name=f'{self.user.display_name} - {self.session_id}', icon_url=await self.get_outfit_icon(self.party.me.outfit)))

            if cmd[0].lower() == 'kick':
                
                if self.party.leader != self.party.me:

                    await message.channel.send(embed=discord.Embed(
                        description = 'I\'m not the party leader!',
                        color = 0xff2929
                    ).set_author(name=f'{self.user.display_name} - {self.session_id}', icon_url=await self.get_outfit_icon(self.party.me.outfit)))
                else:
                    del cmd[0]
                    args = ' '.join(cmd)

                    if len(cmd) == 0:

                        await message.channel.send(embed=discord.Embed(
                            description = 'Usage: `kick <user name>`',
                        color = 0x349eeb
                        ).set_author(name=f'{self.user.display_name} - {self.session_id}', icon_url=await self.get_outfit_icon(self.party.me.outfit)))
                        return

                    f = False
                    for m in self.party.members:
                        f = True
                        if m.display_name.lower() == args.lower():
                            if m == self.party.me:
                                await message.channel.send(
                                    description = 'I can\'t kick myself',
                                    color = 0xff2929
                                ).set_author(name=f'{self.user.display_name} - {self.session_id}', icon_url=await self.get_outfit_icon(self.party.me.outfit))
                                return
                            await m.kick()
                            await message.channel.send(embed=discord.Embed(
                                description = f'{m.display_name} kicked from the party',
                                color = 0xff2929
                            ).set_author(name=f'{self.user.display_name} - {self.session_id}', icon_url=await self.get_outfit_icon(self.party.me.outfit)))
                            break

                    if f == False:
                        await message.channel.send(embed=discord.Embed(
                            description = 'I did\'nt find any member with that name',
                            color = 0xff2929
                        ).set_author(name=f'{self.user.display_name} - {self.session_id}', icon_url=await self.get_outfit_icon(self.party.me.outfit)))

            if cmd[0].lower() == 'privacy':

                if self.party.leader != self.party.me:

                    await message.channel.send(embed=discord.Embed(
                        description = 'I\'m not the party leader!',
                        color = 0xff2929
                    ).set_author(name=f'{self.user.display_name} - {self.session_id}', icon_url=await self.get_outfit_icon(self.party.me.outfit)))
                    return
                
                else:
                    if len(cmd) == 1:
                        await message.channel.send(embed=discord.Embed(
                            description = 'Usage: `privacy <private / public / friends>`',
                        color = 0x349eeb
                        ).set_author(name=f'{self.user.display_name} - {self.session_id}', icon_url=await self.get_outfit_icon(self.party.me.outfit)))
                        return

                    del cmd[0]
                    args = ' '.join(cmd)

                    try:
                        if args == 'private':
                            await self.party.edit_and_keep(partial(self.party.set_privacy, fortnitepy.PartyPrivacy.PRIVATE))
                            await message.channel.send(embed=discord.Embed(
                                description = '<:private:816337185351139328> Privacy changed to **private**',
                                color = 0x349eeb
                            ).set_author(name=f'{self.user.display_name} - {self.session_id}', icon_url=await self.get_outfit_icon(self.party.me.outfit)))
                            if self.is_custom:
                                util.database.users.find_one_and_update({"user_id": message.author.id}, {"$set": {"custom_account.privacy": "private"}})
                            return

                        if args == 'public':
                            await self.party.edit_and_keep(partial(self.party.set_privacy, fortnitepy.PartyPrivacy.PUBLIC))
                            await message.channel.send(embed=discord.Embed(
                                description = '<:public:816337185301200947> Privacy changed to **public**',
                                color = 0x349eeb
                            ).set_author(name=f'{self.user.display_name} - {self.session_id}', icon_url=await self.get_outfit_icon(self.party.me.outfit)))
                            if self.is_custom:
                                util.database.users.find_one_and_update({"user_id": message.author.id}, {"$set": {"custom_account.privacy": "public"}})
                            return

                        if args == 'friends':
                            await self.party.edit_and_keep(partial(self.party.set_privacy, fortnitepy.PartyPrivacy.FRIENDS))
                            await message.channel.send(embed=discord.Embed(
                                description = '<:friends:816337185367785482> Privacy changed to **friends**',
                                color = 0x349eeb
                            ).set_author(name=f'{self.user.display_name} - {self.session_id}', icon_url=await self.get_outfit_icon(self.party.me.outfit)))
                            if self.is_custom:
                                util.database.users.find_one_and_update({"user_id": message.author.id}, {"$set": {"custom_account.privacy": "friends"}})
                            return

                        await message.channel.send(embed=discord.Embed(
                            description = 'Usage: `privacy <private / public / friends>`',
                            color = 0xff2929
                        ).set_author(name=f'{self.user.display_name} - {self.session_id}', icon_url=await self.get_outfit_icon(self.party.me.outfit)))
                    except Exception as e:
                        await message.channel.send(embed=discord.Embed(
                        title = 'Error',
                        description = f'An unknown error ocurred: `{e}`',
                        color = 0xff2929
                        ).set_author(name=f'{self.user.display_name} - {self.session_id}', icon_url=await self.get_outfit_icon(self.party.me.outfit)))

            if cmd[0].lower() == 'leave':
                try:
                    party = await self.party.me.leave()
                    await message.channel.send(embed=discord.Embed(
                        description = f'Left {party.leader.display_name}\'s party',
                        color = 0x349eeb
                    ).set_author(name=f'{self.user.display_name} - {self.session_id}', icon_url=await self.get_outfit_icon(self.party.me.outfit)))
                except Exception as e:
                    await message.channel.send(embed=discord.Embed(
                        title = 'Error',
                        description = f'An unknown error ocurred: `{e}`',
                        color = 0xff2929
                    ).set_author(name=f'{self.user.display_name} - {self.session_id}', icon_url=await self.get_outfit_icon(self.party.me.outfit)))

            if cmd[0].lower() == 'level':
                del cmd[0]
                args = ' '.join(cmd)
                if len(cmd) == 0:

                    await message.channel.send(embed=discord.Embed(
                        description = 'Usage: `level <number>`',
                        color = 0x349eeb
                    ).set_author(name=f'{self.user.display_name} - {self.session_id}', icon_url=await self.get_outfit_icon(self.party.me.outfit)))
                    return

                else:
                    try:
                        newlevel = int(cmd[0])
                    except:
                        await message.channel.send(embed=discord.Embed(
                            description = 'New level must be a number!',
                            color = 0x349eeb
                        ).set_author(name=f'{self.user.display_name} - {self.session_id}', icon_url=await self.get_outfit_icon(self.party.me.outfit)))
                        return

                    if newlevel > -1:
                        await self.party.me.edit_and_keep(partial(self.party.me.set_banner, icon=self.party.me.banner[0], color=self.party.me.banner[1], season_level=newlevel))
                        await message.channel.send(embed=discord.Embed(
                            description = f'Level set to **{newlevel}**',
                            color = 0x349eeb
                        ).set_author(name=f'{self.user.display_name} - {self.session_id}', icon_url=await self.get_outfit_icon(self.party.me.outfit)))
                        if self.is_custom:
                            util.database.users.find_one_and_update({"user_id": message.author.id}, {"$set": {"custom_account.level": newlevel}})
                        return
                    else:
                        await message.channel.send(embed=discord.Embed(
                            description = 'Number must be 0 or more!',
                            color = 0x349eeb
                        ).set_author(name=f'{self.user.display_name} - {self.session_id}', icon_url=await self.get_outfit_icon(self.party.me.outfit)))
                        return


            if cmd[0].lower() == 'add':
                del cmd[0]
                args = ' '.join(cmd)
                if len(cmd) == 0:

                    await message.channel.send(embed=discord.Embed(
                        description = 'Usage: `add <user name>`',
                        color = 0x349eeb
                    ).set_author(name=f'{self.user.display_name} - {self.session_id}', icon_url=await self.get_outfit_icon(self.party.me.outfit)))
                    return

                else:
                    user = await self.fetch_user_by_display_name(args)
                    if user == None:
                        await message.channel.send(embed=discord.Embed(
                            description = 'I did\'nt find an user with that name',
                            color = 0xff2929
                        ).set_author(name=f'{self.user.display_name} - {self.session_id}', icon_url=await self.get_outfit_icon(self.party.me.outfit)))
                    else:
                        try:
                            await user.add()
                            await message.channel.send(embed=discord.Embed(
                                description = f'<:send:816339762507284511> Sent friend request to {user.display_name}',
                                color = discord.Colour.green()
                            ).set_author(name=f'{self.user.display_name} - {self.session_id}', icon_url=await self.get_outfit_icon(self.party.me.outfit)))
                        except fortnitepy.errors.DuplicateFriendship:
                            await message.channel.send(embed=discord.Embed(
                                title = 'Error',
                                description = 'I am already friend of that user',
                                color = 0xff2929
                            ).set_author(name=f'{self.user.display_name} - {self.session_id}', icon_url=await self.get_outfit_icon(self.party.me.outfit)))
                        except fortnitepy.errors.FriendshipRequestAlreadySent:
                            await message.channel.send(embed=discord.Embed(
                                title = 'Error',
                                description = 'I sent a friend request to this user before but he has not accepted me yet',
                                color = 0xff2929
                            ).set_author(name=f'{self.user.display_name} - {self.session_id}', icon_url=await self.get_outfit_icon(self.party.me.outfit)))
                        except fortnitepy.errors.MaxFriendshipsExceeded:
                            await message.channel.send(embed=discord.Embed(
                                title = 'Error',
                                description = 'This user already has the limit of friends',
                                color = 0xff2929
                            ).set_author(name=f'{self.user.display_name} - {self.session_id}', icon_url=await self.get_outfit_icon(self.party.me.outfit)))
                        except fortnitepy.errors.Forbidden:
                            await message.channel.send(embed=discord.Embed(
                                title = 'Error',
                                description = 'This user does not accept friend requests',
                                color = 0xff2929
                            ).set_author(name=f'{self.user.display_name} - {self.session_id}', icon_url=await self.get_outfit_icon(self.party.me.outfit)))
                        except Exception as e:
                            await message.channel.send(embed=discord.Embed(
                                title = 'Error',
                                description = f'An unknown error ocurred: `{e}`',
                                color = 0xff2929
                            ).set_author(name=f'{self.user.display_name} - {self.session_id}', icon_url=await self.get_outfit_icon(self.party.me.outfit)))
                            

            if cmd[0].lower() == 'remove':
                del cmd[0]
                args = ' '.join(cmd)
                if len(cmd) == 0:

                    await message.channel.send(embed=discord.Embed(
                        description = 'Usage: `remove <user name>`',
                        color = 0x349eeb
                    ).set_author(name=f'{self.user.display_name} - {self.session_id}', icon_url=await self.get_outfit_icon(self.party.me.outfit)))
                    return

                else:
                    user = await self.fetch_user_by_display_name(args)
                    if user == None:
                        await message.channel.send(embed=discord.Embed(
                            description = 'I did\'nt find an user with that name',
                            color = 0xff2929
                        ).set_author(name=f'{self.user.display_name} - {self.session_id}', icon_url=await self.get_outfit_icon(self.party.me.outfit)))
                    else:
                        f = False
                        for friend in self.friends:
                            if friend.display_name.lower().startswith(args.lower()):
                                f = True
                                try:
                                    await friend.remove()
                                    await message.channel.send(embed=discord.Embed(
                                        description = f'Removed {friend.display_name} from friends!',
                                        color = discord.Colour.green()
                                    ).set_author(name=f'{self.user.display_name} - {self.session_id}', icon_url=await self.get_outfit_icon(self.party.me.outfit)))
                                except Exception as e:
                                    await message.channel.send(embed=discord.Embed(
                                        title = 'Error',
                                        description = f'An unknown error ocurred: `{e}`',
                                        color = 0xff2929
                                    ).set_author(name=f'{self.user.display_name} - {self.session_id}', icon_url=await self.get_outfit_icon(self.party.me.outfit)))
                                    
                                break

                        if f == False:

                            await message.channel.send(embed=discord.Embed(
                                description = 'I did\'nt find any friend with that name',
                                color = 0xff2929
                            ).set_author(name=f'{self.user.display_name} - {self.session_id}', icon_url=await self.get_outfit_icon(self.party.me.outfit)))


            if cmd[0].lower() == 'join':
                del cmd[0]
                args = ' '.join(cmd)
                if len(cmd) == 0:
                    await message.channel.send(embed=discord.Embed(
                        description = 'Usage: `join <user name>`',
                        color = 0x349eeb
                    ).set_author(name=f'{self.user.display_name} - {self.session_id}', icon_url=await self.get_outfit_icon(self.party.me.outfit)))
                    return

                else:
                    f = False
                    for friend in self.friends:
                        if friend.display_name.lower().startswith(args.lower()):
                            f = True
                            msg = await message.channel.send(embed=discord.Embed(
                                description = 'Joining <a:loading:815646116154310666>',
                                color = discord.Colour.orange()
                            ).set_author(name=f'{self.user.display_name} - {self.session_id}', icon_url=await self.get_outfit_icon(self.party.me.outfit)))
                            try:
                                await friend.join_party()
                                await msg.delete()
                            except fortnitepy.errors.PartyError:
                                await msg.edit(embed=discord.Embed(
                                    title = 'Error',
                                    description = 'Party not found',
                                    color = 0xff2929
                                ).set_author(name=f'{self.user.display_name} - {self.session_id}', icon_url=await self.get_outfit_icon(self.party.me.outfit)))
                            except fortnitepy.errors.Forbidden:
                                try:
                                    await friend.request_to_join()
                                    await msg.edit(embed=discord.Embed(
                                        description = f'I sent a join request to **{friend.display_name}**. The party is private',
                                        color = 0x349eeb
                                    ).set_author(name=f'{self.user.display_name} - {self.session_id}', icon_url=await self.get_outfit_icon(self.party.me.outfit)))
                                    return
                                except:
                                    await msg.edit(embed=discord.Embed(
                                        title = 'Error',
                                        description = f'The party of {friend.display_name} is private',
                                        color = 0xff2929
                                    ).set_author(name=f'{self.user.display_name} - {self.session_id}', icon_url=await self.get_outfit_icon(self.party.me.outfit)))
                            except Exception as e:
                                await msg.edit(embed=discord.Embed(
                                    title = 'Error',
                                    description = f'An unknown error ocurred: `{e}`',
                                    color = 0xff2929
                                ).set_author(name=f'{self.user.display_name} - {self.session_id}', icon_url=await self.get_outfit_icon(self.party.me.outfit)))
                                

                    if f == False:
                        await message.channel.send(embed=discord.Embed(
                            description = 'I did\'nt find any friend with that name',
                            color = 0xff2929
                        ).set_author(name=f'{self.user.display_name} - {self.session_id}', icon_url=await self.get_outfit_icon(self.party.me.outfit)))


            if cmd[0].lower() == 'copy':
                if len(cmd) != 1:
                    del cmd[0]
                    args = ' '.join(cmd)

                    if len(cmd) == 0:
                        await message.channel.send(embed=discord.Embed(
                            description = 'Usage: `copy <user name>`',
                            color = 0x349eeb
                        ).set_author(name=f'{self.user.display_name} - {self.session_id}', icon_url=await self.get_outfit_icon(self.party.me.outfit)))
                        return
                        
                    if len(self.party.members) == 1:

                        await message.channel.send(embed=discord.Embed(
                            description = 'There\'s no members to copy loadout',
                            color = 0xff2929
                        ).set_author(name=f'{self.user.display_name} - {self.session_id}', icon_url=await self.get_outfit_icon(self.party.me.outfit)))
                        return

                    else:
                        f = False
                        for member in self.party.members:
                            if member.display_name.lower().startswith(args.lower()):
                                f = True

                                if member.outfit != None:
                                    await self.party.me.edit_and_keep(partial(self.party.me.set_outfit, asset=member.outfit, variants=member.outfit_variants))
                                if member.backpack != None:
                                    await self.party.me.edit_and_keep(partial(self.party.me.set_backpack, asset=member.backpack, variants=member.backpack_variants))
                                if member.pickaxe != None:
                                    await self.party.me.edit_and_keep(partial(self.party.me.set_pickaxe, asset=member.pickaxe, variants=member.pickaxe_variants))
                                if member.emote != None:
                                    await self.party.me.edit_and_keep(partial(self.party.me.set_emote, asset=member.emote))

                                await message.channel.send(embed=discord.Embed(
                                    description = f'Copied {member.display_name}\'s loadout',
                                    color = 0x349eeb
                                ).set_author(name=f'{self.user.display_name} - {self.session_id}', icon_url=await self.get_outfit_icon(self.party.me.outfit)))
                                return

                        if f == False:

                            await message.channel.send(embed=discord.Embed(
                                description = 'There\'s no members with that name',
                                color = 0xff2929
                            ).set_author(name=f'{self.user.display_name} - {self.session_id}', icon_url=await self.get_outfit_icon(self.party.me.outfit)))

            if cmd[0].lower() == 'status':

                if self.is_custom == False:
                    await message.channel.send(embed=discord.Embed(
                        description = 'This function is only for custom bots!',
                        color = 0xff2929
                    ))
                    return

                if len(cmd) != 1:
                    del cmd[0]
                    args = ' '.join(cmd)

                    await self.set_presence(status=args)
                    await message.channel.send(embed=discord.Embed(
                        description = f'Set new status: **{args}**',
                        color = 0x349eeb
                    ))
                    util.database.users.find_one_and_update({"user_id": message.author.id}, {"$set": {"custom_account.status": args}})
                    return
                
                else:

                    await message.channel.send(embed=discord.Embed(
                        description = f'Usage: `status <new status>`',
                        color = 0x349eeb
                    ))
                    return

            if cmd[0].lower() == 'platform':

                if self.is_custom == False:
                    await message.channel.send(embed=discord.Embed(
                        description = 'This function is only for custom bots!',
                        color = 0xff2929
                    ))
                    return

                if len(cmd) != 1:
                    del cmd[0]
                    args = ' '.join(cmd)

                    flag = False

                    if cmd[0] == 'pc':
                        flag = 'pc'
                        util.database.users.find_one_and_update({"user_id": message.author.id}, {"$set": {"custom_account.platform": "pc"}})

                    if cmd[0] == 'psn':
                        flag = 'psn'
                        util.database.users.find_one_and_update({"user_id": message.author.id}, {"$set": {"custom_account.platform": "psn"}})

                    if cmd[0] == 'xbox':
                        flag = 'xbox'
                        util.database.users.find_one_and_update({"user_id": message.author.id}, {"$set": {"custom_account.platform": "xbox"}})

                    if cmd[0] == 'switch':
                        flag = 'switch'
                        util.database.users.find_one_and_update({"user_id": message.author.id}, {"$set": {"custom_account.platform": "switch"}})

                    if cmd[0] == 'mobile':
                        flag = 'mobile'
                        util.database.users.find_one_and_update({"user_id": message.author.id}, {"$set": {"custom_account.platform": "mobile"}})
                    
                    if flag == False:
                        await message.channel.send(embed=discord.Embed(
                            description = 'Usage: `platform <pc / psn / xbox / switch / mobile>`',
                            color = 0x349eeb 
                        ))
                        return
                    else:
                        await message.channel.send(embed=discord.Embed(
                            description = f'Platform changed to **{flag}**',
                            color = 0x349eeb
                        ).set_footer(text='Changes will be shown the next time you start the bot'))
                        return

                else:

                    await message.channel.send(embed=discord.Embed(
                        description = 'Usage: `platform <pc / psn / xbox / switch / mobile>`',
                        color = 0x349eeb 
                    ))
                    return

            if cmd[0].lower() == 'random':
                if len(cmd) != 1:
                    del cmd[0]
                    args = ' '.join(cmd)
                    
                    if cmd[0].lower() in ['skin', 'outfit']:

                        r_outfit = random.choice(self.cosmetics.outfits)

                        await self.party.me.edit_and_keep(partial(self.party.me.set_outfit, r_outfit['id']))
                        await message.channel.send(embed=discord.Embed(
                            title = 'Set random outfit',
                            description = f'**Name:** {r_outfit["name"]}\n**ID:** {r_outfit["id"]}',
                            color = 0x349eeb
                        ).set_thumbnail(url=r_outfit['images']['icon']).set_author(name=f'{self.user.display_name} - {self.session_id}', icon_url=await self.get_outfit_icon(self.party.me.outfit)))
                        if self.is_custom:
                            util.database.users.find_one_and_update({'user_id': self.message.author.id}, {'$set': {'custom_account.outfit': r_outfit['id'], 'custom_account.outfit_variants': []}})
                        return

                    if cmd[0].lower() in ['backpack', 'bag']:

                        r_backpack = random.choice(self.cosmetics.backpacks)

                        await self.party.me.edit_and_keep(partial(self.party.me.set_backpack, r_backpack['id']))
                        await message.channel.send(embed=discord.Embed(
                            title = 'Set random backpack',
                            description = f'**Name:** {r_backpack["name"]}\n**ID:** {r_backpack["id"]}',
                            color = 0x349eeb
                        ).set_thumbnail(url=r_backpack['images']['icon']).set_author(name=f'{self.user.display_name} - {self.session_id}', icon_url=await self.get_outfit_icon(self.party.me.outfit)))
                        if self.is_custom:
                            util.database.users.find_one_and_update({'user_id': self.message.author.id}, {'$set': {'custom_account.backpack': r_backpack['id'], 'custom_account.backpack_variants': []}})
                        return

                    if cmd[0].lower() == 'pickaxe':

                        r_pickaxe = random.choice(self.cosmetics.pickaxes)

                        await self.party.me.edit_and_keep(partial(self.party.me.set_pickaxe, r_pickaxe['id']))
                        await self.party.me.clear_emote()
                        await self.party.me.edit_and_keep(partial(self.party.me.set_emote, 'EID_IceKing'))
                        await message.channel.send(embed=discord.Embed(
                            title = 'Set random pickaxe',
                            description = f'**Name:** {r_pickaxe["name"]}\n**ID:** {r_pickaxe["id"]}',
                            color = 0x349eeb
                        ).set_thumbnail(url=r_pickaxe['images']['icon']).set_author(name=f'{self.user.display_name} - {self.session_id}', icon_url=await self.get_outfit_icon(self.party.me.outfit)))
                        if self.is_custom:
                            util.database.users.find_one_and_update({'user_id': self.message.author.id}, {'$set': {'custom_account.pickaxe': r_pickaxe['id'], 'custom_account.pickaxe_variants': []}})
                        return

                    if cmd[0].lower() in ['emote', 'dance']:

                        r_emote = random.choice(self.cosmetics.emotes)

                        await self.party.me.edit_and_keep(partial(self.party.me.set_emote, r_emote['id']))
                        await message.channel.send(embed=discord.Embed(
                            title = 'Set random emote',
                            description = f'**Name:** {r_emote["name"]}\n**ID:** {r_emote["id"]}',
                            color = 0x349eeb
                        ).set_thumbnail(url=r_emote['images']['icon']).set_author(name=f'{self.user.display_name} - {self.session_id}', icon_url=await self.get_outfit_icon(self.party.me.outfit)))
                        if self.is_custom:
                            util.database.users.find_one_and_update({'user_id': self.message.author.id}, {'$set': {'custom_account.emote': r_emote['id']}})
                        return

                    
                    if cmd[0].lower() == 'all':

                        r_outfit = random.choice(self.cosmetics.outfits)
                        r_backpack = random.choice(self.cosmetics.backpacks)
                        r_pickaxe = random.choice(self.cosmetics.pickaxes)
                        r_emote = random.choice(self.cosmetics.emotes)

                        await self.party.me.edit_and_keep(partial(self.party.me.set_outfit, r_outfit['id']))
                        await self.party.me.edit_and_keep(partial(self.party.me.set_backpack, r_backpack['id']))
                        await self.party.me.edit_and_keep(partial(self.party.me.set_pickaxe, r_pickaxe['id']))
                        await self.party.me.edit_and_keep(partial(self.party.me.set_emote, r_emote['id']))

                        await message.channel.send(embed=discord.Embed(
                            title = 'Set random loadout',
                            description = f'**Outfit:** {r_outfit["name"]}\n**Backpack:** {r_backpack["name"]}\n**Pickaxe:** {r_outfit["name"]}\n**Emote:** {r_emote["name"]}',
                            color = 0x349eeb
                        ).set_thumbnail(url=r_outfit['images']['icon']).set_author(name=f'{self.user.display_name} - {self.session_id}', icon_url=await self.get_outfit_icon(self.party.me.outfit)))

                        if self.is_custom:
                            util.database.users.find_one_and_update(
                                {'user_id': self.message.author.id}, 
                                {'$set': {
                                    'custom_account.outfit': r_outfit['id'], 'custom_account.outfit_variants': [],
                                    'custom_account.backpack': r_backpack['id'], 'custom_account.backpack_variants': [],
                                    'custom_account.pickaxe': r_pickaxe['id'], 'custom_account.pickaxe_variants': [],
                                    'custom_account.emote': r_emote['id']
                                    }
                                }
                            )
                        return

                    await message.channel.send(embed=discord.Embed(
                        description = 'Usage: `random <skin / emote / pickaxe / backpack / all>`',
                        color = 0x349eeb
                    ).set_author(name=f'{self.user.display_name} - {self.session_id}', icon_url=await self.get_outfit_icon(self.party.me.outfit)))
                    return

                else:
                    await message.channel.send(embed=discord.Embed(
                        description = 'Usage: `random <skin / emote / pickaxe / backpack / all>`',
                        color = 0x349eeb
                    ).set_author(name=f'{self.user.display_name} - {self.session_id}', icon_url=await self.get_outfit_icon(self.party.me.outfit)))
                    return

            if cmd[0].lower() == 'hide':

                if self.party.leader != self.party.me:

                    await message.channel.send(embed=discord.Embed(
                        description = 'I am not the party leader!',
                        color = 0xff2929
                    ))
                    return
                
                if len(cmd) != 1:
                    del cmd[0]
                    args = ' '.join(cmd)

                    for member in self.party.members:
                        if member.display_name.lower().startswith(args.lower()):
                            await self.party.hide(member)
                            await message.channel.send(embed=discord.Embed(
                                description = f'**{member.display_name}** is now **hidden**',
                                color = 0x349eeb
                            ))
                            return
                    
                    await message.channel.send(embed=discord.Embed(
                        description = 'No member with that name was found',
                        color = 0xff2929
                    ))
                    return

                else:

                    await message.channel.send(embed=discord.Embed(
                        description = 'Usage: `hide <member name>`',
                        color = 0x349eeb
                    ))
                    return

            if cmd[0].lower() == 'show':

                if self.party.leader != self.party.me:

                    await message.channel.send(embed=discord.Embed(
                        description = 'I am not the party leader!',
                        color = 0xff2929
                    ))
                    return
                
                if len(cmd) != 1:
                    del cmd[0]
                    args = ' '.join(cmd)

                    for member in self.party.members:
                        if member.display_name.lower().startswith(args.lower()):
                            await self.party.show(member)
                            await message.channel.send(embed=discord.Embed(
                                description = f'**{member.display_name}** is now **shown**',
                                color = 0x349eeb
                            ))
                            return
                    
                    await message.channel.send(embed=discord.Embed(
                        description = 'No member with that name was found',
                        color = 0xff2929
                    ))
                    return

                else:

                    await message.channel.send(embed=discord.Embed(
                        description = 'Usage: `hide <member name>`',
                        color = 0x349eeb
                    ))
                    return

            if cmd[0].lower() == 'match':
                del cmd[0]
                args = ' '.join(cmd)

                if len(cmd) == 0:

                    await message.channel.send(embed=discord.Embed(
                        description = 'Usage: `match <0 to 255>`',
                        color = 0x349eeb
                    ))
                    return
                
                else:

                    try:
                        players_int = int(args.strip(' '))

                        if players_int < 0:

                            await message.channel.send(embed=discord.Embed(
                                description = 'The number can\'t be negative!',
                                color = 0x349eeb
                            ))
                            return

                        elif players_int > 255:

                            await message.channel.send(embed=discord.Embed(
                                description = 'The number can\'t be more than 255!',
                                color = 0x349eeb
                            ))
                            return

                        if self.in_match_timestamp == None:
                            self.in_match_timestamp = datetime.datetime.utcnow()

                        await self.party.me.set_in_match(players_left=players_int, started_at=self.in_match_timestamp)
                        await message.channel.send(embed=discord.Embed(
                            description = f'In-match state updated. {players_int} left',
                            color = 0x349eeb
                        ))
                        return
                    except ValueError:

                        await message.channel.send(embed=discord.Embed(
                            description = 'Players in match must be a number between 0 and 255!',
                            color = 0x349eeb
                        ))
                        return
                    
                    except Exception as e:

                        await message.channel.send(embed=discord.Embed(
                            description = f'An uknown error ocurred: `{e}`',
                            color = 0x349eeb
                        ))
                        traceback.print_exc()
                        return

            if cmd[0].lower() == 'unmatch':
                
                try:
                    self.in_match_timestamp = None
                    await self.party.me.clear_in_match()
                    await message.channel.send(embed=discord.Embed(
                        description = 'In-match state cleared.',
                        color = 0x349eeb
                    ))
                except Exception as e:
                    await message.channel.send(embed=discord.Embed(
                        description = f'An unknown error ocurred: {e}',
                        color = 0xff2929
                    ))


            if cmd[0].lower() == 'skin':
                if len(cmd) != 1:
                    del cmd[0]
                    args = ' '.join(cmd)
                    
                    if cmd[0].lower().startswith('cid_'):
                        search = await self.cosmetics.get(type_='outfit', id_=args)
                        result = search
                    else:
                        search = await self.cosmetics.get(type_='outfit', name=args)
                        result = search[0] if len(search) > 0 else []
                    if len(result) != 0:
                        await self.party.me.edit_and_keep(partial(self.party.me.set_outfit, result['id']))

                        await message.channel.send(embed=discord.Embed(
                            title = 'Set outfit',
                            description = f'**Name:** {result["name"]}\n**ID:** {result["id"]}',
                            color = 0x349eeb
                        ).set_thumbnail(url=result['images']['icon']).set_author(name=f'{self.user.display_name} - {self.session_id}', icon_url=await self.get_outfit_icon(self.party.me.outfit)))
                        if self.is_custom:
                            util.database.users.find_one_and_update({'user_id': self.message.author.id}, {'$set': {'custom_account.outfit': result['id'], 'custom_account.outfit_variants': []}})
                    else:
                        await message.channel.send(embed=discord.Embed(
                            description = 'Nothing found',
                            color = 0xff2929
                        ).set_author(name=f'{self.user.display_name} - {self.session_id}', icon_url=await self.get_outfit_icon(self.party.me.outfit)))

            if cmd[0].lower() == 'emote':
                if len(cmd) != 1:
                    del cmd[0]
                    args = ' '.join(cmd)
                    if cmd[0].lower().startswith('eid_'):
                        search = await self.cosmetics.get(type_='emote', id_=args)
                        result = search
                    else:
                        search = await self.cosmetics.get(type_='emote', name=args)
                        result = search[0] if len(search) > 0 else []
                    if len(result) != 0:
                        await self.party.me.clear_emote()
                        await self.party.me.edit_and_keep(partial(self.party.me.set_emote, result['id']))

                        await message.channel.send(embed=discord.Embed(
                            title = 'Set emote',
                            description = f'**Name:** {result["name"]}\n**ID:** {result["id"]}',
                            color = 0x349eeb
                        ).set_thumbnail(url=result['images']['icon']).set_author(name=f'{self.user.display_name} - {self.session_id}', icon_url=await self.get_outfit_icon(self.party.me.outfit)))
                        if self.is_custom:
                            util.database.users.find_one_and_update({'user_id': self.message.author.id}, {'$set': {'custom_account.emote': result['id']}})
                    else:
                        await message.channel.send(embed=discord.Embed(
                            description = 'Nothing found',
                            color = 0xff2929
                        ).set_author(name=f'{self.user.display_name} - {self.session_id}', icon_url=await self.get_outfit_icon(self.party.me.outfit)))

            if cmd[0].lower() == 'backpack':
                if len(cmd) != 1:
                    del cmd[0]
                    args = ' '.join(cmd)
                    if args.lower() == 'clear':
                        await self.party.me.edit_and_keep(partial(self.party.me.set_backpack, 'bid_'))
                        await message.channel.send(embed=discord.Embed(
                            description = 'Cleared backpack',
                            color = 0x349eeb
                        ).set_author(name=f'{self.user.display_name} - {self.session_id}', icon_url=await self.get_outfit_icon(self.party.me.outfit)))
                        if self.is_custom:
                            util.database.users.find_one_and_update({'user_id': self.message.author.id}, {'$set': {'custom_account.backpack': '', 'custom_account.backpack_variants': []}})
                        return
                    if cmd[0].lower().startswith('bid_'):
                        search = await self.cosmetics.get(type_='backpack', id_=args)
                        result = search
                    else:
                        search = await self.cosmetics.get(type_='backpack', name=args)
                        result = search[0] if len(search) > 0 else []
                    if len(result) != 0:
                        await self.party.me.edit_and_keep(partial(self.party.me.set_backpack, result['id']))

                        await message.channel.send(embed=discord.Embed(
                            title = 'Set backpack',
                            description = f'**Name:** {result["name"]}\n**ID:** {result["id"]}',
                            color = 0x349eeb
                        ).set_thumbnail(url=result['images']['icon']).set_author(name=f'{self.user.display_name} - {self.session_id}', icon_url=await self.get_outfit_icon(self.party.me.outfit)))
                    else:
                        await message.channel.send(embed=discord.Embed(
                            description = 'Nothing found',
                            color = 0xff2929
                        ).set_author(name=f'{self.user.display_name} - {self.session_id}', icon_url=await self.get_outfit_icon(self.party.me.outfit)))

            if cmd[0].lower() == 'pickaxe':
                if len(cmd) != 1:
                    del cmd[0]
                    args = ' '.join(cmd)
                    if args.lower() == 'clear':
                        await self.party.me.edit_and_keep(partial(self.party.me.set_backpack, 'pickaxe_'))
                        util.database.users.find_one_and_update({'user_id': self.message.author.id}, {'$set': {'custom_account.pickaxe': '', 'custom_account.pickaxe_variants': []}})
                        await message.channel.send(embed=discord.Embed(
                            description = 'Cleared pickaxe',
                            color = 0x349eeb
                        ).set_author(name=f'{self.user.display_name} - {self.session_id}', icon_url=await self.get_outfit_icon(self.party.me.outfit)))
                    if cmd[0].lower().startswith('pickaxe_'):
                        search = await self.cosmetics.get(type_='pickaxe', id_=args)
                        result = search
                    else:
                        search = await self.cosmetics.get(type_='pickaxe', name=args)
                        result = search[0] if len(search) > 0 else []
                    if len(result) != 0:
                        await self.party.me.edit_and_keep(partial(self.party.me.set_pickaxe, result['id']))

                        await self.party.me.clear_emote()       #in order to show the pickaxe
                        await self.party.me.set_emote(asset='EID_IceKing')

                        await message.channel.send(embed=discord.Embed(
                            title = 'Set pickaxe',
                            description = f'**Name:** {result["name"]}\n**ID:** {result["id"]}',
                            color = 0x349eeb
                        ).set_thumbnail(url=result['images']['icon']).set_author(name=f'{self.user.display_name} - {self.session_id}', icon_url=await self.get_outfit_icon(self.party.me.outfit)))
                        if self.is_custom:
                            util.database.users.find_one_and_update({'user_id': self.message.author.id}, {'$set': {'custom_account.pickaxe': result['id'], 'custom_account.pickaxe_variants': []}})
                    else:
                        await message.channel.send(embed=discord.Embed(
                            description = 'Nothing found',
                            color = 0xff2929
                        ).set_author(name=f'{self.user.display_name} - {self.session_id}', icon_url=await self.get_outfit_icon(self.party.me.outfit)))


            if cmd[0].lower() == 'style':
                del cmd[0]
                args = ' '.join(cmd)

                if len(cmd) == 0:
                    await message.channel.send(embed=discord.Embed(
                        description = f'Usage: `style <skin / backpack / pickaxe>`',
                        color = 0x349eeb
                    ).set_author(name=f'{self.user.display_name} - {self.session_id}', icon_url=await self.get_outfit_icon(self.party.me.outfit)))
                    return

                types = {
                    'outfit': 'AthenaCharacter',
                    'backpack': 'AthenaBackpack',
                    'pickaxe': 'AthenaPickaxe'
                }
                def check(msg):
                    return msg.author == message.author and msg.channel == message.channel
                
                if cmd[0] == 'skin':

                    cosmetic = await self.cosmetics.get('outfit', id_=self.party.me.outfit)
                    if cosmetic['variants'] == None:
                        await message.channel.send(embed=discord.Embed(
                            description = 'This skin do not have styles',
                            color = 0x349eeb
                        ).set_author(name=f'{self.user.display_name} - {self.session_id}', icon_url=await self.get_outfit_icon(self.party.me.outfit)))
                        return

                    else:

                        if len(cosmetic['variants']) > 1:
                            categories = cosmetic['variants']
                            categories_str = ''
                            count = 0
                            for category in categories:
                                count += 1
                                categories_str += f'**{count}.** {category["type"]}\n'

                            msg = await message.channel.send(embed=discord.Embed(
                                title = 'Select type of variant',
                                description = f'{categories_str}',
                                color = 0x349eeb
                            ).set_author(name=f'{self.user.display_name} - {self.session_id}', icon_url=await self.get_outfit_icon(self.party.me.outfit)))
                            try:
                                m = await self.bot.wait_for('message', check=check, timeout=300)
                                if m.content not in string.digits:
                                    return
                                try:
                                    category = categories[int(m.content) - 1]
                                except Exception:
                                    return
                            except asyncio.TimeoutError:
                                await msg.delete()
                                return
                        
                        else:
                            category = cosmetic['variants'][0]

                        variant_options = category['options']
                        variant_channel = category['channel'].lower()

                        options_str = ''
                        count = 0
                        for option in variant_options:
                            count += 1
                            options_str += f'**{count}.** {option["name"]}\n'

                        msg = await message.channel.send(embed=discord.Embed(
                            title = 'Select style',
                            description = f'{options_str}',
                            color = 0x349eeb
                        ).set_author(name=f'{self.user.display_name} - {self.session_id}', icon_url=await self.get_outfit_icon(self.party.me.outfit)))
                        try:
                            m = await self.bot.wait_for('message', check=check, timeout=300)
                            if m.content not in string.digits:
                                    return
                            try:
                                selected = variant_options[int(m.content) - 1]
                                user_selection_int = int(m.content)
                            except IndexError:
                                return
                            try:
                                variants = await get_variants(self, types['outfit'], variant_channel, user_selection_int, selected)
                                await self.party.me.edit_and_keep(partial(self.party.me.set_outfit, asset=cosmetic['id'], variants=variants))
                            
                            except Exception as e:
                                await message.channel.send(embed=discord.Embed(
                                    title = 'Error',
                                    description = f'An uknown error ocurred:\n```py\n{traceback.format_exc()}```',
                                    color = 0xff2929
                                ).set_author(name=f'{self.user.display_name} - {self.session_id}', icon_url=await self.get_outfit_icon(self.party.me.outfit)))
                                
                                return

                            await message.channel.send(embed=discord.Embed(
                                description = f'Skin style changed to **{selected["name"]}**',
                                color = 0x349eeb
                            ).set_thumbnail(url=selected['image']).set_author(name=f'{self.user.display_name} - {self.session_id}', icon_url=await self.get_outfit_icon(self.party.me.outfit)))
                            if self.is_custom:
                                util.database.users.find_one_and_update({'user_id': self.message.author.id}, {'$set': {'custom_account.outfit_variants': variants}})
                            return

                        except asyncio.TimeoutError:
                            await msg.delete()

                if cmd[0] == 'backpack':

                    cosmetic = await self.cosmetics.get('backpack', id_=self.party.me.backpack)
                    if cosmetic['variants'] == None:
                        await message.channel.send(embed=discord.Embed(
                            description = 'This backpack do not have styles',
                            color = 0x349eeb
                        ).set_author(name=f'{self.user.display_name} - {self.session_id}', icon_url=await self.get_outfit_icon(self.party.me.outfit)))
                        return

                    else:

                        if len(cosmetic['variants']) > 1:
                            categories = cosmetic['variants']
                            categories_str = ''
                            count = 0
                            for category in categories:
                                count += 1
                                categories_str += f'**{count}.** {category["type"]}\n'

                            msg = await message.channel.send(embed=discord.Embed(
                                title = 'Select type of variant',
                                description = f'{categories_str}',
                                color = 0x349eeb
                            ).set_author(name=f'{self.user.display_name} - {self.session_id}', icon_url=await self.get_outfit_icon(self.party.me.outfit)))
                            try:
                                m = await self.bot.wait_for('message', check=check, timeout=300)
                                if m.content not in string.digits:
                                    return
                                try:
                                    category = categories[int(m.content) - 1]
                                except Exception:
                                    return
                            except asyncio.TimeoutError:
                                await msg.delete()
                                return
                        
                        else:
                            category = cosmetic['variants'][0]

                        variant_options = category['options']
                        variant_channel = category['channel'].lower()

                        options_str = ''
                        count = 0
                        for option in variant_options:
                            count += 1
                            options_str += f'**{count}.** {option["name"]}\n'

                        msg = await message.channel.send(embed=discord.Embed(
                            title = 'Select style',
                            description = f'{options_str}',
                            color = 0x349eeb
                        ).set_author(name=f'{self.user.display_name} - {self.session_id}', icon_url=await self.get_outfit_icon(self.party.me.outfit)))
                        try:
                            m = await self.bot.wait_for('message', check=check, timeout=300)

                            try:
                                selected = variant_options[int(m.content) - 1]
                                user_selection_int = int(m.content)
                            except IndexError:
                                return
                            try:
                                variants = await get_variants(self, types['backpack'], variant_channel, user_selection_int, selected)
                                await self.party.me.edit_and_keep(partial(self.party.me.set_backpack, asset=cosmetic['id'], variants=variants))
                            
                            except Exception as e:
                                await message.channel.send(embed=discord.Embed(
                                    title = 'Error',
                                    description = f'An uknown error ocurred:\n```py\n{traceback.format_exc()}```',
                                    color = 0xff2929
                                ).set_author(name=f'{self.user.display_name} - {self.session_id}', icon_url=await self.get_outfit_icon(self.party.me.outfit)))
                                
                                return

                            await message.channel.send(embed=discord.Embed(
                                description = f'Backpack style changed to **{selected["name"]}**',
                                color = 0x349eeb
                            ).set_thumbnail(url=selected['image']).set_author(name=f'{self.user.display_name} - {self.session_id}', icon_url=await self.get_outfit_icon(self.party.me.outfit)))
                            if self.is_custom:
                                util.database.users.find_one_and_update({'user_id': self.message.author.id}, {'$set': {'custom_account.backpack_variants': variants}})
                            return

                        except asyncio.TimeoutError:
                            await msg.delete()
                
                if cmd[0] == 'pickaxe':

                    cosmetic = await self.cosmetics.get('pickaxe', id_=self.party.me.backpack)
                    if cosmetic['variants'] == None:
                        await message.channel.send(embed=discord.Embed(
                            description = 'This pickaxe do not have styles',
                            color = 0x349eeb
                        ).set_author(name=f'{self.user.display_name} - {self.session_id}', icon_url=await self.get_outfit_icon(self.party.me.outfit)))
                        return

                    else:

                        if len(cosmetic['variants']) > 1:
                            categories = cosmetic['variants']
                            categories_str = ''
                            count = 0
                            for category in categories:
                                count += 1
                                categories_str += f'**{count}.** {category["type"]}\n'

                            msg = await message.channel.send(embed=discord.Embed(
                                title = 'Select type of variant',
                                description = f'{categories_str}',
                                color = 0x349eeb
                            ).set_author(name=f'{self.user.display_name} - {self.session_id}', icon_url=await self.get_outfit_icon(self.party.me.outfit)))
                            try:
                                m = await self.bot.wait_for('message', check=check, timeout=300)
                                if m.content not in string.digits:
                                    return
                                try:
                                    category = categories[int(m.content) - 1]
                                except Exception:
                                    return
                            except asyncio.TimeoutError:
                                await msg.delete()
                                return
                        
                        else:
                            category = cosmetic['variants'][0]

                        variant_options = category['options']
                        variant_channel = category['channel'].lower()

                        options_str = ''
                        count = 0
                        for option in variant_options:
                            count += 1
                            options_str += f'**{count}.** {option["name"]}\n'

                        msg = await message.channel.send(embed=discord.Embed(
                            title = 'Select style',
                            description = f'{options_str}',
                            color = 0x349eeb
                        ).set_author(name=f'{self.user.display_name} - {self.session_id}', icon_url=await self.get_outfit_icon(self.party.me.outfit)))
                        try:
                            m = await self.bot.wait_for('message', check=check, timeout=300)
                            if m.content not in string.digits:
                                    return
                            try:
                                selected = variant_options[int(m.content) - 1]
                                user_selection_int = int(m.content)
                            except IndexError:
                                return
                            try:
                                variants = await get_variants(self, types['pickaxe'], variant_channel, user_selection_int, selected)
                                await self.party.me.edit_and_keep(partial(self.party.me.set_pickaxe, asset=cosmetic['id'], variants=variants))
                            
                            except Exception as e:
                                await message.channel.send(embed=discord.Embed(
                                    title = 'Error',
                                    description = f'An uknown error ocurred:\n```py\n{traceback.format_exc()}```',
                                    color = 0xff2929
                                ).set_author(name=f'{self.user.display_name} - {self.session_id}', icon_url=await self.get_outfit_icon(self.party.me.outfit)))
                                
                                return

                            await message.channel.send(embed=discord.Embed(
                                description = f'Pickaxe style changed to **{selected["name"]}**',
                                color = 0x349eeb
                            ).set_thumbnail(url=selected['image']).set_author(name=f'{self.user.display_name} - {self.session_id}', icon_url=await self.get_outfit_icon(self.party.me.outfit)))
                            if self.is_custom:
                                util.database.users.find_one_and_update({'user_id': self.message.author.id}, {'$set': {'custom_account.pickaxe_variants': variants}})
                            return

                        except asyncio.TimeoutError:
                            await msg.delete()

                else:
                    await message.channel.send(embed=discord.Embed(
                        description = f'Usage: `style <skin / backpack / pickaxe>`',
                        color = 0x349eeb
                    ).set_author(name=f'{self.user.display_name} - {self.session_id}', icon_url=await self.get_outfit_icon(self.party.me.outfit)))
                    return

        except Exception:
            util.discord_log(content=f'[{self.user.display_name}] Error handling command "{message.content}": ```py\n{traceback.format_exc()}```')