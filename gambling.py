import discord
from discord.ext import commands
import random
import json
import os

class GamblingCog(commands.Cog):
    def __init__(self, client):
        self.client = client
    
    async def get_bank_data(self):
        if not os.path.exists('data'):
            os.makedirs('data')
        
        if not os.path.exists('data/bank.json'):
            with open('data/bank.json', 'w') as f:
                json.dump({}, f)

        with open('data/bank.json', 'r') as f:
            content = f.read().strip()
            if not content:
                users = {}
            else:
                try:
                    users = json.loads(content)
                except json.JSONDecodeError:
                    users = {}
            
        if not content:
            with open('data/bank.json', 'w') as f:
                json.dump(users, f)
                
        return users
    
    async def open_account(self, user):
        users = await self.get_bank_data()

        if str(user.id) in users:
            return False
        else:
            users[str(user.id)] = {}
            users[str(user.id)]["wallet"] = 0
            users[str(user.id)]["bank"] = 0

        with open('data/bank.json', 'w') as f:
            json.dump(users, f)
        return True
    
    @commands.command()
    async def gamble(self, ctx, amount: int = None):
        await self.open_account(ctx.author)
        
        if amount is None:
            await ctx.send("Please specify an amount to gamble!")
            return
        
        users = await self.get_bank_data()
        user = ctx.author
        
        wallet_amt = users[str(user.id)]["wallet"]
        
        if amount > wallet_amt:
            await ctx.send("You don't have enough coins!")
            return
        if amount <= 0:
            await ctx.send("Amount must be positive!")
            return
            
        if random.randint(1, 2) == 1:
            users[str(user.id)]["wallet"] += amount
            await ctx.send(f"You won {amount} coins! Your new balance: {users[str(user.id)]['wallet']}")
        else:
            users[str(user.id)]["wallet"] -= amount
            await ctx.send(f"You lost {amount} coins! Your new balance: {users[str(user.id)]['wallet']}")
            
        with open('data/bank.json', 'w') as f:
            json.dump(users, f)