from discord.ext import commands
from discord_components import *
import time
import logging
import asyncio
import random
import requests
import discord
import math
import util

from modules import client

class Commands(commands.Cog):

    def __init__(self, bot):
        self.bot = bot


    @commands.command(usage='help [command]')
    @commands.cooldown(4, 8, commands.BucketType.user)
    async def help(self, ctx, command_=None):
        """
        Shows the commands of the bot. Shows info about a command adding it as argument
        """

        if command_ == None:

            prefix = util.get_prefix(self.bot, ctx.message)

            commands_list = ['start', 'stop', 'invite', 'channel', 'prefix', 'help']
            custom_lb_list = ['startcustom', 'removecustom', 'account']

            general_cmds_str = ''
            for command in commands_list:
                try:
                    cmd = self.bot.get_command(command)
                    general_cmds_str += f'`{prefix}{cmd.usage}`' + '\n'
                except:
                    continue

            custom_cmds_str = ''
            for command in custom_lb_list:
                try:
                    cmd = self.bot.get_command(command)
                    custom_cmds_str += f'`{prefix}{cmd.usage}`' + '\n'
                except:
                    continue

            tempbots_cmds_str = 'At the moment you can only find them at the [support server](https://discord.gg/YJ8wK9H)'

            embed = discord.Embed(
                title = 'Help',
                description = f'Use `{prefix}help <command>` to see more info about a command.',
                color = 0x349eeb
            )
            embed.add_field(name='Commands:', value=general_cmds_str, inline=False)
            embed.add_field(name='Custom LobbyBot commands:', value=custom_cmds_str, inline=False)
            embed.add_field(name='Fortnite commands:', value=tempbots_cmds_str, inline=False)

            embed.set_footer(text=f'Made by Bay#7210')
            embed.set_thumbnail(url='https://cdn.discordapp.com/avatars/761360995117170748/02c9a2ba3b4cafed2d05c690f9ea3bdb.webp')

            components = [
                Button(style=ButtonStyle.URL, label='Support Server', url='https://discord.gg/YJ8wK9H')
            ]

            await ctx.send(embed=embed, components=components)
            return
        
        else:

            cmd = self.bot.get_command(command_)

            if cmd == None:

                await ctx.send(embed=discord.Embed(
                    description = 'That command was not found',
                    color = 0xff2929
                ))
                return

            else:

                prefix = util.get_prefix(self.bot, ctx.message)

                aliases_str = ''
                for alias in cmd.aliases:
                    aliases_str += f'`{alias}` '

                if aliases_str == '':
                    aliases_str = 'There\'s no aliases'

                embed = discord.Embed(
                    title = 'Help',
                    description = f'Command `{prefix}{cmd.name}`:',
                    color = 0x349eeb
                )
                embed.add_field(name='Description:', value=f'{cmd.help}', inline=False)
                embed.add_field(name='Usage:', value=f'{prefix}{cmd.usage}', inline=False)
                embed.add_field(name='Aliases:', value=aliases_str, inline=False)

                embed.set_thumbnail(url='https://cdn.discordapp.com/avatars/761360995117170748/02c9a2ba3b4cafed2d05c690f9ea3bdb.webp')

                await ctx.send(embed=embed)

    
    @commands.command(aliases=['startbot'], usage='start')
    @commands.cooldown(2, 10, commands.BucketType.user)
    async def start(self, ctx):
        """
        Starts a temporary lobby bot
        """

        if isinstance(ctx.message.guild, discord.Guild):
            guild = util.database.guilds.find_one({"guild_id": ctx.guild.id})
            if guild['lb_channel'] != None:
                if ctx.channel.id != guild['lb_channel']:

                    await ctx.send(embed=discord.Embed(
                        description = f'This command can only be used in <#{guild["lb_channel"]}>',
                        color = 0xff2929
                    ))
                    return

        if util.allow_new_sessions == False:

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

        msg = await ctx.send(embed=discord.Embed(
            title = 'Loading <a:loading:815646116154310666>',
            color = 0x349eeb
        ))

        accounts = list(util.database.credentials.find({"active": False, "glitched": False}))

        if len(accounts) == 0:
            await msg.edit(embed=discord.Embed(
                description = 'There are no bots to use at this time. Try again later',
                color = 0xff2929
            ))
            return

        account = random.choice(accounts)

        session = client.Session(ctx, account, util.gen_id())
        util.active_sessions.append(session)

        start_result = await session.start_client()
        if start_result != True:
            await msg.edit(embed=discord.Embed(
                description = f'An error occurred while starting your bot. Error:\n{f"`{start_result}"}`',
                color = 0xff2929
            ))
            await session.stop_client()
            util.discord_log('Unable to start an account\n' + f'{session.account["display_name"]}: `{start_result}`')
            util.database.credentials.find_one_and_update({"display_name": account["display_name"]}, {"$set": {"glitched": True}})
            return

        embed = discord.Embed(
            title = 'Your Lobby Bot',
            description = f'**Name:** {session.client.user.display_name}\n**ID:** {session.client.user.id}',
            color = 0x349eeb
        )
        try:
            cosmetic = await session.client.cosmetics.get('outfit', id_=session.client.defaultoutfit)
            embed.set_thumbnail(url=cosmetic['images']['icon'])
        except:
            pass
        embed.set_author(name=f'Session {session._id}')
        await msg.edit(embed=embed)

        session._handle_messages_task = asyncio.create_task(session.handle_messages())


    @commands.command(aliases=['logout'], usage='stop')
    @commands.cooldown(2, 15, commands.BucketType.user)
    async def stop(self, ctx):
        """
        Stop of your current active bot
        """

        flag = False

        for session in util.active_sessions:
            if session.ctx.author.id == ctx.author.id:
                flag = True

                author_txt = f'{session.client.user.display_name} - {session._id}'
                asyncio.create_task(session.stop_client())

                try:
                    util.active_sessions.remove(session)
                except:
                    pass
                try:
                    util.used_ids.remove(session._id)
                except:
                    pass
                util.database.credentials.find_one_and_update({"display_name": session.account["display_name"]}, {"$set": {"active": False}})
                session._handle_messages_task.cancel()
                break

        
        if flag == True:
            await ctx.send(embed=discord.Embed(
                description = 'Finished session.',
                color = 0x349eeb
            ).set_author(name=author_txt))

        else:
            await ctx.send(embed=discord.Embed(
                description = 'You not have an session to stop',
                color = 0xff2929
            ))


    @commands.command(aliases=['invitation'], usage='invite')
    @commands.cooldown(2, 5.4, commands.BucketType.user)
    async def invite(self, ctx):
        """
        Sends you the invite of the bot
        """

        await ctx.send(embed=discord.Embed(
            description = f'[Click here]({util.get_config()["invite"]}) to invite this bot to your server',
            color = 0x349eeb
        ))


def setup(bot):
    bot.add_cog(Commands(bot))