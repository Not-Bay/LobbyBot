from discord.commands import slash_command, Option, OptionChoice, SlashCommandGroup
from discord.ext import commands
import logging
import asyncio
import discord
import time

from modules import crypto, utils
from clients import restclient

log = logging.getLogger('LobbyBot.cogs.account')

class Account(commands.Cog):

    def __init__(self, bot: discord.Bot):
        self.bot = bot

    account = SlashCommandGroup(
        name = 'account',
        description = 'Account related commands'
    )

    @account.command(
        name = 'register',
        description = 'Registers you in our database allowing to store your preferences'
    )
    async def account_register(
        self,
        ctx: discord.ApplicationContext
    ):

        users = await self.bot.database.get_collection('users')

        result = await users.find_one(
            filter = {
                'id': crypto.sha1(str(ctx.author.id))
            }
        )

        if result != None:
            await ctx.respond(
                embed = discord.Embed(
                    title = 'Oops!',
                    description = 'Seems like you are already registered.',
                    color = discord.Color.red()
                ),
            )
            return

        user_data = utils.user_base()
        user_data['id'] = crypto.sha1(str(ctx.author.id))
        user_data['added'] = int(time.time())

        insert = await users.insert_one(
            document = user_data
        )

        if insert == False:
            await ctx.respond(
                embed = discord.Embed(
                    title = 'Oops!',
                    description = 'An error ocurred registering, please try again later.',
                    color = discord.Color.red()
                )
            )
            return

        embed = discord.Embed(
            title = 'Registered',
            description = 'You have successfully registered. You should have access to all features now.',
            color = discord.Color.blue()
        )
        embed.set_footer(text = 'You can delete your saved data anytime with /account delete')

        await ctx.respond(
            embed = embed
        )
        return

    @account.command(
        name = 'delete',
        description = 'Deletes your saved data from our database'
    )
    async def account_register(
        self,
        ctx: discord.ApplicationContext
    ):

        users = await self.bot.database.get_collection('users')

        result = await users.find_one(
            filter = {
                'id': crypto.sha1(str(ctx.author.id))
            }
        )

        if result == None:
            await ctx.respond(
                embed = discord.Embed(
                    title = 'Oops!',
                    description = 'You need to register with `/account register` first.',
                    color = discord.Color.red()
                )
            )
            return

        await ctx.respond(
            embed = discord.Embed(
                title = 'Are you sure?',
                description = 'All your information stored in our database will be deleted, this is not reversible, please confirm',
                color = discord.Color.orange()
            ),
            view = discord.ui.View(
                discord.ui.Button(
                    style = discord.ButtonStyle.red,
                    label = 'Confirm',
                    custom_id = 'confirm_delete'
                ),
                discord.ui.Button(
                    style = discord.ButtonStyle.gray,
                    label = 'Cancel',
                    custom_id = 'cancel_delete'
                ),
                timeout = 120,
                disable_on_timeout = True
            )
        )

        try:
            interaction = await self.bot.wait_for(
                'interaction',
                check = lambda i: i.user == ctx.author and i.custom_id in ['confirm_delete', 'cancel_delete'],
                timeout = 120
            )
        except asyncio.TimeoutError:
            return

        if interaction.custom_id == 'cancel_delete':

            await ctx.interaction.edit_original_message(
                embed = discord.Embed(
                    title = 'Canceled',
                    description = 'Deletion of data canceled.',
                    color = discord.Color.blue()
                ),
                view = None
            )

        else:

            delete = await users.delete_one( 
                filter = {
                    'id': crypto.sha1(str(ctx.author.id))
                }
            )

            if delete == False:
                await ctx.interaction.edit_original_message(
                    embed = discord.Embed(
                        title = 'Oops!',
                        description = 'An error ocurred deleting your from our database, please try again later.',
                        color = discord.Color.red()
                    ),
                    view = None
                )
                return

            await ctx.interaction.edit_original_message(
                embed = discord.Embed(
                    title = 'Deleted',
                    description = 'You have successfully deleted your LobbyBot account.',
                    color = discord.Color.blue()
                ),
                view = None
            )
            return

    @slash_command(
        name = 'add-bot',
        description = 'Adds an bot account'
    )
    async def add_bot(
        self,
        ctx: discord.ApplicationContext,
        code: Option(
            input_type = str,
            description = 'authorization code',
            default = 'none'
        )
    ):

        users = await self.bot.database.get_collection('users')

        result = await users.find_one(
            filter = {
                'id': crypto.sha1(str(ctx.author.id))
            }
        )

        if result == None:
            await ctx.respond(
                embed = discord.Embed(
                    title = 'Oops!',
                    description = 'Seems like you are not registered.',
                    color = discord.Color.red()
                ),
                ephemeral = True
            )
            return

        if len(result['bots']) >= self.bot.config.get('database')['max_accounts']:
            await ctx.respond(
                embed = discord.Embed(
                    title = 'Oops!',
                    description = 'You have reached the maximum of accounts saved.',
                    color = discord.Color.red()
                ),
                ephemeral = True
            )
            return

        if code == 'none':

            embed = discord.Embed(
                description = f"""
⚠️**Before logging in please note the following**
_It is possible that after some time the used account will receive a password reset, please use a **bot** account where you have access to the mail._
- Click on the `Login` button
- Login with an **bot** account (don't login on you main account)
- Copy the 32 character code
- Use this command again with your code inside the `code` parameter
""",
                color = discord.Colour.blue()
            )

            await ctx.respond(
                embed = embed,
                view = discord.ui.View(
                    discord.ui.Button(
                        style = discord.ButtonStyle.url,
                        label = 'Login',
                        url = 'https://www.epicgames.com/id/login?redirectUrl=https%3A%2F%2Fwww.epicgames.com%2Fid%2Fapi%2Fredirect%3FclientId%3D3f69e56c7649492c8cc29f1af08a8a12%26responseType%3Dcode&prompt=login'
                    )
                )
            )

        else:

            if len(code) != 32:
                await ctx.respond(
                    embed = discord.Embed(
                        title = 'Oops!',
                        description = 'The code length is invalid.',
                        color = discord.Color.red()
                    ),
                    ephemeral = True
                )

            else:

                log.debug('Adding account...')

                config = self.bot.config.get('fortnite')
                client = restclient.RestClient(
                    ios_token = config['ios_token'],
                    build = config['build'],
                    os = config['os']
                )

                request = await client.authenticate(
                    payload = {
                        'grant_type': 'authorization_code',
                        'code': code,
                        'token_type': 'eg1'
                    }
                )

                log.debug(f'authorization_code authentication received status {request.status}')

                if request.status != 200:

                    data = await request.json()
                    await ctx.respond(
                        embed = discord.Embed(
                            title = 'Oops!',
                            description = f'`{data.get("errorMessage")}`',
                            color = discord.Color.red()
                        ),
                        ephemeral = True
                    )
                
                else:

                    auth_session = await request.json()

                    log.debug(auth_session)

                    await ctx.respond(
                        embed = discord.Embed(
                            title = 'Logging in...',
                            description = f'Creating device auth for `{auth_session.get("displayName")}`...',
                            color = discord.Color.blue()
                        ),
                        ephemeral = True
                    )

                    new_device_auth = await client.create_device_auth(
                        access_token = auth_session.get('access_token'),
                        account_id = auth_session.get('account_id')
                    )

                    log.debug(f'Device auth creation received {new_device_auth.status}')

                    if new_device_auth.status != 200:

                        data = await request.json()
                        await ctx.interaction.edit_original_message(
                            embed = discord.Embed(
                                title = 'Oops!',
                                description = f'`{data.get("errorMessage")}`',
                                color = discord.Color.red()
                            )
                        )
                    
                    else:

                        data = await new_device_auth.json()

                        new_bot = utils.bot_base()
                        new_bot['added'] = int(time.time())
                        new_bot['display_name'] = crypto.encrypt_user_string(ctx.author.id, self.bot.ekey, auth_session['displayName']).decode()
                        new_bot['device_id'] = crypto.encrypt_user_string(ctx.author.id, self.bot.ekey, data['deviceId']).decode()
                        new_bot['account_id'] = crypto.encrypt_user_string(ctx.author.id, self.bot.ekey, data['accountId']).decode()
                        new_bot['secret'] = crypto.encrypt_user_string(ctx.author.id, self.bot.ekey, data['secret']).decode()

                        await users.update_one(
                            filter = {'id': crypto.sha1(str(ctx.author.id))},
                            update = {f'bots.{crypto.sha1(data["accountId"])}': new_bot}
                        )

                        await ctx.interaction.edit_original_message(
                            embed = discord.Embed(
                                title = 'Added correctly!',
                                description = f'The account {auth_session["displayName"]} was added correctly.',
                                color = discord.Color.green()
                            )
                        )

    @slash_command(
        name = 'remove-bot',
        description = 'Removes an bot'
    )
    async def remove_bot(
        self,
        ctx: discord.ApplicationContext
    ):

        users = await self.bot.database.get_collection('users')

        result = await users.find_one(
            filter = {
                'id': crypto.sha1(str(ctx.author.id))
            }
        )

        if result == None:
            await ctx.respond(
                embed = discord.Embed(
                    title = 'Oops!',
                    description = 'Seems like you are not registered.',
                    color = discord.Color.red()
                ),
                ephemeral = True
            )
            return

        if len(list(result['bots'].keys())) == 0:

            await ctx.respond(
                embed = discord.Embed(
                    title = 'Oops!',
                    description = 'You do not have any bot.',
                    color = discord.Color.red()
                ),
                ephemeral = True
            )
        
        else:

            options = []
            accounts = result['bots']
            for account in list(result['bots'].keys()):

                display_name = crypto.decrypt_user_string(ctx.author.id, self.bot.ekey, accounts[account]['display_name'])
                account_id = crypto.decrypt_user_string(ctx.author.id, self.bot.ekey, accounts[account]['account_id'])

                options.append(
                    discord.SelectOption(
                        label = display_name,
                        value = account
                    )
                )

            view = discord.ui.View(
                discord.ui.Select(
                    options = options,
                    custom_id = 'select_remove'
                ),
                timeout = 120,
                disable_on_timeout = True
            )

            await ctx.respond(
                embed = discord.Embed(
                    title = 'Remove bot',
                    description = 'Select the bot to remove',
                    color = discord.Color.blue()
                ),
                view = view
            )

            try:
                interaction = await self.bot.wait_for(
                    'interaction',
                    check = lambda i: i.user == ctx.author and i.custom_id in 'select_remove',
                    timeout = 120
                )
            except asyncio.TimeoutError:
                return

            choice = accounts[view.children[0].values[0]]

            await users.update_one(
                filter = {'id': crypto.sha1(str(ctx.author.id))},
                update = {'bots': choice},
                type = '$unset'
            )

            config = self.bot.config.get('fortnite')
            client = restclient.RestClient(
                ios_token = config['ios_token'],
                build = config['build'],
                os = config['os']
            )

            account_id = crypto.decrypt_user_string(ctx.author.id, self.bot.ekey, choice['account_id'])
            device_id = crypto.decrypt_user_string(ctx.author.id, self.bot.ekey, choice['device_id'])

            request = await client.authenticate(
                payload = {
                    'grant_type': 'device_auth',
                    'account_id': account_id,
                    'device_id': device_id,
                    'secret': crypto.decrypt_user_string(ctx.author.id, self.bot.ekey, choice['secret']),
                    'token_type': 'eg1'
                }
            )

            if request.status != 200:

                await ctx.interaction.edit_original_message(
                    embed = discord.Embed(
                        title = 'Remove bot',
                        description = 'The bot credentials were removed from database correctly, credentials were invalid.',
                        color = discord.Color.blue()
                    ),
                    view = None
                )
            
            else:

                auth_session = await request.json()

                log.debug(auth_session)

                delete = await client.delete_device_auth(
                    access_token = auth_session.get('access_token'),
                    account_id = auth_session.get('account_id'),
                    device_id = device_id
                )

                if delete.status != 204:
                    
                    await ctx.interaction.edit_original_message(
                        embed = discord.Embed(
                            title = 'Removed bot',
                            description = 'The bot credentials were removed from database but may still valid, change the account password to kill these credentials.',
                            color = discord.Color.blue()
                        ),
                        view = None
                    )

                else:

                    await ctx.interaction.edit_original_message(
                        embed = discord.Embed(
                            title = 'Removed bot',
                            description = 'The bot credentials were removed from database correctly',
                            color = discord.Color.blue()
                        ),
                        view = None
                    )

def setup(bot: discord.Bot):
    bot.add_cog(Account(bot))
