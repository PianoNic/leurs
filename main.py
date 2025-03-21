import discord
from discord.ext import commands
import os
from dotenv import load_dotenv

from economy import EconomyCog
from gambling import GamblingCog
from other import OtherCog

os.chdir(os.path.dirname(os.path.abspath(__file__)))

intents = discord.Intents.default()
intents.message_content = True

client = commands.Bot(command_prefix='-', intents=intents)

@client.event
async def on_ready():
    print('Bot is ready.')

async def setup():
    await client.add_cog(EconomyCog(client))
    await client.add_cog(GamblingCog(client))
    await client.add_cog(OtherCog(client))

if __name__ == "__main__":
    load_dotenv()
    token = os.getenv('bot_token')
    
    if token:
        import asyncio
        asyncio.run(setup())
        client.run(token)
    else:
        print("Error: Bot token not found. Please set the bot_token in your .env file.")