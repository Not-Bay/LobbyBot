from discord.ext import commands
from discord_components import *
import datetime
import asyncio
import discord
import util
import json
import io

from util import log
from modules import auth
from modules import client

AUTHORIZATION_CODE_URL = "https://www.epicgames.com/id/login?redirectUrl=https%3A%2F%2Fwww.epicgames.com%2Fid%2Fapi%2Fredirect%3FclientId%3D3446cd72694c4a4485d81b77adbb2141%26responseType%3Dcode&prompt=loginhttps://www.epicgames.com/id/login?redirectUrl=https%3A%2F%2Fwww.epicgames.com%2Fid%2Fapi%2Fredirect%3FclientId%3D3446cd72694c4a4485d81b77adbb2141%26responseType%3Dcode&prompt=login"
AUTHORIZATION_CODE_EXAMPLE_IMAGE = "https://media.discordapp.net/attachments/838192486547324938/855203089887133757/authorizationcode.png"

class Custom(commands.Cog):

    def __init__(self, bot):
        self.bot = bot

    @commands.command(usage='account', aliases=['profile'])
    @commands.cooldown(4, 8, commands.BucketType.user)
    async def account(self, ctx):
        """
        Shows your LobbyBot account, premium status and saved account info with some options to manage it
        """

        user = util.database.users.find_one({'user_id': ctx.author.id})

        if user == None:

            buttons = [
                Button(style=ButtonStyle.green, label='Register', custom_id='USR_REGISTER'),
                Button(style=ButtonStyle.red, label='Cancel', custom_id='MSG_CANCEL')
            ]
            embed = discord.Embed(
                description = 'You are not registered in database yet. Click `Register` to do it now',
                color = 0x349eeb
            )
            await ctx.send(embed=embed, components=buttons)


        else:

            embed = discord.Embed(
                title = 'Your LobbyBot account',
                color = 0x349eeb
            )
            embed.add_field(name='Premium', value=f'<:yes:816337064130904105> Since {datetime.datetime.fromtimestamp(int(user["premium_since"])).strftime("%d/%m/%Y")}' if user['premium'] == True else '<:no:816337113968279612>', inline=False)
            embed.add_field(name='Custom account', value=f'<:yes:816337064130904105> **{user["custom_account"]["display_name"]}**' if user['custom_account']['configurated'] == True else '<:no:816337113968279612> Not yet configured', inline=False)
            embed.set_thumbnail(url=ctx.author.avatar_url)

            buttons = []

            if user['custom_account']['configurated'] == True:
                buttons.append(Button(style=ButtonStyle.blue, label='Remove saved account', custom_id='USR_REMOVE_CUSTOM'))
            else:
                buttons.append(Button(style=ButtonStyle.blue, label='Add bot account', custom_id='USR_ADD_CUSTOM'))

            buttons.append(Button(style=ButtonStyle.gray, label='Request copy of my data', custom_id='USR_DATA_REQUEST'))
            buttons.append(Button(style=ButtonStyle.red, label='Delete my LobbyBot account', custom_id='USR_ACCOUNT_DELETE'))

            await ctx.send(embed=embed, components=buttons)

    @commands.command(usage='startcustom')
    @commands.cooldown(4, 8, commands.BucketType.user)
    async def startcustom(self, ctx):
        """
        Let you start a bot using your own account
        """

        user = util.database.users.find_one({"user_id": ctx.author.id})

        if user == None:
            await ctx.invoke(self.bot.get_command('account'))
            return

        if isinstance(ctx.message.guild, discord.Guild):
            guild = util.database.guilds.find_one({"guild_id": ctx.guild.id})
            if guild['lb_channel'] != None:
                if ctx.channel.id != guild['lb_channel']:

                    await ctx.send(embed=discord.Embed(
                        description = f'This command can only be used in <#{guild["lb_channel"]}>',
                        color = 0xff2929
                    ))
                    return

        if util.allow_new_custom_sessions == False:

            await ctx.send(embed=discord.Embed(
                description = 'This function is temporarily disabled',
                color = 0xff2929
            ))
            return

        for session in util.active_sessions:
            if session.ctx.author.id == ctx.author.id:
                await ctx.send(embed=discord.Embed(
                    description = 'You already have an bot active',
                    color = 0xff2929
                ))
                return

        if user['custom_account']['configurated'] == False:

            await ctx.send(embed=discord.Embed(
                title = 'Start custom',
                description = f'You do not have any account saved yet.\n- Login on Epic Games with the account to use as bot (do not use your account) in [this link]({AUTHORIZATION_CODE_URL})\n- Copy the 32 character code from the data\n- Use this command again with the code as argument `!startcustom <32 character code>`\n**Preferably do it in bot dms**',
                color = 0x349eeb
            ).set_footer(text='Once you have done this you will not have to do it again. You can delete the saved login with !removecustom').set_image(url=AUTHORIZATION_CODE_EXAMPLE_IMAGE))
            return

        else:

            account = user['custom_account']

            msg = await ctx.send(embed=discord.Embed(
                title = 'Start custom',
                description = '<a:loading:815646116154310666> Starting...',
                color = 0x349eeb
            ))

            session = client.Session(ctx, account, util.gen_id(), custom=True)
            util.active_sessions.append(session)

            start_result = await session.start_client()
            if start_result != True:
                await msg.edit(embed=discord.Embed(
                    description = f'An error occurred while starting your bot. Error:\n{f"`{start_result}"}`',
                    color = 0xff2929
                ).set_footer(text='Note: If it does not work after a few tries try removing and re-adding the account with !removecustom'))
                await session.stop_client()
                return

            embed = discord.Embed(
                title = 'Your custom lobby bot',
                description = f'**Name:** {session.client.user.display_name}\n**ID:** {session.client.user.id}',
                color = 0x349eeb
            )
            await msg.edit(embed=embed)
            try:
                cosmetic = await session.client.cosmetics.get('outfit', id_=session.client.defaultoutfit)
                embed.set_thumbnail(url=cosmetic['images']['icon'])
            except:
                pass
            embed.set_author(name=f'Session {session._id}')
            await msg.edit(embed=embed)

            session._handle_messages_task = asyncio.create_task(session.handle_messages())

    @commands.command(usage='removecustom')
    @commands.cooldown(4, 8, commands.BucketType.user)
    async def removecustom(self, ctx):
        """
        (Deprecated, use !account instead) If you have an saved custom account it will remove it (deleting created device auths and auth sessions)
        """

        user = util.database.users.find_one({"user_id": ctx.author.id})

        if user == None:
            await ctx.invoke(self.bot.get_command('account'))
            return

        if user['custom_account']['configurated'] == True:

            for session in util.active_sessions:
                if session.ctx.author.id == ctx.author.id:
                    if session.is_custom == True:
                        await ctx.send(embed=discord.Embed(
                            description = 'Your custom account is active. Use `!stop` and try again',
                            color = 0xff2929
                        ))
                        return
                    else:
                        break

            components = [
                Button(style=ButtonStyle.green, label='Confirm'),
                Button(style=ButtonStyle.red, label='Cancel')
            ]

            msg = await ctx.send(embed=discord.Embed(
                description = f'You have a saved login for **{user["custom_account"]["display_name"]}**\nAre you sure you want to remove it?',
                color = 0x349eeb
            ).set_footer(text='The generated device auths will be removed and deleted from the database'), components=components)

            def check(interaction):
                return ctx.author == interaction.author and interaction.channel == ctx.channel

            try:
                result = await self.bot.wait_for('button_click', timeout=300, check=check)

                if result.component.label == 'Confirm':

                    AUTH = auth.DeviceAuths()
                    data = await AUTH.authenticate(user['custom_account'])
                    delete = await AUTH.delete_device_auths(user['custom_account']['device_id'], user['custom_account']['account_id'], data)
                    await AUTH.kill_auth_session(data)
                    util.database.users.find_one_and_update({"user_id": ctx.author.id}, {"$set": {"custom_account": util.custom_account_base()}})

                    await result.respond(
                        type=InteractionType.UpdateMessage,
                        embed=discord.Embed(
                            description = f'Account **{user["custom_account"]["display_name"]}** removed successfully!',
                            color = 0x349eeb
                        ),
                        components=[]
                    )
                        
                    return

                else:

                    await result.respond(
                        type=InteractionType.UpdateMessage,
                        embed=discord.Embed(
                            description = 'Canceled',
                            color = 0xff2929
                        ),
                        components=[]
                    )
                    return

            except asyncio.TimeoutError:
                await msg.edit(
                    embed=discord.Embed(
                        description = 'Canceled by timeout',
                        color = 0xff2929
                    ),
                    components=[]
                )
                return


def setup(bot):
    bot.add_cog(Custom(bot))