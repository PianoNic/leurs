import discord
from discord.ext import commands
import random
import datetime
from database import db

class GamblingCog(commands.Cog):
    def __init__(self, client):
        self.client = client
    
    async def open_account(self, user):
        """Create a bank account for a user if they don't have one."""
        user_id = user.id
        
        # Check if user already has an account
        account = await self.get_account(user_id)
        if account:
            return False
        
        # Create new account with default values
        await db.execute('''
            INSERT INTO bank_accounts (user_id, wallet, bank) 
            VALUES ($1, $2, $3)
            ON CONFLICT (user_id) DO NOTHING
        ''', user_id, 50, 0)
        
        return True
    
    async def get_account(self, user_id):
        """Get a user's bank account data."""
        account = await db.fetchrow('''
            SELECT * FROM bank_accounts WHERE user_id = $1
        ''', user_id)
        
        if account:
            return dict(account)
        return None
    
    @commands.command()
    async def gamble(self, ctx, amount=None):
        await self.open_account(ctx.author)
        account = await self.get_account(ctx.author.id)
        
        if amount is None:
            embed = discord.Embed(
                title="Error",
                description="Please specify an amount to gamble",
                color=discord.Color.red()
            )
            await ctx.send(embed=embed)
            return
            
        if amount == "all":
            amount = account["wallet"]
        elif isinstance(amount, str) and "%" in amount:
            try:
                percentage = int(amount.replace("%", ""))
                if percentage <= 0 or percentage > 100:
                    raise ValueError
                amount = int(account["wallet"] * (percentage / 100))
            except ValueError:
                embed = discord.Embed(
                    title="Error",
                    description="Please enter a valid percentage between 1% and 100%",
                    color=discord.Color.red()
                )
                await ctx.send(embed=embed)
                return
        else:
            try:
                amount = int(amount)
            except ValueError:
                embed = discord.Embed(
                    title="Error",
                    description="Please enter a valid number, percentage, or 'all'",
                    color=discord.Color.red()
                )
                await ctx.send(embed=embed)
                return
        
        wallet_amt = account["wallet"]
        
        if amount <= 0:
            embed = discord.Embed(
                title="Error",
                description="Amount must be positive!",
                color=discord.Color.red()
            )
            await ctx.send(embed=embed)
            return
            
        if amount > wallet_amt:
            embed = discord.Embed(
                title="Error",
                description="You don't have enough coins!",
                color=discord.Color.red()
            )
            await ctx.send(embed=embed)
            return
        
        # Coin flip - heads or tails
        result = "heads" if random.randint(1, 2) == 1 else "tails"
        win = result == "heads"  # Win on heads, lose on tails
        
        # Update balance in database
        if win:
            await db.execute('''
                UPDATE bank_accounts 
                SET wallet = wallet + $1
                WHERE user_id = $2
            ''', amount, ctx.author.id)
            
            color = discord.Color.green()
            title = "You Won!"
            description = f"The coin landed on **{result}**! You won **{amount} coins**!"
        else:
            await db.execute('''
                UPDATE bank_accounts 
                SET wallet = wallet - $1
                WHERE user_id = $2
            ''', amount, ctx.author.id)
            
            color = discord.Color.red()
            title = "You Lost!"
            description = f"The coin landed on **{result}**! You lost **{amount} coins**!"
        
        # Get updated balance
        new_balance = await db.fetchval('''
            SELECT wallet FROM bank_accounts 
            WHERE user_id = $1
        ''', ctx.author.id)
        
        # Create and send embed
        embed = discord.Embed(
            title=title,
            description=description,
            color=color
        )
        
        embed.add_field(
            name="New Balance", 
            value=f"{new_balance} coins",
            inline=False
        )
        
        embed.set_footer(text=f"Requested by {ctx.author.name}", icon_url=ctx.author.avatar.url if ctx.author.avatar else ctx.author.default_avatar.url)
        embed.timestamp = datetime.datetime.utcnow()
        
        await ctx.send(embed=embed)

async def setup(client):
    await client.add_cog(GamblingCog(client))