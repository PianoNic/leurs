import discord
from discord.ext import commands
import os
import json
import random
from dotenv import load_dotenv

# directory to the current file location
os.chdir(os.path.dirname(os.path.abspath(__file__)))

intents = discord.Intents.default()
intents.message_content = True  # Enable message content intent for commands to work

# Add intents parameter to Bot constructor
client = commands.Bot(command_prefix='-', intents=intents)

@client.event
async def on_ready():
    print('Bot is ready.')

@client.command()
async def balance(ctx):
    await open_account(ctx.author)
    user = ctx.author
    users = await get_bank_data()

    wallet_amt = users[str(ctx.author.id)]["wallet"]
    bank_amt = users[str(ctx.author.id)]["bank"]

    em = discord.Embed(title=f"{ctx.author.name}'s balance", color=discord.Color.red())
    em.add_field(name="Wallet balance", value=wallet_amt)
    em.add_field(name="Bank balance", value=bank_amt)
    await ctx.send(embed=em)

@client.command()
async def beg(ctx):
    await open_account(ctx.author)

    users = await get_bank_data()

    user = ctx.author

    earnings = random.randrange(101)  # amount the user gets for -beg = max 101

    await ctx.send(f"Diddy gave you {earnings} coins!!")

    users[str(ctx.author.id)]["wallet"] += earnings  # used for changing wallet amount

    with open('data/bank.json', 'w') as f:
        json.dump(users, f)

async def open_account(user):
    users = await get_bank_data()

    if str(user.id) in users:
        return False
    else:
        users[str(user.id)] = {}
        users[str(user.id)]["wallet"] = 0  # starting balance
        users[str(user.id)]["bank"] = 0

    with open('data/bank.json', 'w') as f:  # opens account for new user
        json.dump(users, f)
    return True

async def get_bank_data():
    # Ensure the data directory exists
    if not os.path.exists('data'):
        os.makedirs('data')
    
    # Ensure the bank.json file exists and is properly initialized
    if not os.path.exists('data/bank.json'):
        with open('data/bank.json', 'w') as f:
            json.dump({}, f)  # Initialize with empty JSON object

    with open('data/bank.json', 'r') as f:
        content = f.read().strip()
        if not content:  # Handle empty file case
            users = {}
        else:
            try:
                users = json.loads(content)
            except json.JSONDecodeError:
                # If file is corrupted, reset it
                users = {}
        
    # Always write back valid data if we had to fix anything
    if not content:
        with open('data/bank.json', 'w') as f:
            json.dump(users, f)
            
    return users

@client.command()
async def code(ctx):
    await ctx.send("zgte5dr6ftgzhujikokztrdeswa536edfr65fm ,WU83 34 FTZFTBFTBF7677U6")

@client.command()
async def geschichte(ctx):
    await ctx.send("ich habe mal david in migros getroffen und ein foto mit david gemacht. das hat mich glücklich gemacht. dann hatten wir französisch...")

@client.command()
async def david(ctx):
    random_num_david = random.randint(1, 20)
    jpeg_path = f"images/david/{random_num_david}.jpeg"
    gif_path = f"images/david/{random_num_david}.gif"
    
    if os.path.exists(jpeg_path):
        file = discord.File(jpeg_path)
    elif os.path.exists(gif_path):
        file = discord.File(gif_path)
    else:
        # Fallback if neither exists
        await ctx.send("Couldn't find image for David")
        return
        
    await ctx.send(file=file)

@client.command()
async def opl(ctx):
    await ctx.send("https://habenwirmorgenopl.info (might be down)")

@client.command()
async def dsl(ctx):
    await ctx.send("https://habenwirmorgenopl.info (might be down)")


@client.command()
async def ppl(ctx):
    await ctx.send("https://habenwirmorgenopl.info (might be down)")


@client.command()
async def hwmo(ctx):
    await ctx.send("https://habenwirmorgenopl.info (might be down)")


if __name__ == "__main__":
    load_dotenv()  # Load variables from .env file
    token = os.getenv('bot_token')
    
    if token:
        client.run(token)
    else:
        print("Error: Bot token not found. Please set the bot_token in your .env file.")