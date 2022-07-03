from discord.commands import slash_command, Option, OptionChoice, SlashCommandGroup
from discord.ext import commands
import logging
import discord
import time

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
                'user_id': ctx.author.id
            }
        )

        if result != None:
            await ctx.respond(
                embed = discord.Embed(
                    title = 'Oops!',
                    description = 'Seems like you are already registered.',
                    color = discord.Color.red()
                ),
                ephemeral = True
            )
            return

        insert = await users.insert_one(
            document = {
                'user_id': ctx.author.id,
                'added': int(time.time()),
                'banned': False
            }
        )

        if insert == False:
            await ctx.respond(
                embed = discord.Embed(
                    title = 'Oops!',
                    description = 'An error ocurred registering, please try again later.',
                    color = discord.Color.red()
                ),
                ephemeral = True
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
                'user_id': ctx.author.id
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

        # to-do: confirm delete with view

        delete = await users.delete_one( 
            filter = {
                'user_id': ctx.author.id
            }
        )

        if delete == False:
            await ctx.respond(
                embed = discord.Embed(
                    title = 'Oops!',
                    description = 'An error ocurred deleting your from our database, please try again later.',
                    color = discord.Color.red()
                ),
                ephemeral = True
            )
            return

        await ctx.respond(
            embed = discord.Embed(
                title = 'Deleted',
                description = 'You have successfully deleted your LobbyBot account.',
                color = discord.Color.blue()
            )
        )
        return


def setup(bot: discord.Bot):
    bot.add_cog(Account(bot))
