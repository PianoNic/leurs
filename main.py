import discord
from discord.ext import commands
import os
from dotenv import load_dotenv
import random

from economy import EconomyCog
from gambling import GamblingCog
from other import OtherCog
from jobs import JobMarketCog

os.chdir(os.path.dirname(os.path.abspath(__file__)))

intents = discord.Intents.default()
intents.message_content = True

client = commands.Bot(command_prefix='-', intents=intents)

@client.event
async def on_command_error(ctx, error):
    if ctx.channel.id != 1172476424704237589:
        embed = discord.Embed(
            title="Wrong Channel",
            description="Please use the bot in the designated bot channel.",
            color=discord.Color.red()
        )
        await ctx.message.delete()
        await ctx.send(embed=embed, delete_after=1.5)
        return
        
    if isinstance(error, commands.CommandNotFound):
        embed = discord.Embed(
            title="Error",
            description=f"Command `{ctx.invoked_with}` not found. Please use a valid command.",
            color=discord.Color.red()
        )
        await ctx.send(embed=embed)

@client.check
async def global_check(ctx):
    if ctx.channel.id != 1172476424704237589:
        embed = discord.Embed(
            title="Wrong Channel",
            description="Please use the bot in the designated bot channel.",
            color=discord.Color.red()
        )
        await ctx.message.delete()
        await ctx.send(embed=embed, delete_after=1.5)
        return False
    return True

@client.event
async def on_ready():
    print('Bot is ready.')

async def setup():
    await client.add_cog(EconomyCog(client))
    await client.add_cog(GamblingCog(client))
    await client.add_cog(OtherCog(client))
    await client.add_cog(JobMarketCog(client))

if __name__ == "__main__":
    load_dotenv()
    token = os.getenv('bot_token')
    
    if token:
        import asyncio
        asyncio.run(setup())
        client.run(token)
    else:
        print("Error: Bot token not found.")