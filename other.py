import discord
from discord.ext import commands
import random
import os

class OtherCog(commands.Cog):
    def __init__(self, client):
        self.client = client
    
    @commands.command()
    async def code(self, ctx):
        await ctx.send("zgte5dr6ftgzhujikokztrdeswa536edfr65fm ,WU83 34 FTZFTBFTBF7677U6")
    
    @commands.command()
    async def geschichte(self, ctx):
        await ctx.send("ich habe mal david in migros getroffen und ein foto mit david gemacht. das hat mich glücklich gemacht. dann hatten wir französisch...")
    
    @commands.command()
    async def david(self, ctx):
        random_num_david = random.randint(1, 20)
        jpeg_path = f"images/david/{random_num_david}.jpeg"
        gif_path = f"images/david/{random_num_david}.gif"
        
        if os.path.exists(jpeg_path):
            file = discord.File(jpeg_path)
        elif os.path.exists(gif_path):
            file = discord.File(gif_path)
        else:
            await ctx.send("Couldn't find image for David")
            return
            
        await ctx.send(file=file)
    
    @commands.command()
    async def opl(self, ctx):
        await ctx.send("https://habenwirmorgenopl.info (might be down)")
    
    @commands.command()
    async def dsl(self, ctx):
        await ctx.send("https://habenwirmorgenopl.info (might be down)")
    
    @commands.command()
    async def ppl(self, ctx):
        await ctx.send("https://habenwirmorgenopl.info (might be down)")
    
    @commands.command()
    async def hwmo(self, ctx):
        await ctx.send("https://habenwirmorgenopl.info (might be down)")