from discord.ext import commands
from discord_components import *
import traceback
import asyncio
import discord
import datetime
import json
import util
import sys
import io

from modules import auth

AUTHORIZATION_CODE_URL = "https://www.epicgames.com/id/login?redirectUrl=https%3A%2F%2Fwww.epicgames.com%2Fid%2Fapi%2Fredirect%3FclientId%3D3446cd72694c4a4485d81b77adbb2141%26responseType%3Dcode&prompt=login"
AUTHORIZATION_CODE_EXAMPLE_IMAGE = "https://media.discordapp.net/attachments/838192486547324938/855203089887133757/authorizationcode.png"

class Events(commands.Cog):

    def __init__(self, bot):
        self.bot = bot

    @commands.Cog.listener()
    async def on_command_error(self, ctx, error):

        if isinstance(error, commands.CommandOnCooldown):

            await ctx.send(embed=discord.Embed(
                description = f'Command on cooldown. Try again in `{error.retry_after[0][1][2]}` seconds',
                color = 0xff2929
            ))

        elif isinstance(error, commands.MissingPermissions):
            await ctx.send(embed=discord.Embed(
                description = 'You do not have sufficient permissions to execute this command',
                color = 0xff2929
            ))
            return

        elif isinstance(error, commands.NoPrivateMessage):
            await ctx.send(embed=discord.Embed(
                description = 'This command is not available in direct messages',
                color = 0xff2929
            ))
            return

        elif isinstance(error, commands.CommandNotFound):
            return

        elif isinstance(error, commands.NotOwner):
            return

        else:
            try:
                err_str = ''
                try:
                    err_str = traceback.format_tb(error)
                except:
                    err_str = error
                util.log(f'Error in command {ctx.message.content}: {traceback.format_tb(type(error), error, error.__traceback__, file=sys.stderr)}', 'error')
                util.discord_log(f'Error in command `{ctx.message.content}`: ```py\n{traceback.format_tb(type(error), error, error.__traceback__, file=sys.stderr)}```')
            except:
                pass


    @commands.Cog.listener()
    async def on_guild_join(self, guild):

        util.log(f'Bot added to a new guild: {guild.id}')
        util.store_guild(guild)

    @commands.Cog.listener()
    async def on_guild_remove(self, guild):

        util.log(f'Bot removed from a guild: {guild.id}')
        util.remove_guild(guild)


    @commands.Cog.listener()
    async def on_button_click(self, interaction):

        if interaction.custom_id == 'USR_REGISTER':

            await interaction.respond(
                type=InteractionType.UpdateMessage,
                embed=discord.Embed(
                    description = 'Registering...',
                    color = 0x349eeb
                ),
                components = []
            )
            util.store_user(interaction.author.id)
            await interaction.message.edit(
                embed=discord.Embed(
                    description = 'Successfully registered!',
                    color = 0x349eeb
                ),
                components=[]
            )

            await asyncio.sleep(2.1)

            user = util.database.users.find_one({'user_id': interaction.author.id})

            embed = discord.Embed(
                title = 'Your LobbyBot account',
                color = 0x349eeb
            )
            embed.add_field(name='Premium', value=f'<:yes:816337064130904105> Since {datetime.datetime.fromtimestamp(int(user["premium_since"])).strftime("%d/%m/%Y")}' if user['premium'] == True else '<:no:816337113968279612>', inline=False)
            embed.add_field(name='Custom account', value=f'<:yes:816337064130904105> **{user["custom_account"]["display_name"]}**' if user['custom_account']['configurated'] == True else '<:no:816337113968279612> Not yet configured', inline=False)
            embed.set_thumbnail(url=interaction.author.avatar_url)

            buttons = []

            if user['custom_account']['configurated'] == True:
                buttons.append(Button(style=ButtonStyle.blue, label='Remove saved account', custom_id='USR_REMOVE_CUSTOM'))
            else:
                buttons.append(Button(style=ButtonStyle.blue, label='Add bot account', custom_id='USR_ADD_CUSTOM'))

            buttons.append(Button(style=ButtonStyle.gray, label='Request copy of my data', custom_id='USR_DATA_REQUEST'))
            buttons.append(Button(style=ButtonStyle.red, label='Delete my LobbyBot account', custom_id='USR_ACCOUNT_DELETE'))

            await interaction.message.edit(embed=embed, components=buttons)


        elif interaction.custom_id == 'USR_ADD_CUSTOM':

            await interaction.respond(
                type=InteractionType.UpdateMessage,
                embed=discord.Embed(
                    title = 'Add bot account',
                    description = f'• Click `Login` button and login with **an bot account** (Create one if necessary).\n• Copy the 32 character code (example in the image) and send it.',
                    color = 0x349eeb
                ).set_image(url=AUTHORIZATION_CODE_EXAMPLE_IMAGE).set_footer(text='Type "cancel" to cancel'),
                components=[Button(style=ButtonStyle.URL, label='Login', url=AUTHORIZATION_CODE_URL)]
            )

            AUTH = auth.AuthorizationCode()

            def check(message):
                return message.author == interaction.author and message.channel == interaction.channel

            try:
                user_message = await self.bot.wait_for('message', check=check, timeout=300)

                if user_message.content.lower() == 'cancel':

                    await interaction.message.edit(
                        embed=discord.Embed(
                            description = 'Canceled',
                            color = 0xff2929
                        ),
                        components=[]
                    )
                    return

                if len(user_message.content) != 32:
                    await interaction.message.edit(embed=discord.Embed(
                        title = 'Error',
                        description = 'That is not a valid authorization code. Example of code:'
                        ).set_image(url=AUTHORIZATION_CODE_EXAMPLE_IMAGE),
                        components=[]
                    )
                    return

                else:
                    try:
                        await user_message.delete()
                    except:
                        pass

                    await interaction.message.edit(
                        type=InteractionType.UpdateMessage,
                        embed = discord.Embed(
                            description = '<a:loading:815646116154310666> Logging in...',
                            color = discord.Colour.orange()
                        ),
                        components=[]
                    )

                    auth_session = await AUTH.authenticate(str(user_message.content))

                    try:
                        error = auth_session['errorMessage']

                        await interaction.message.edit(
                            embed=discord.Embed(
                                title = 'Error',
                                description = f'An error ocurred while authenticating: `{error}`',
                                color = 0x349eeb
                            ),
                            components=[]
                        )
                        return
                    except:

                        device_auths = await AUTH.generate_device_auths(auth_session)
                        try:
                            error = device_auths['errorMessage']

                            await interaction.message.edit(
                                embed=discord.Embed(
                                    title = 'Error',
                                    description = f'An error ocurred while generating device auth: `{error}`',
                                    color = 0x349eeb
                                ),
                                components=[]
                            )
                            return

                        except:

                            await AUTH.kill_auth_session(auth_session)

                            account = util.custom_account_base()

                            account['configurated'] = True
                            account['display_name'] = auth_session['displayName']
                            account['status'] = f'LobbyBot {util.bot_version}'
                            account['outfit'] = 'CID_028_Athena_Commando_F'
                            account['outfit_variants'] = []
                            account['emote'] = 'EID_KpopDance03'
                            account['backpack'] = 'BID_138_Celestial'
                            account['backpack_variants'] = []
                            account['pickaxe'] = 'Pickaxe_ID_013_Teslacoil'
                            account['pickaxe_variants'] = []
                            account['level'] = 100
                            account['platform'] = 'pc'
                            account['privacy'] = 'private'
                            account['device_id'] = device_auths['deviceId']
                            account['account_id'] = device_auths['accountId']
                            account['secret'] = device_auths['secret']

                            util.database.users.find_one_and_update({"user_id": interaction.author.id}, {"$set": {"custom_account": account}})

                            await interaction.message.edit(
                                embed=discord.Embed(
                                    description = f'Your custom account **{account["display_name"]}** has been saved correctly!',
                                    color = 0x349eeb
                                    ).set_footer(text='Use !startcustom command to start it'),
                                    components=[]
                                )
                            return

            except asyncio.TimeoutError:
                await interaction.message.edit(
                    embed=discord.Embed(
                        description = 'Canceled by timeout',
                        color = 0xff2929
                    ),
                    components = []
                )
                return


        elif interaction.custom_id == 'USR_REMOVE_CUSTOM':

            for session in util.active_sessions:
                if session.ctx.author.id == interaction.author.id:
                    if session.is_custom == True:
                        await interaction.message.edit(
                            embed=discord.Embed(
                                description = 'Your custom account is active. Use `!stop` and try again',
                                color = 0xff2929
                                ),
                                components=[]
                                )
                        return
                    else:
                        break

            user = util.database.users.find_one({'user_id': interaction.author.id})

            def check(message):
                return message.author == interaction.author and message.channel == interaction.channel

            components = [
                Button(style=ButtonStyle.green, label='Confirm'),
                Button(style=ButtonStyle.red, label='Cancel', custom_id='MSG_CANCEL')
            ]

            msg = await interaction.respond(
                type=InteractionType.UpdateMessage,
                embed=discord.Embed(
                    description = f'You have a saved login for **{user["custom_account"]["display_name"]}**\nAre you sure you want to remove it?',
                    color = 0x349eeb
                    ).set_footer(text='The saved device auths will be removed and deleted from the database'),
                components=components
            )

            try:
                result = await self.bot.wait_for('button_click', timeout=300, check=check)

                if result.component.label == 'Confirm':

                    try:
                        AUTH = auth.DeviceAuths()
                        data = await AUTH.authenticate(user['custom_account'])
                        delete = await AUTH.delete_device_auths(user['custom_account']['device_id'], user['custom_account']['account_id'], data)
                        await AUTH.kill_auth_session(data)
                    except:
                        pass

                    util.database.users.find_one_and_update({"user_id": interaction.author.id}, {"$set": {"custom_account": util.custom_account_base()}})

                    await result.respond(
                        type=InteractionType.UpdateMessage,
                        embed=discord.Embed(
                            description = f'Account **{user["custom_account"]["display_name"]}** removed successfully!',
                            color = 0x349eeb
                        ),
                        components=[]
                    )
                    return

            except asyncio.TimeoutError:
                await msg.edit(
                    embed=discord.Embed(
                        description = 'Canceled by timeout',
                        color = 0xff2929
                    )
                )


        elif interaction.custom_id == 'USR_DATA_REQUEST':

            user = util.database.users.find_one({'user_id': interaction.author.id})

            embed = discord.Embed(
                title = 'Copy of your saved data',
                description = 'You previously requested a copy of your saved data in LobbyBot and here is.\nPlease note that it may contain sensitive information and we recommend you to **do not share it** with anyone.\nGreetings!',
                color = 0x349eeb
            ).set_footer(text='This message and the file will be deleted in 10 minutes! Click "Delete now" to do it now')

            to_dict = {           # holy shit i cant just use json.dumps with mongodb objects lmao
                "user_id": user['user_id'],
                "premium": user['premium'],
                "premium_since": user['premium_since'],
                "custom_account": {
                    "configurated": user['custom_account']['configurated'],
                    "display_name": user['custom_account']['display_name'],
                    "outfit": user['custom_account']['outfit'],
                    "outfit_variants": user['custom_account']['outfit_variants'],
                    "emote": user['custom_account']['emote'],
                    "backpack": user['custom_account']['backpack'],
                    "backpack_variants": user['custom_account']['backpack_variants'],
                    "pickaxe": user['custom_account']['pickaxe'],
                    "pickaxe_variants": user['custom_account']['pickaxe_variants'],
                    "status": user['custom_account']['status'],
                    "level": user['custom_account']['level'],
                    "platform": user['custom_account']['platform'],
                    "privacy": user['custom_account']['privacy'],
                    "device_id": user['custom_account']['device_id'],
                    "account_id": user['custom_account']['account_id'],
                    "secret": user['custom_account']['secret']
                }
            }

            file = discord.File(io.StringIO(json.dumps(to_dict, indent=4, ensure_ascii=False)), filename=f'{interaction.author.id}.json', spoiler=True)
            buttons = [Button(style=ButtonStyle.gray, label='Delete now', custom_id='MSG_DELETE')]

            try:
                temp_msg = await interaction.author.send(embed=embed, file=file, components=buttons)
                await interaction.respond(
                    type=InteractionType.UpdateMessage,
                    embed=discord.Embed(
                        description = 'A copy of your data has been sent to your direct messages!',
                        color = 0x349eeb
                    ),
                    components=[]
                )

                def check(res):
                    return res.author == interaction.author and interaction.channel == res.channel

                try:
                    result = await self.bot.wait_for('button_click', timeout=600, check=check)

                    if result.component.label == 'Delete now':
                        await temp_msg.delete()
                        return

                except asyncio.TimeoutError:
                    await temp_msg.delete()
                    return

            except:
                await interaction.respond(
                    type=InteractionType.UpdateMessage,
                    embed=discord.Embed(
                        title = 'Error',
                        description = 'Your direct messages are closed, open them and try again.',
                        color = 0xff2929
                    ),
                    components=[]
                )
                return


        elif interaction.custom_id == 'USR_ACCOUNT_DELETE':

            for session in util.active_sessions:
                if session.ctx.author.id == interaction.author.id:
                    if session.is_custom == True:
                        await interaction.message.edit(embed=discord.Embed(
                            description = 'You cannot do this while your custom bot is running. Use `!stop` and try again.',
                            color = 0xff2929
                        ),
                        components=[]
                        )
                        return
                    else:
                        break

            components = [
                Button(style=ButtonStyle.red, label='Yes, delete my LobbyBot account'),
                Button(style=ButtonStyle.gray, label='Cancel')
            ]
            embed = discord.Embed(
                description = '¿Are you sure? This will remove **all data** about you from the database (including custom bots). If you have a premium subscription you will **not** be able to recover it!',
                color = discord.Colour.orange()
            )

            user = util.database.users.find_one({'user_id': interaction.author.id})

            await interaction.respond(
                type=InteractionType.UpdateMessage,
                embed=embed,
                components=components
            )

            def check(res):
                return res.author == interaction.author and interaction.channel == res.channel

            try:
                result = await self.bot.wait_for('button_click', check=check, timeout=300)

                if result.component.label == 'Yes, delete my LobbyBot account':

                    if user['custom_account']['configurated'] == True:
                        device_auths = user['custom_account']
                        valid_auth_flag = True
                        AUTH = auth.DeviceAuths()
                        auth_session = await AUTH.authenticate(device_auths)
                        delete = util.database.users.find_one_and_delete({'user_id': interaction.author.id})
                        try:
                            error = auth_session['errorMessage']
                            valid_auth_flag = False
                        except:
                            if valid_auth_flag == True:
                                await AUTH.delete_device_auths(device_auths['device_id'], device_auths['account_id'], auth_session)
                                await AUTH.kill_auth_session(auth_session)
                        await result.respond(
                            type=InteractionType.UpdateMessage,
                            embed=discord.Embed(
                                description = 'Your LobbyBot account has been successfully deleted!',
                                color = 0x349eeb
                            ),
                            components=[]
                        )
                        return

                    else:
                        
                        delete = util.database.users.find_one_and_delete({'user_id': interaction.author.id})

                        await result.respond(
                            type=InteractionType.UpdateMessage,
                            embed=discord.Embed(
                                description = 'Your LobbyBot account has been successfully deleted!',
                                color = 0x349eeb
                            ),
                            components=[]
                        )
                        return


            except asyncio.TimeoutError:
                await interaction.message.edit(
                    embed=discord.Embed(
                        description = 'Canceled by timeout.',
                        color = 0xff2929
                    ),
                    components=[]
                )
                return


        elif interaction.custom_id == 'MSG_CANCEL':

            await interaction.respond(
                type=InteractionType.UpdateMessage,
                embed=discord.Embed(
                    description = 'Canceled',
                    color = 0xff2929
                ),
                components = []
            )


        elif interaction.custom_id == 'MSG_DELETE':

            await interaction.message.delete()


        elif interaction.custom_id == 'CMD_CHANNEL_CONFIGURE':

            member = await interaction.guild.fetch_member(interaction.author.id)
            if member.guild_permissions.administrator == False:
                return

            await interaction.respond(
                type=InteractionType.UpdateMessage,
                embed=discord.Embed(
                    description = 'Send the mention or ID of the channel',
                    color = discord.Colour.orange()
                ).set_footer(text='The bot must have permissions to see and send messages in the channel! • Type "cancel" to cancel'),
                components=[]
            )

            def check(message):
                return message.author == interaction.author and message.channel == interaction.channel

            try:
                channel_msg = await self.bot.wait_for('message', check=check, timeout=300)
                id_ = channel_msg.content.strip('<># ')
                try:
                    channel = await self.bot.fetch_channel(id_)
                except:
                    await interaction.message.edit(embed=discord.Embed(
                        description = 'I do not have enough permissions to view that channel. Enable it and try again',
                        color = 0xff2929
                    ),
                    components=[])
                    return
                if channel == None:
                    await interaction.message.edit(embed=discord.Embed(
                        description = 'The channel mention/id is invalid. Make sure the bot has permissions on that channel and try again.',
                        color = 0xff2929
                    ),
                    components=[])
                    return
                else:
                    flag = False
                    missing_str = ''
                    bot_permissions = channel.permissions_for(await interaction.guild.fetch_member(self.bot.user.id))

                    if bot_permissions.use_external_emojis == False:
                        missing_str += f'Use external emojis\n'
                        flag = True
                    if bot_permissions.send_messages == False:
                        missing_str += f'Send messages\n'
                        flag = True
                    if bot_permissions.add_reactions == False:
                        missing_str += f'Add reactions\n'
                        flag = True
                    if bot_permissions.read_messages == False:
                        missing_str += f'Read messages\n'
                        flag = True

                    if flag == False:

                        util.database.guilds.find_one_and_update({'guild_id': interaction.guild.id}, {'$set': {'lb_channel': int(channel.id)}})
                        await interaction.message.edit(embed=discord.Embed(
                            description = f'Command channel changed to <#{channel.id}>!',
                            color = 0x349eeb
                            ),
                            components=[]
                        )
                        return
                    
                    else:

                        await interaction.message.edit(embed=discord.Embed(
                            description = f'I don\'t have enough permissions on that channel. Please enable these permissions and try again:\n```\n{missing_str}\n```',
                            color = 0xff2929
                            ),
                            components=[]
                        )
                        return

            except asyncio.TimeoutError:

                await interaction.message.edit(embed=discord.Embed(
                    description = 'Canceled by timeout',
                    color = 0xff2929
                    ),
                    components=[]
                )


        elif interaction.custom_id == 'CMD_CHANNEL_DISABLE':

            member = await interaction.guild.fetch_member(interaction.author.id)
            if member.guild_permissions.administrator == False:
                return

            util.database.guilds.find_one_and_update({'guild_id': interaction.guild.id}, {'$set': {'lb_channel': None}})
            await interaction.message.edit(embed=discord.Embed(
                description = 'Command channel disabled!',
                color = 0x349eeb
                ),
                components=[]
            )
            return


        elif interaction.custom_id == 'SRV_CHANGE_PREFIX':

            member = await interaction.guild.fetch_member(interaction.author.id)
            if member.guild_permissions.administrator == False:
                return

            await interaction.respond(
                type=InteractionType.UpdateMessage,
                embed=discord.Embed(
                    description = 'Send the new prefix to use, maximum 2 characters.',
                    color = discord.Colour.orange()
                ).set_footer(text='Type "cancel" to cancel'),
                components=[]
            )

            def check(message):
                return message.author == interaction.author and message.channel == interaction.channel

            try:
                msg = await self.bot.wait_for('message', check=check, timeout=300)

                if len(msg.content) > 2:

                    await interaction.message.edit(
                        embed=discord.Embed(
                            description = 'The prefix must have a maximum of 2 characters!',
                            color = 0xff2929
                        )
                    )

                else:

                    util.database.guilds.find_one_and_update({'guild_id': interaction.guild.id}, {'$set': {'prefix': msg.content}})
                    await interaction.message.edit(
                        embed = discord.Embed(
                            description = f'Prefix changed to `{msg.content}`!',
                            color = 0x349eeb
                        )
                    )
                    return

            except asyncio.TimeoutError:
                await interaction.message.edit(
                    embed=discord.Embed(
                        description = 'Canceled by timeout',
                        color = 0xff2929
                    )
                )

def setup(bot):
    bot.add_cog(Events(bot))
