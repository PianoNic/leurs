import discord
from discord.ext import commands
import random
import os
import asyncio
from discord.ext.commands import has_permissions

class AdminCog(commands.Cog):
    def __init__(self, client):
        self.client = client

    @commands.command()
    @has_permissions(administrator=True)
    async def ban(self, ctx, member: discord.Member, *, reason=None):
        """Ban a member from the server"""
        try:
            await member.ban(reason=reason)
            embed = discord.Embed(
                title="Ban",
                description=f"{member.mention} has been banned.\nReason: {reason or 'No reason provided'}",
                color=discord.Color.red()
            )
            await ctx.send(embed=embed)
        except Exception as e:
            await ctx.send(f"Error banning user: {str(e)}")

    @commands.command()
    @has_permissions(administrator=True)
    async def kick(self, ctx, member: discord.Member, *, reason=None):
        """Kick a member from the server"""
        try:
            await member.kick(reason=reason)
            embed = discord.Embed(
                title="Kick",
                description=f"{member.mention} has been kicked.\nReason: {reason or 'No reason provided'}",
                color=discord.Color.red()
            )
            await ctx.send(embed=embed)
        except Exception as e:
            await ctx.send(f"Error kicking user: {str(e)}")

    # TODO: Implement mute and unmute commands (WORKS BUT AUTOMATIC UNMUTE DOESNT)
    # @commands.command()
    # @has_permissions(administrator=True)
    # async def mute(self, ctx, member: discord.Member, duration: str = "10m", *, reason=None):
    #     """Mute a member for a specified duration (e.g., '60s' for seconds, '10m' for minutes)"""
    #     try:
    #         muted_role = discord.utils.get(ctx.guild.roles, name="Muted")
    #         if not muted_role:
    #             muted_role = await ctx.guild.create_role(name="Muted")
    #             for channel in ctx.guild.channels:
    #                 await channel.set_permissions(muted_role, speak=False, send_messages=False)
            
    #         if muted_role in member.roles:
    #             await ctx.send(f"{member.mention} is already muted.")
    #         else:
    #             await member.add_roles(muted_role)
    #             embed = discord.Embed(
    #                 title="Mute",
    #                 description=f"{member.mention} has been muted for {duration}.\nReason: {reason or 'No reason provided'}",
    #                 color=discord.Color.red()
    #             )
    #             await ctx.send(embed=embed)
                
    #             time_multiplier = 60 if duration.endswith('m') else 1
    #             duration_seconds = int(duration[:-1]) * time_multiplier
                
    #             await asyncio.sleep(duration_seconds)
    #             if muted_role in member.roles:
    #                 await member.remove_roles(muted_role)
    #                 unmute_embed = discord.Embed(
    #                     title="Unmute",
    #                     description=f"{member.mention} has been automatically unmuted.",
    #                     color=discord.Color.green()
    #                 )
    #                 await ctx.send(embed=unmute_embed)
    #     except Exception as e:
    #         await ctx.send(f"Error muting user: {str(e)}")

    # @commands.command()
    # @has_permissions(administrator=True)
    # async def unmute(self, ctx, member: discord.Member):
    #     """Unmute a member"""
    #     try:
    #         muted_role = discord.utils.get(ctx.guild.roles, name="Muted")
    #         if muted_role and muted_role in member.roles:
    #             await member.remove_roles(muted_role)
    #             embed = discord.Embed(
    #                 title="Unmute",
    #                 description=f"{member.mention} has been unmuted.",
    #                 color=discord.Color.green()
    #             )
    #             await ctx.send(embed=embed)
    #         else:
    #             await ctx.send(f"{member.mention} is not muted.")
    #     except Exception as e:
    #         await ctx.send(f"Error unmuting user: {str(e)}")

    @commands.command()
    @has_permissions(administrator=True)
    async def addbalance(self, ctx, member: discord.Member, amount: int):
        """Add balance to a user's account"""
        try:
            economy_cog = self.client.get_cog("EconomyCog")
            if economy_cog:
                await economy_cog.add_balance(member.id, amount)
                embed = discord.Embed(
                    title="Balance Added",
                    description=f"Added {amount} coins to {member.mention}'s balance.",
                    color=discord.Color.green()
                )
                await ctx.send(embed=embed)
            else:
                await ctx.send("Economy system is not available.")
        except Exception as e:
            await ctx.send(f"Error adding balance: {str(e)}")

    @commands.command()
    @has_permissions(administrator=True)
    async def removebalance(self, ctx, member: discord.Member, amount: int):
        """Remove balance from a user's account"""
        try:
            economy_cog = self.client.get_cog("EconomyCog")
            if economy_cog:
                await economy_cog.remove_balance(member.id, amount)
                embed = discord.Embed(
                    title="Balance Removed",
                    description=f"Removed {amount} coins from {member.mention}'s balance.",
                    color=discord.Color.red()
                )
                await ctx.send(embed=embed)
            else:
                await ctx.send("Economy system is not available.")
        except Exception as e:
            await ctx.send(f"Error removing balance: {str(e)}")

    @ban.error
    @kick.error
    # @mute.error
    # @unmute.error
    @addbalance.error
    @removebalance.error
    async def admin_command_error(self, ctx, error):
        if isinstance(error, commands.MissingPermissions):
            embed = discord.Embed(
                title="Permission Denied",
                description="You don't have permission to use this command.",
                color=discord.Color.red()
            )
            await ctx.send(embed=embed)
        elif isinstance(error, commands.MemberNotFound):
            embed = discord.Embed(
                title="Error",
                description="Member not found.",
                color=discord.Color.red()
            )
            await ctx.send(embed=embed)
        else:
            embed = discord.Embed(
                title="Error",
                description=f"An error occurred: {str(error)}",
                color=discord.Color.red()
            )
            await ctx.send(embed=embed)

async def setup(client):
    await client.add_cog(AdminCog(client))