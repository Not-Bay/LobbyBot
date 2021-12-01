from discord.ext import commands
from discord_components.component import Button, ButtonStyle
from discord_components.interaction import InteractionType
from modules import auth
from bson import json_util
import traceback
import asyncio
import discord
import datetime
import crayons
import json
import time
import util
import ast
import os
import io

from util import log, discord_log
from modules import auth

reactions = ['<:no:816337113968279612>', '<:yes:816337064130904105>']
AUTHORIZATION_CODE_URL = "https://www.epicgames.com/id/api/redirect?clientId=3446cd72694c4a4485d81b77adbb2141&responseType=code"

class Admin(commands.Cog):

    def __init__(self, bot):
        self.bot = bot

    @commands.command(hidden=True)
    async def eval(self, ctx, *, cmd):
        """Evaluates code"""
        if ctx.author.id != 364878336872284163:
            return
        
        fn_name = "_eval_expr"
        cmd = "\n".join(f"    {i}" for i in cmd.splitlines())
        body = f"async def {fn_name}():\n{cmd}"
        parsed = ast.parse(body)
        body = parsed.body[0].body
        util.insert_returns(body)
        env = {
            'import': __import__,
            'auth': auth,
            'discord': discord,
            'bot': ctx.bot,
            'ctx': ctx,
            'util': util,
            'os': os
        }
        exec(compile(parsed, filename="<ast>", mode="exec"), env)

        try:
            result = (await eval(f"{fn_name}()", env))
            await ctx.send(f'```py\n{result}```')
        except Exception as error:
            await ctx.send(f'```\n{error}```')

    @commands.command(hidden=True)
    @commands.is_owner()
    async def _setstatus(self, ctx, *, newstatus):
        """
        Sets a status for the bot
        """

        if newstatus in ['off', 'disable']:
            util.status_loop = True
            await ctx.send(embed=discord.Embed(
                description = 'Custom status disabled',
                color = discord.Colour.blue()
            ))
            return
        else:
            util.status_loop = False
            await self.bot.change_presence(activity=discord.Game(name=newstatus))
            await ctx.send(embed=discord.Embed(
                description = f'Changed status to `{newstatus}`',
                color = discord.Colour.blue()
            ))
            return

    @commands.command(hidden=True)
    async def _glitched(self, ctx):
        """
        Show which accounts are flagged as glitched
        """
        if ctx.author.id not in util.get_config()['staff_ids']:
            return

        glitched_len = util.database.credentials.count({"glitched": True})

        if glitched_len == 0:
            await ctx.send(embed=discord.Embed(
                description = 'There is no glitched accounts.',
                color = 0x349eeb
            ))
            return
        
        else:
            glitched_accounts = util.database.credentials.aggregate([{"$sample": {"size": glitched_len}},{"$match": {"glitched": True}}])

            accounts_str = ''
            for i in glitched_accounts:
                accounts_str += i['display_name'] + '\n'

            await ctx.send(embed=discord.Embed(
                color = 0x349eeb,
                description = '**Accounts flagged as glitched**\n' + accounts_str,
            ))
    

    @commands.command(hidden=True)
    async def _disablebots(self, ctx):
        """
        Disable the !start command
        """
        if ctx.author.id not in util.get_config()['staff_ids']:
            return

        util.allow_new_sessions = False
        await ctx.send(embed=discord.Embed(
            description = 'New sessions are **disabled**',
            color = discord.Colour.blue()
        ))

    @commands.command(hidden=True)
    async def _enablebots(self, ctx):
        """
        Enable the !start command
        """
        if ctx.author.id not in util.get_config()['staff_ids']:
            return

        util.allow_new_sessions = True
        await ctx.send(embed=discord.Embed(
            description = 'New sessions are **enabled**',
            color = discord.Colour.blue()
        ))

    @commands.command(hidden=True)
    async def _disablecustombots(self, ctx):
        """
        Disable the !startcustom command
        """
        if ctx.author.id not in util.get_config()['staff_ids']:
            return

        util.allow_new_sessions = False
        await ctx.send(embed=discord.Embed(
            description = 'New custom sessions are **disabled**',
            color = discord.Colour.blue()
        ))

    @commands.command(hidden=True)
    async def _enablecustombots(self, ctx):
        """
        Enable the !startcustom command
        """
        if ctx.author.id not in util.get_config()['staff_ids']:
            return

        util.allow_new_sessions = True
        await ctx.send(embed=discord.Embed(
            description = 'New custom sessions are **enabled**',
            color = discord.Colour.blue()
        ))

    @commands.command(hidden=True)
    async def _session(self, ctx, sessionId=None, action=None):

        if ctx.author.id not in util.get_config()['staff_ids']:
            return

        if sessionId == None:

            return
        
        else:

            index_int = 0
            current_session = None
            for i in util.active_sessions:
                index_int + 1
                if i._id.lower() == sessionId.lower():
                    current_session = i
                    break

            index_int - 1

            if current_session == None:

                await ctx.send(embed=discord.Embed(
                    description = 'There are not session with that id',
                    color = 0xff2929
                ))
                return

            else:

                if action in ['restart', 'refresh']:

                    msg = await ctx.send(embed=discord.Embed(
                        description = f'Restarting session `{current_session._id}`...',
                        color = discord.Colour.orange()
                    ))
                    await current_session.restart_client()

                    await msg.edit(embed=discord.Embed(
                        description = f'Session `{current_session._id}` restarted.',
                        color = discord.Colour.green()
                    ))
                    return


                elif action in ['stop', 'finish']:

                    msg = await ctx.send(embed=discord.Embed(
                        description = f'Stopping session {current_session._id}...',
                        color = discord.Colour.orange()
                    ))

                    await current_session.ctx.send(embed=discord.Embed(
                        description = 'Finished session.',
                        color = discord.Colour.blue()
                    ).set_footer(text=current_session.account["display_name"]))
                    asyncio.create_task(current_session.stop_client())

                    await msg.edit(embed=discord.Embed(
                        description = f'Session {current_session._id} finished.',
                        color = discord.Colour.blue()
                    ))
                    return

                else:

                    embed = discord.Embed(
                        title = f'Session {current_session._id}',
                        color = discord.Colour.blue()
                    )
                    embed.add_field(name='User', value=f'<@{current_session.ctx.author.id}>', inline=True)
                    embed.add_field(name='Bot', value=current_session.account["display_name"], inline=True)
                    embed.add_field(name='Time active', value=str(datetime.timedelta(seconds=int(round(time.time() - current_session._startTime)))), inline=True)
                    embed.add_field(name='List index', value=str(index_int), inline=True)


                    await ctx.send(embed=embed)
                    return


    @commands.command(hidden=True)
    async def _addaccount(self, ctx):
        """
        Adds an account to the bot credentials database
        """
        if ctx.author.id not in util.get_config()['staff_ids']:
            return

        AUTH = auth.AuthorizationCode()

        msg = await ctx.send(embed=discord.Embed(
            title = 'Add account',
            description = f'Enter [here]({AUTHORIZATION_CODE_URL}) and send the authorization code',
            color = discord.Colour.orange()
        ))

        def check(message):
            return message.author.id == ctx.author.id and message.channel == ctx.channel

        try:
            code = await self.bot.wait_for('message', check=check, timeout=600)

            if code.content == '!cancel':
                await msg.edit(embed=discord.Embed(
                    title = 'Add account',
                    description = f'Cancelled.',
                    color = 0xff2929
                ))

            else:

                await msg.edit(embed=discord.Embed(
                    title = 'Add account',
                    description = f'Generating credentials <a:loading:815646116154310666>',
                    color = discord.Colour.orange()
                ))

                auth_session = await AUTH.authenticate(code.content)

                try:
                    error = auth_session['errorMessage']

                    await msg.edit(embed=discord.Embed(
                        title = 'Add account',
                        description = f'An error ocurred during authorization: `{error}`',
                        color = discord.Colour.red()
                    ))
                    return
                except:

                    if util.database.credentials.find_one({"display_name": auth_session['displayName']}) != None:
                        util.database.credentials.find_one_and_delete({"display_name": auth_session['displayName']})

                    device_auths = await AUTH.generate_device_auths(auth_session)

                    try:
                        error = auth_session['errorMessage']

                        await msg.edit(embed=discord.Embed(
                            title = 'Add account',
                            description = f'An error ocurred generating device auths: `{error}`',
                            color = discord.Colour.red()
                        ))
                        await AUTH.kill_auth_session(auth_session)
                        return
                    except:

                        accountdata = {
                            "active": False,
                            "glitched": False,
                            "display_name": auth_session['displayName'],
                            "device_id": device_auths['deviceId'],
                            "account_id": device_auths['accountId'],
                            "secret": device_auths['secret']
                        }
                        util.database.credentials.insert_one(accountdata)

                        await msg.edit(embed=discord.Embed(
                            title = 'Add account',
                            description = f'Account {auth_session["displayName"]} saved in database correctly!',
                            color = discord.Colour.green()
                        ))
                        await AUTH.kill_auth_session(auth_session)

        except asyncio.TimeoutError:

            await msg.edit(embed=discord.Embed(
                    title = 'Add account',
                    description = f'Cancelled.',
                    color = 0xff2929
                ))


    @commands.command(hidden=True)
    @commands.is_owner()
    async def _removeaccount(self, ctx, *,accountname=None):

        if ctx.author.id not in util.get_config()['staff_ids']:
            return

        if accountname != None:

            account = util.database.credentials.find_one_and_delete({"display_name": accountname})

            if account != None:
                await ctx.send(embed=discord.Embed(
                    description = f'Removed account "{account["display_name"]}" from database',
                    color = 0x349eeb
                ))
            else:
                await ctx.send(embed=discord.Embed(
                    description = f'There\'s no accounts with name "{accountname}" in database',
                    color = 0xff2929
                ))

    @commands.command(hidden=True)
    async def _refreshaccount(self, ctx, *, accountname=None):

        if ctx.author.id not in util.get_config()['staff_ids']:
            return

        if accountname != None:

            account = util.database.credentials.find_one({"display_name": accountname})

            if account != None:

                AUTH = auth.AuthorizationCode()

        msg = await ctx.send(embed=discord.Embed(
            title = 'Add account',
            description = f'Enter [here]({AUTHORIZATION_CODE_URL}) and send the authorization code',
            color = discord.Colour.orange()
        ))

        def check(message):
            return message.author.id == ctx.author.id and message.channel == ctx.channel

        try:
            code = await self.bot.wait_for('message', check=check, timeout=600)

            if code.content == '!cancel':
                await msg.edit(embed=discord.Embed(
                    title = 'Refresh account',
                    description = f'Cancelled.',
                    color = 0xff2929
                ))

            else:

                await msg.edit(embed=discord.Embed(
                    title = 'Refresh account',
                    description = f'Refreshing credentials <a:loading:815646116154310666>',
                    color = discord.Colour.orange()
                ))

                auth_session = await AUTH.authenticate(code)

                try:
                    error = auth_session['errorMessage']

                    await msg.edit(embed=discord.Embed(
                        title = 'Refresh account',
                        description = f'An error ocurred during authorization: `{error}`',
                        color = discord.Colour.red()
                    ))
                    return
                except:

                    if util.database.credentials.find_one({"display_name": auth_session['displayName']}) != None:
                        util.database.credentials.find_one_and_delete({"display_name": auth_session['displayName']})

                    device_auths = AUTH.generate_device_auths(auth_session)

                    try:
                        error = auth_session['errorMessage']

                        await msg.edit(embed=discord.Embed(
                            title = 'Refresh account',
                            description = f'An error ocurred generating device auths: `{error}`',
                            color = discord.Colour.red()
                        ))
                        await AUTH.kill_auth_session(auth_session)
                        return
                    except:

                        accountdata = {
                            "active": False,
                            "glitched": False,
                            "display_name": auth_session['displayName'],
                            "device_id": device_auths['deviceId'],
                            "account_id": device_auths['accountId'],
                            "secret": device_auths['secret']
                        }
                        util.database.credentials.insert_one(accountdata)

                        await msg.edit(embed=discord.Embed(
                            title = 'Refresh account',
                            description = f'Account {auth_session["displayName"]} refreshed correctly!',
                            color = discord.Colour.green()
                        ))
                        await AUTH.kill_auth_session(auth_session)

        except asyncio.TimeoutError:

            await msg.edit(embed=discord.Embed(
                    title = 'Refresh account',
                    description = f'Cancelled.',
                    color = 0xff2929
                ))

        
    @commands.command(hidden=True)
    async def _checkaccounts(self, ctx):

        if ctx.author.id not in util.get_config()['staff_ids']:
            return

        log('Performing accounts check...')
        discord_log('Performing accounts check...')

        accounts = list(util.database.credentials.find({}))

        msg = await ctx.send(embed=discord.Embed(
            description = '<a:loading:815646116154310666> Checking accounts...'
        ))

        broken_accounts = 0

        for account in accounts:
            
            AUTH = auth.DeviceAuths()
            auth_session = await AUTH.authenticate(account)

            try:
                if auth_session['errorMessage']:
                    discord_log(f'[ACCOUNTS CHECK] {account["display_name"]} broken. Code `{auth_session["errorCode"]}`. Message: `{auth_session["errorMessage"]}`')
                    log(f'Account {account["display_name"]} broken. Error: {crayons.red(auth_session["errorMessage"])}')
                    broken_accounts += 1
                    util.database.credentials.find_one_and_update({"display_name": account["display_name"]}, {"$set": {"glitched": True}})
            except:
                await AUTH.kill_auth_session(auth_session)
                continue

        discord_log(f'Accounts check finished. {broken_accounts} broken accounts detected')

        if broken_accounts == 0:

            await msg.edit(embed=discord.Embed(
                description = f'<:yes:816337064130904105> Checked {len(accounts)} accounts. No broken accounts detected',
                color = discord.Colour.green()
            ))
            return
        
        else:

            await msg.edit(embed=discord.Embed(
                description = f'<:no:816337113968279612> Checked {len(accounts)} accounts. There is {broken_accounts} broken accounts',
                color = discord.Colour.red()
            ))
            return

    @commands.command(hidden=True)
    async def _user(self, ctx, user_id = None):

        if ctx.author.id not in util.get_config()['staff_ids']:
            return

        if user_id == None:

            await ctx.send(embed=discord.Embed(
                description = 'Specify an user id!',
                color = 0xff2929
            ))
            return

        user = util.database.users.find_one({'user_id': int(user_id)})

        if user == None:
            await ctx.send(embed=discord.Embed(
                description = 'No user with that id was found in database',
                color = 0xff2929
            ))

        else:

            discord_user = await self.bot.fetch_user(int(user_id))

            embed = discord.Embed(
                description = f'**{discord_user.display_name}#{discord_user.discriminator}**' if discord_user != None else '(failed fetching user name)',
                color = 0x349eeb
            )
            embed.add_field(name='Premium', value='<:yes:816337064130904105>' if user['premium'] == True else '<:no:816337113968279612>', inline=False)
            if user['premium']:
                embed.add_field(name='Premium since', value=f'{datetime.datetime.fromtimestamp(int(user["premium_since"])).strftime("%d/%m/%Y %H:%M:%S")}', inline=False)
            embed.add_field(name='Custom account configurated', value='<:yes:816337064130904105>' if user['custom_account']['configurated'] == True else '<:no:816337113968279612>', inline=False)

            message_buttons = []

            if user['premium'] == True:
                message_buttons.append(Button(style=ButtonStyle.red, label='Remove premium access'))
            else:
                message_buttons.append(Button(style=ButtonStyle.green, label='Give premium access'))
            if user['custom_account']['configurated'] == True:
                message_buttons.append(Button(style=ButtonStyle.red, label='Remove saved account', custom_id='USR_REMOVE_CUSTOM'))
                
            message_buttons.append(Button(style=ButtonStyle.red, label='Delete from database'))
            message_buttons.append(Button(style=ButtonStyle.gray, label='Send data copy to user'))

            msg = await ctx.send(
                embed=embed,
                components=message_buttons
            )

            def check(interaction):
                return ctx.author == interaction.user and interaction.channel == ctx.channel

            try:
                result = await self.bot.wait_for('button_click', timeout=300, check=check)

                if result.component.label == 'Give premium access':
                    util.database.users.find_one_and_update({'user_id': user['user_id']}, {"$set": {"premium": True, "premium_since": int(time.time())}})
                    await result.respond(
                        type=InteractionType.UpdateMessage,
                        embed = discord.Embed(
                            description = f'Gave premium access to user {user_id} correctly!',
                            color = 0x349eeb
                        ),
                        components=[]
                    )

                elif result.component.label == 'Remove premium access':
                    util.database.users.find_one_and_update({'user_id': user['user_id']}, {"$set": {"premium": False, "premium_since": None}})
                    await result.respond(
                        type=InteractionType.UpdateMessage,
                        embed = discord.Embed(
                            description = f'Removed premium access to user {user_id} correctly!',
                            color = 0x349eeb
                        ),
                        components=[]
                    )

                elif result.component.label == 'Remove saved account':
                    
                    AUTH = auth.DeviceAuths()
                    auth_session = await AUTH.authenticate(user['custom_account'])
                    try:
                        error = auth_session['errorMessage']
                        log(f'Custom account of {user_id} failed authentication: {error}', 'debug')
                    except:
                        delete = await AUTH.delete_device_auths(user['custom_account']['device_id'], user['custom_account']['account_id'], auth_session)
                        if delete.text == '':
                            await AUTH.kill_auth_session(auth_session)
                            util.database.users.find_one_and_update({'user_id': user_id}, {'$set': {'custom_account': util.custom_account_base()}})
                            log(f'User {user_id} saved device auth deleted correctly!')
                            await result.respond(
                                type=InteractionType.UpdateMessage,
                                embed = discord.Embed(
                                    description = f'Deleted user device auth correctly!',
                                    color = 0x349eeb
                                ),
                                components=[]
                            )
                        else:
                            AUTH.kill_auth_session(auth_session)
                            log(f'Failed device auth deletion for user {user_id}: {delete.json()}', 'debug')
                            await result.respond(
                                type=InteractionType.UpdateMessage,
                                embed = discord.Embed(
                                    description = f'An error ocurred deleting user {user_id} saved device auth:```json\n{delete.json()}```',
                                    color = 0xff2929
                                ),
                                components=[]
                            )

                elif result.component.label == 'Delete from database':
                    log(f'Deleting {user_id} from database...', 'debug')

                    if user['custom_account']['configurated'] == True:
                        AUTH = auth.DeviceAuths()
                        auth_session = AUTH.authenticate(user['custom_account'])

                        try:
                            error = auth_session['errorMessage']
                            log(f'Custom account of {user_id} failed authentication, skiping device auth deletion', 'debug')
                            util.database.users.find_one_and_delete({'user_id': user['user_id']})
                            log(f'User {user_id} deleted from database correctly', 'debug')
                            
                            await result.respond(
                                type=InteractionType.UpdateMessage,
                                embed = discord.Embed(
                                    description = f'User {user_id} was deleted from database correctly!',
                                    color = 0x349eeb
                                ),
                                components=[]
                            )

                        except:

                            AUTH.delete_device_auths(user['custom_account']['device_id'], user['custom_account']['account_id'], auth_session)
                            AUTH.kill_auth_session(auth_session)
                            log(f'Deleted saved device auth of {user_id} correctly')
                            util.database.users.find_one_and_delete({'user_id': user['user_id']})
                            log(f'Deleted user {user_id} from database correctly')

                            await result.respond(
                                type=InteractionType.UpdateMessage,
                                embed = discord.Embed(
                                    description = f'User {user_id} was deleted from database correctly!',
                                    color = 0x349eeb
                                ),
                                components=[]
                            )

                elif result.component.label == 'Send data copy to user':

                    embed = discord.Embed(
                        title = 'Copy of your saved data',
                        description = 'You previously requested a copy of your saved data in LobbyBot and here is.\nPlease note that it may contain sensitive information and we recommend you to **do not share it** with anyone.\nGreetings!',
                        color = 0x349eeb
                    ).set_footer(text='This message and the file will be deleted in 20 minutes! Click "Delete now" to do it now')

                    json_data = {           # holy shit i cant just use json.dumps with mongodb objects lmao
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

                    file = discord.File(io.StringIO(json.dumps(json_data, indent=4, ensure_ascii=False)), filename=f'{user_id}.json', spoiler=True)
                    buttons = [Button(style=ButtonStyle.gray, label='Delete now')]

                    try:
                        if discord_user != None:
                            msg = await discord_user.send(embed=embed, file=file, components=buttons)
                            await result.respond(
                                type=InteractionType.UpdateMessage,
                                embed=discord.Embed(
                                    description = 'A copy of the user data has been sent to user direct messages!',
                                    color = 0x349eeb
                                ),
                                components=[]
                            )

                            def check(interaction):
                                return interaction.user == discord_user

                            try:
                                result = await self.bot.wait_for('button_click', timeout=1200, check=check)

                                if result.component.label == 'Delete now':
                                    await msg.delete()

                            except asyncio.TimeoutError:
                                await msg.delete()

                            return
                        
                        else:
                            await result.respond(
                                type=InteractionType.UpdateMessage,
                                embed=discord.Embed(
                                    description = 'Fetch discord user failed. Probably it is not in any server that i am',
                                    color = 0xff2929
                                ),
                                components=[]
                            )
                            return

                    except Exception as e:

                        await result.respond(
                            type=InteractionType.UpdateMessage,
                            embed=discord.Embed(
                                description = f'An error ocurred while trying to send data to the user: {e}',
                                color = 0xff2929
                            ),
                            components=[]
                        )
                        return

            except asyncio.TimeoutError:
                await msg.edit(embed=embed, components=[])

            except Exception:
                await ctx.send(embed=discord.Embed(
                    title = 'An error ocurred',
                    description = f'```py\n{traceback.format_exc()}```'
                ))

    @commands.command(hidden=True)
    async def _restart(self, ctx, now=False):

        if ctx.author.id not in util.get_config()['staff_ids']:
            return

        if now == False:

            if len(util.active_sessions) != 0:

                await ctx.send('The restart will be executed when the active sessions are finished.')
                await self.restart_when_no_sessions()

            else:

                await ctx.send('Rebooting...')
                os.system('systemctl restart lobbybot')
            
        else:

            if now == 'now':
                await ctx.send('Rebooting...')
                for session in util.active_sessions:
                    await session.stop_client()
                os.system('systemctl restart lobbybot')


    async def restart_when_no_sessions():

        while True:

            if len(util.active_sessions) != 0:

                await asyncio.sleep(1)
            
            else:

                os.system('systemctl restart lobbybot')


def setup(bot):
    bot.add_cog(Admin(bot))
