from discord.ext import commands
import traceback
import asyncio
import discord
import util

class Settings(commands.Cog):

    def __init__(self, bot):
        self.bot = bot

    @commands.command(usage='channel [channel mention]')
    @commands.has_permissions(administrator=True)
    @commands.guild_only()
    async def channel(self, ctx, newchannel=None):
        """
        Changes the command channel of the bot. You need to have administrator permissions
        """

        guild = util.database.guilds.find_one({"guild_id": ctx.guild.id})

        if newchannel != None:
            try:
                selected_chan_int = int(newchannel.strip('<># '))
                selected_channel = self.bot.get_channel(selected_chan_int)
                if selected_channel != None:
                    if selected_channel.guild != ctx.guild:
                        await ctx.send(embed=discord.Embed(
                            description = f'The mentioned channel is not valid or i don\'t have access to it',
                            color = 0xff2929
                        ))
                        return
                    util.update_guild(ctx.guild, 'lb_channel', selected_channel.id)
                    await ctx.send(embed=discord.Embed(
                        description = f'Successfully set <#{selected_channel.id}> as bot commands channel',
                        color = 0x349eeb
                    ))
                    return
                else:
                    await ctx.send(embed=discord.Embed(
                        description = f'The mentioned channel is not valid or i don\'t have access to it',
                        color = 0xff2929
                    ))
                    return

            except discord.errors.Forbidden:
                await ctx.send(embed=discord.Embed(
                    description = f'I don\'t have access to the mentioned channel',
                    color = 0xff2929
                ))
                return

            except ValueError:
                await ctx.send(embed=discord.Embed(
                    description = f'Invalid channel. You must enter only the mention/id of the channel.',
                    color = 0xff2929
                ))
                return
            except Exception as e:
                await ctx.send(embed=discord.Embed(
                    description = f'Could not configure selected channel: {e}',
                    color = 0xff2929
                ))
                return

        else:

            if guild["lb_channel"] == None:
                config_str = 'Commands channel are not configured yet. Send the ID or mention of the channel to use.'
            else:
                config_str = f'The current commands channel is <#{guild["lb_channel"]}>. Send the ID or mention of the new channel to use or type `disable` to disable it'

            def check(message):
                return message.author.id == ctx.author.id and message.channel.id == ctx.channel.id

            msg = await ctx.send(embed=discord.Embed(
                description = f'{config_str}',
                color = discord.Colour.orange()
            ).set_footer(text='Type "cancel" to cancel'))
            try:
                usr_msg = await self.bot.wait_for('message', check=check, timeout=300)
                msg_content= usr_msg.content

                if msg_content.lower() == 'cancel':

                    await msg.edit(embed=discord.Embed(
                        description = f'Canceled',
                        color = 0xff2929
                    ))
                    return

                if msg_content.lower() == 'disable':

                    util.update_guild(ctx.guild, 'lb_channel', None)
                    await msg.edit(embed=discord.Embed(
                        description = f'Bot commands channel disabled',
                        color = 0x349eeb
                    ))
                    return

                try:
                    selected_chan_int = int(msg_content.strip('<># '))
                    selected_channel = self.bot.get_channel(selected_chan_int)
                    if selected_channel != None:
                        if selected_channel.guild != ctx.guild:
                            await ctx.send(embed=discord.Embed(
                                description = f'The mentioned channel is not valid or i don\'t have access to it',
                                color = 0xff2929
                            ))
                            return
                        util.update_guild(ctx.guild, 'lb_channel', selected_channel.id)
                        await msg.edit(embed=discord.Embed(
                            description = f'Successfully set <#{selected_channel.id}> as bot commands channel',
                            color = 0x349eeb
                        ))
                    else:
                        await ctx.send(embed=discord.Embed(
                            description = f'The mentioned channel is not valid or i do not have access to it',
                            color = 0xff2929
                        ))
                        return
                except Exception:
                    await msg.edit(embed=discord.Embed(
                        description = f'Could not configure selected channel: {traceback.format_exc()}',
                        color = 0xff2929
                    ))
                    return

            except asyncio.TimeoutError:

                await msg.edit(embed=discord.Embed(
                    description = 'Canceled by timeout',
                    color = 0xff2929
                ))
                return

    @commands.command(usage='prefix <new prefix>')
    @commands.has_permissions(administrator=True)
    @commands.guild_only()
    async def prefix(self, ctx, newprefix=None):
        """
        Changes the prefix of the bot. You need to have administrator permissions
        """

        guild = util.database.guilds.find_one({"guild_id": ctx.guild.id})

        if newprefix != None:

            if newprefix == guild['prefix']:

                await ctx.send(embed=discord.Embed(
                    description = 'The prefix must be different than the current',
                    color = 0xff2929
                ))
                return

            else:
                newprefix.strip(' ')
                util.update_guild(ctx.guild, 'prefix', newprefix)

                await ctx.send(embed=discord.Embed(
                    description = f'Prefix changed to: {newprefix}',
                    color = discord.Colour.green()
                ))
                return

        else:

            def check(message):
                return message.author.id == ctx.author.id and message.channel.id == ctx.channel.id

            msg = await ctx.send(embed=discord.Embed(
                description = 'Send the new prefix to use',
                color = discord.Colour.orange()
            ).set_footer(text='Type "cancel" to cancel'))

            try:
                result = await self.bot.wait_for('message', check=check, timeout=300)

                newprefix = result.content
                newprefix.strip(' ')

                if newprefix == 'cancel':
                    await ctx.send(embed=discord.Embed(
                        description = f'Canceled',
                        color = 0xff2929
                    ))
                    return

                util.update_guild(ctx.guild, 'prefix', newprefix)

                await ctx.send(embed=discord.Embed(
                    description = f'Prefix changed to: {newprefix}',
                    color = discord.Colour.green()
                ))
                return

            except asyncio.TimeoutError:

                await msg.edit(embed=discord.Embed(
                    description = 'Canceled by timeout',
                    color = 0xff2929
                ))
                return


def setup(bot):
    bot.add_cog(Settings(bot))