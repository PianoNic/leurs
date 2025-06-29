import discord
from discord.ext import commands
import random
import os
import asyncio
import re
from discord.ext.commands import has_permissions
import json
from datetime import datetime
from collections import defaultdict
import pathlib

class AdminCog(commands.Cog):
    def __init__(self, client):
        self.client = client
        self.pending_cclear = {}  # Store pending clear operations
        
        # Create data directory if it doesn't exist
        self.data_dir = pathlib.Path("data")
        self.data_dir.mkdir(exist_ok=True)
        
        # Cache file paths
        self.message_cache_file = self.data_dir / "message_cache.json"
        self.message_index_file = self.data_dir / "message_index.json"
        self.last_scan_file = self.data_dir / "last_scan.txt"
        self.word_index = defaultdict(list)  # In-memory index for faster searching

    @commands.command()
    @has_permissions(administrator=True)
    async def ban(self, ctx, member: discord.Member, *, reason=None):
        """Ban a member from the server"""
        await member.ban(reason=reason)
        embed = discord.Embed(
            title="Ban",
            description=f"{member.mention} has been banned.\nReason: {reason or 'No reason provided'}",
            color=discord.Color.red()
        )
        await ctx.send(embed=embed)

    @commands.command()
    @has_permissions(administrator=True)
    async def kick(self, ctx, member: discord.Member, *, reason=None):
        """Kick a member from the server"""
        await member.kick(reason=reason)
        embed = discord.Embed(
            title="Kick",
            description=f"{member.mention} has been kicked.\nReason: {reason or 'No reason provided'}",
            color=discord.Color.red()
        )
        await ctx.send(embed=embed)

    @commands.command()
    @has_permissions(administrator=True)
    async def mute(self, ctx, member: discord.Member, duration: str = "10m", *, reason=None):
        """Mute a member for a specified duration (e.g., '60s' for seconds, '10m' for minutes)"""
        muted_role = await self.get_or_create_muted_role(ctx)
        if muted_role in member.roles:
            raise commands.CommandError(f"{member.mention} is already muted.")
        
        await self.apply_mute(ctx, member, muted_role, duration, reason)

    async def get_or_create_muted_role(self, ctx):
        """Retrieve or create the 'Muted' role."""
        muted_role = discord.utils.get(ctx.guild.roles, name="Muted")
        if not muted_role:
            muted_role = await ctx.guild.create_role(name="Muted")
            for channel in ctx.guild.channels:
                await channel.set_permissions(muted_role, speak=False, send_messages=False)
        return muted_role

    async def apply_mute(self, ctx, member, muted_role, duration, reason):
        """Apply the mute to the member."""
        await member.add_roles(muted_role)
        embed = discord.Embed(
            title="Mute",
            description=f"{member.mention} has been muted for {duration}.\nReason: {reason or 'No reason provided'}",
            color=discord.Color.red()
        )
        await ctx.send(embed=embed)
        
        asyncio.create_task(self.schedule_unmute(ctx, member, muted_role, duration))

    async def schedule_unmute(self, ctx, member, muted_role, duration):
        """Schedule the unmute after the specified duration."""
        if duration.endswith('s'):
            duration_seconds = int(duration[:-1])
        elif duration.endswith('m'):
            duration_seconds = int(duration[:-1]) * 60
        elif duration.endswith('h'):
            duration_seconds = int(duration[:-1]) * 3600
        elif duration.endswith('d'):
            duration_seconds = int(duration[:-1]) * 86400
        else:
            try:
                duration_seconds = int(duration) * 60
            except ValueError:
                raise commands.CommandError(f"Invalid duration format: {duration}. Use formats like '30s', '10m', '1h', or '1d'.")
        
        await asyncio.sleep(duration_seconds)
        
        try:
            member = await ctx.guild.fetch_member(member.id)
        except discord.NotFound:
            return  # Member left the server, no need to unmute
            
        if muted_role in member.roles:
            await member.remove_roles(muted_role)
            unmute_embed = discord.Embed(
                title="Unmute",
                description=f"{member.mention} has been automatically unmuted.",
                color=discord.Color.green()
            )
            await ctx.send(embed=unmute_embed)
            
    @commands.command()
    @has_permissions(administrator=True)
    async def unmute(self, ctx, member: discord.Member):
        """Unmute a member"""
        muted_role = discord.utils.get(ctx.guild.roles, name="Muted")
        if muted_role and muted_role in member.roles:
            await member.remove_roles(muted_role)
            embed = discord.Embed(
                title="Unmute",
                description=f"{member.mention} has been unmuted.",
                color=discord.Color.green()
            )
            await ctx.send(embed=embed)
        else:
            raise commands.CommandError(f"{member.mention} is not muted.")

    @commands.command()
    @has_permissions(administrator=True)
    async def addbalance(self, ctx, member: discord.Member, amount: int):
        """Add balance to a user's account"""
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
            raise commands.CommandError("Economy system is not available.")

    @commands.command()
    @has_permissions(administrator=True)
    async def removebalance(self, ctx, member: discord.Member, amount: int):
        """Remove balance from a user's account"""
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
            raise commands.CommandError("Economy system is not available.")

    @commands.command()
    @has_permissions(administrator=True)
    async def grant(self, ctx, member: discord.Member, time: str = None):
        """Grant a special role to a user for a specified duration (e.g., '30s', '5m', '2h', '7d') or permanently if no time specified"""
        try:
            role = ctx.guild.get_role(1225863450308378644)
            if not role:
                raise commands.CommandError("The specified role could not be found.")

            # If no time specified or 'perm'/'permanent', make it permanent
            if not time or time.lower() in ['perm', 'permanent']:
                duration_seconds = None
                time_str = "permanently"
            else:
                # Regular expression to parse time format
                time_pattern = re.compile(r'(\d+)([smhd])')
                match = time_pattern.match(time.lower())
                
                if not match:
                    raise commands.CommandError("Invalid time format. Use numbers followed by s/m/h/d (e.g., 30s, 5m, 2h, 7d) or no time for permanent.")
                    
                amount = int(match.group(1))
                unit = match.group(2)
                
                # Convert to seconds
                multipliers = {'s': 1, 'm': 60, 'h': 3600, 'd': 86400}
                duration_seconds = amount * multipliers[unit]
                
                # Create human-readable time string
                units = {'s': 'seconds', 'm': 'minutes', 'h': 'hours', 'd': 'days'}
                time_str = f"for {amount} {units[unit]}"

            # Add role
            await member.add_roles(role)
            
            embed = discord.Embed(
                title="Role Granted",
                description=f"Granted {role.mention} to {member.mention} {time_str}.",
                color=discord.Color.green()
            )
            await ctx.send(embed=embed)
            
            # If not permanent, schedule role removal
            if duration_seconds is not None:
                await asyncio.sleep(duration_seconds)
                try:
                    member = await ctx.guild.fetch_member(member.id)
                    if role in member.roles:  # Check if user still has the role
                        await member.remove_roles(role)
                        embed = discord.Embed(
                            title="Role Expired",
                            description=f"Removed {role.mention} from {member.mention} (Duration expired).",
                            color=discord.Color.blue()
                        )
                        await ctx.send(embed=embed)
                except discord.NotFound:
                    # Member left the server
                    pass
                    
        except discord.Forbidden:
            raise commands.CommandError("I don't have permission to manage roles.")

    @commands.command()
    @has_permissions(administrator=True)
    async def ungrant(self, ctx, member: discord.Member, time: str = None):
        """Temporarily remove the special role from a user for specified duration (e.g., '30s', '5m', '2h', '7d') or permanently if no time specified"""
        try:
            role = ctx.guild.get_role(1225863450308378644)
            if not role:
                raise commands.CommandError("The specified role could not be found.")

            if not role in member.roles:
                raise commands.CommandError(f"{member.mention} doesn't have the role to remove.")

            # If no time specified, remove permanently
            if not time:
                await member.remove_roles(role)
                embed = discord.Embed(
                    title="Role Removed",
                    description=f"Removed {role.mention} from {member.mention} permanently.",
                    color=discord.Color.blue()
                )
                await ctx.send(embed=embed)
                return

            # Parse time for temporary removal
            time_pattern = re.compile(r'(\d+)([smhd])')
            match = time_pattern.match(time.lower())
            
            if not match:
                raise commands.CommandError("Invalid time format. Use numbers followed by s/m/h/d (e.g., 30s, 5m, 2h, 7d) or no time for permanent removal.")
                
            amount = int(match.group(1))
            unit = match.group(2)
            
            # Convert to seconds
            multipliers = {'s': 1, 'm': 60, 'h': 3600, 'd': 86400}
            duration_seconds = amount * multipliers[unit]
            
            # Create human-readable time string
            units = {'s': 'seconds', 'm': 'minutes', 'h': 'hours', 'd': 'days'}
            time_str = f"for {amount} {units[unit]}"

            # Remove the role
            await member.remove_roles(role)
            embed = discord.Embed(
                title="Role Temporarily Removed",
                description=f"Removed {role.mention} from {member.mention} {time_str}.",
                color=discord.Color.yellow()
            )
            await ctx.send(embed=embed)
            
            # Schedule role restoration
            await asyncio.sleep(duration_seconds)
            try:
                member = await ctx.guild.fetch_member(member.id)
                if not role in member.roles:  # Only add if they don't already have it
                    await member.add_roles(role)
                    embed = discord.Embed(
                        title="Role Restored",
                        description=f"Restored {role.mention} to {member.mention} (Temporary removal period ended).",
                        color=discord.Color.green()
                    )
                    await ctx.send(embed=embed)
            except discord.NotFound:
                # Member left the server
                pass
                    
        except discord.Forbidden:
            raise commands.CommandError("I don't have permission to manage roles.")

    @commands.command()
    @has_permissions(administrator=True)
    async def clear(self, ctx, amount: int):
        """Clear a specified number of messages from the channel"""
        try:
            # Add 1 to include the command message itself
            amount = amount + 1
            
            # Check if amount is within Discord's limits
            if amount > 100:
                raise commands.CommandError("Cannot delete more than 99 messages at once.")
            elif amount < 1:
                raise commands.CommandError("Please specify a positive number of messages to delete.")
                
            # Delete messages
            deleted = await ctx.channel.purge(limit=amount)
            
            # Send confirmation message
            confirm_msg = await ctx.send(embed=discord.Embed(
                title="Messages Cleared",
                description=f"Deleted {len(deleted)-1} messages.",
                color=discord.Color.green()
            ))
            
            # Delete confirmation message after 1 second
            await asyncio.sleep(1)
            await confirm_msg.delete()
            
        except discord.Forbidden:
            raise commands.CommandError("I don't have permission to delete messages.")
        except discord.HTTPException as e:
            raise commands.CommandError(f"Failed to delete messages: {str(e)}")

    @commands.command()
    @has_permissions(administrator=True)
    async def jail(self, ctx, member: discord.Member, time: str = None):
        """Jail a user for a specified duration (e.g., '30s', '5m', '2h', '7d') or permanently if no time specified"""
        try:
            role = ctx.guild.get_role(1211618366763044874)
            if not role:
                raise commands.CommandError("The jail role could not be found.")

            # If no time specified or 'perm'/'permanent', make it permanent
            if not time or time.lower() in ['perm', 'permanent']:
                duration_seconds = None
                time_str = "permanently"
            else:
                # Regular expression to parse time format
                time_pattern = re.compile(r'(\d+)([smhd])')
                match = time_pattern.match(time.lower())
                
                if not match:
                    raise commands.CommandError("Invalid time format. Use numbers followed by s/m/h/d (e.g., 30s, 5m, 2h, 7d) or no time for permanent.")
                    
                amount = int(match.group(1))
                unit = match.group(2)
                
                # Convert to seconds
                multipliers = {'s': 1, 'm': 60, 'h': 3600, 'd': 86400}
                duration_seconds = amount * multipliers[unit]
                
                # Create human-readable time string
                units = {'s': 'seconds', 'm': 'minutes', 'h': 'hours', 'd': 'days'}
                time_str = f"for {amount} {units[unit]}"

            # Add role
            await member.add_roles(role)
            
            embed = discord.Embed(
                title="User Jailed",
                description=f"Jailed {member.mention} {time_str}.",
                color=discord.Color.red()
            )
            await ctx.send(embed=embed)
            
            # If not permanent, schedule role removal
            if duration_seconds is not None:
                await asyncio.sleep(duration_seconds)
                try:
                    member = await ctx.guild.fetch_member(member.id)
                    if role in member.roles:  # Check if user still has the role
                        await member.remove_roles(role)
                        embed = discord.Embed(
                            title="Jail Time Ended",
                            description=f"Released {member.mention} from jail (Time served).",
                            color=discord.Color.green()
                        )
                        await ctx.send(embed=embed)
                except discord.NotFound:
                    # Member left the server
                    pass
                    
        except discord.Forbidden:
            raise commands.CommandError("I don't have permission to manage roles.")

    @commands.command()
    @has_permissions(administrator=True)
    async def unjail(self, ctx, member: discord.Member, time: str = None):
        """Temporarily release a user from jail for specified duration (e.g., '30s', '5m', '2h', '7d') or permanently if no time specified"""
        try:
            role = ctx.guild.get_role(1211618366763044874)
            if not role:
                raise commands.CommandError("The jail role could not be found.")

            if not role in member.roles:
                raise commands.CommandError(f"{member.mention} is not jailed.")

            # If no time specified, remove permanently
            if not time:
                await member.remove_roles(role)
                embed = discord.Embed(
                    title="User Released",
                    description=f"Released {member.mention} from jail permanently.",
                    color=discord.Color.green()
                )
                await ctx.send(embed=embed)
                return

            # Parse time for temporary release
            time_pattern = re.compile(r'(\d+)([smhd])')
            match = time_pattern.match(time.lower())
            
            if not match:
                raise commands.CommandError("Invalid time format. Use numbers followed by s/m/h/d (e.g., 30s, 5m, 2h, 7d) or no time for permanent release.")
                
            amount = int(match.group(1))
            unit = match.group(2)
            
            # Convert to seconds
            multipliers = {'s': 1, 'm': 60, 'h': 3600, 'd': 86400}
            duration_seconds = amount * multipliers[unit]
            
            # Create human-readable time string
            units = {'s': 'seconds', 'm': 'minutes', 'h': 'hours', 'd': 'days'}
            time_str = f"for {amount} {units[unit]}"

            # Remove the role
            await member.remove_roles(role)
            embed = discord.Embed(
                title="Temporary Release",
                description=f"Released {member.mention} from jail {time_str}.",
                color=discord.Color.yellow()
            )
            await ctx.send(embed=embed)
            
            # Schedule return to jail
            await asyncio.sleep(duration_seconds)
            try:
                member = await ctx.guild.fetch_member(member.id)
                if not role in member.roles:  # Only add if they don't already have it
                    await member.add_roles(role)
                    embed = discord.Embed(
                        title="Return to Jail",
                        description=f"Returned {member.mention} to jail (Temporary release period ended).",
                        color=discord.Color.red()
                    )
                    await ctx.send(embed=embed)
            except discord.NotFound:
                # Member left the server
                pass
                    
        except discord.Forbidden:
            raise commands.CommandError("I don't have permission to manage roles.")

    @commands.command()
    @has_permissions(administrator=True)
    async def cclear(self, ctx, *args):
        """Clear messages containing specific text. Usage:
        cclear [text] - Search in all channels
        cclear -current [text] - Search only in current channel
        cclear [@user] [text] - Search messages from specific user
        cclear -scan - Scan and cache all messages
        cclear -p [percentage] [text] - Delete only specified percentage of matches
        cclear yes/no - Confirm or cancel pending deletion"""
        
        if not args:
            raise commands.CommandError("Please provide search text or yes/no for confirmation.")

        # Handle scan command
        if args[0] == '-scan':
            return await self.scan_all_messages(ctx)

        # Handle confirmation responses
        if args[0].lower() in ['yes', 'no']:
            return await self.handle_cclear_confirmation(ctx, args[0].lower())

        # Check if we have a recent cache
        if not self.is_cache_recent():
            await ctx.send(embed=discord.Embed(
                title="Cache Not Found or Outdated",
                description="Message cache is outdated or doesn't exist. Please run `cclear -scan` first.",
                color=discord.Color.red()
            ))
            return

        # Parse arguments
        target_user = None
        current_channel_only = False
        search_text = ""
        percentage = 100  # Default to 100%

        # Handle percentage flag
        if args[0] in ['-p', '-%']:
            if len(args) < 3:
                raise commands.CommandError("Please provide percentage and search text after -p flag.")
            try:
                percentage = float(args[1].strip('%'))  # Remove % if present
                if not 0 < percentage <= 100:
                    raise ValueError
                args = args[2:]  # Remove percentage arguments
            except ValueError:
                raise commands.CommandError("Percentage must be a number between 0 and 100.")
        
        if args[0] == '-current':
            if len(args) < 2:
                raise commands.CommandError("Please provide search text after -current flag.")
            current_channel_only = True
            search_text = ' '.join(args[1:])
        elif args[0].startswith('<@') and args[0].endswith('>'):
            if len(args) < 2:
                raise commands.CommandError("Please provide search text after user mention.")
            try:
                target_user = await commands.MemberConverter().convert(ctx, args[0])
                search_text = ' '.join(args[1:])
            except:
                raise commands.CommandError("Invalid user mention.")
        else:
            search_text = ' '.join(args)

        # Search in cached messages
        messages_to_delete = await self.search_cached_messages(ctx, search_text, current_channel_only, target_user)

        if not messages_to_delete:
            raise commands.CommandError(f"No messages found containing '{search_text}'")

        # Apply percentage if less than 100%
        if percentage < 100:
            # Calculate how many messages to keep and take the first N%
            messages_to_keep = int(len(messages_to_delete) * (percentage / 100))
            messages_to_delete = messages_to_delete[:messages_to_keep]

        # Store the pending operation
        self.pending_cclear[ctx.author.id] = {
            'messages': messages_to_delete,
            'search_text': search_text,
            'timestamp': ctx.message.created_at,
            'percentage': percentage
        }

        # Send confirmation message
        embed = discord.Embed(
            title="Confirm Message Deletion",
            description=f"Found {len(messages_to_delete)} messages containing '{search_text}'\n"
                      f"Will delete {percentage}% ({len(messages_to_delete)} messages)\n"
                      f"Type `cclear yes` to confirm deletion or `cclear no` to cancel.",
            color=discord.Color.yellow()
        )
        await ctx.send(embed=embed)

    async def scan_all_messages(self, ctx):
        """Scan and cache all messages in the server"""
        status_msg = await ctx.send(embed=discord.Embed(
            title="Scanning Messages",
            description="Starting scan... This might take a while.",
            color=discord.Color.blue()
        ))

        cached_messages = []
        channels_to_scan = ctx.guild.text_channels
        total_channels = len(channels_to_scan)
        processed_channels = 0
        total_messages = 0

        # Clear existing index
        self.word_index.clear()

        for channel in channels_to_scan:
            try:
                processed_channels += 1
                await status_msg.edit(embed=discord.Embed(
                    title="Scanning Messages",
                    description=f"Channel {processed_channels}/{total_channels}: {channel.name}\n"
                              f"Total messages scanned: {total_messages}",
                    color=discord.Color.blue()
                ))

                async for message in channel.history(limit=None):
                    total_messages += 1
                    
                    # Update progress every 100 messages
                    if total_messages % 100 == 0:
                        await status_msg.edit(embed=discord.Embed(
                            title="Scanning Messages",
                            description=f"Channel {processed_channels}/{total_channels}: {channel.name}\n"
                                      f"Total messages scanned: {total_messages}",
                            color=discord.Color.blue()
                        ))

                    # Cache message data
                    message_data = {
                        'content': message.content,
                        'channel_id': channel.id,
                        'message_id': message.id,
                        'author_id': message.author.id,
                        'timestamp': message.created_at.isoformat()
                    }
                    
                    # Add to cached messages
                    msg_index = len(cached_messages)
                    cached_messages.append(message_data)
                    
                    # Index words for faster searching
                    words = set(message.content.lower().split())  # Using set to avoid duplicate words
                    for word in words:
                        self.word_index[word].append(msg_index)

            except discord.Forbidden:
                await status_msg.edit(embed=discord.Embed(
                    title="Scanning Messages",
                    description=f"Skipped channel {channel.name} (No access)\n"
                              f"Total messages scanned: {total_messages}",
                    color=discord.Color.blue()
                ))
                continue
            except Exception as e:
                await ctx.send(f"Error in channel {channel.name}: {str(e)}")
                continue

        # Save to cache files
        try:
            # Save messages
            with open(self.message_cache_file, 'w', encoding='utf-8') as f:
                json.dump(cached_messages, f, ensure_ascii=False, indent=2)
            
            # Save word index
            with open(self.message_index_file, 'w', encoding='utf-8') as f:
                json.dump(dict(self.word_index), f, ensure_ascii=False, indent=2)
            
            # Save scan timestamp
            with open(self.last_scan_file, 'w') as f:
                f.write(datetime.utcnow().isoformat())

            await status_msg.edit(embed=discord.Embed(
                title="Scan Complete",
                description=f"Successfully cached {total_messages} messages from {total_channels} channels.\n"
                          f"Created search index with {len(self.word_index)} unique words.",
                color=discord.Color.green()
            ))
        except Exception as e:
            await ctx.send(f"Error saving cache: {str(e)}")

    def load_cache(self):
        """Load cache files into memory"""
        try:
            # Load messages
            with open(self.message_cache_file, 'r', encoding='utf-8') as f:
                cached_messages = json.load(f)
            
            # Load word index
            with open(self.message_index_file, 'r', encoding='utf-8') as f:
                self.word_index = defaultdict(list, json.load(f))
            
            return cached_messages
        except:
            raise commands.CommandError("Error reading cache files. Please run `cclear -scan` again.")

    async def search_cached_messages(self, ctx, search_text, current_channel_only, target_user):
        """Search through cached messages using the word index"""
        status_msg = await ctx.send(embed=discord.Embed(
            title="Searching Messages",
            description="Reading cache files...",
            color=discord.Color.blue()
        ))

        try:
            cached_messages = self.load_cache()
        except Exception as e:
            await status_msg.delete()
            raise e

        messages_to_delete = []
        search_words = search_text.lower().split()
        
        # Get potential message indices from the word index
        potential_indices = set()
        if search_words:
            # Start with indices from the first word
            potential_indices = set(self.word_index[search_words[0]])
            # Intersect with indices from other words
            for word in search_words[1:]:
                potential_indices &= set(self.word_index[word])
        
        await status_msg.edit(embed=discord.Embed(
            title="Searching Messages",
            description=f"Found {len(potential_indices)} potential matches. Verifying...",
            color=discord.Color.blue()
        ))

        # Verify matches and fetch messages
        for msg_index in potential_indices:
            msg_data = cached_messages[msg_index]
            
            # Check channel filter
            if current_channel_only and msg_data['channel_id'] != ctx.channel.id:
                continue

            # Check user filter
            if target_user and msg_data['author_id'] != target_user.id:
                continue

            # Double check content (for partial word matches)
            if search_text.lower() in msg_data['content'].lower():
                try:
                    channel = ctx.guild.get_channel(msg_data['channel_id'])
                    if channel:
                        message = await channel.fetch_message(msg_data['message_id'])
                        messages_to_delete.append(message)
                except:
                    continue

        await status_msg.delete()
        return messages_to_delete

    async def handle_cclear_confirmation(self, ctx, response):
        """Handle the confirmation response for cclear command"""
        if ctx.author.id not in self.pending_cclear:
            raise commands.CommandError("No pending clear operation. Please start a new search.")

        pending = self.pending_cclear[ctx.author.id]
        
        # Check if the confirmation has expired (5 minutes)
        if (ctx.message.created_at - pending['timestamp']).total_seconds() > 300:
            del self.pending_cclear[ctx.author.id]
            raise commands.CommandError("Confirmation expired. Please start a new search.")

        if response == 'no':
            del self.pending_cclear[ctx.author.id]
            embed = discord.Embed(
                title="Operation Cancelled",
                description="Message deletion cancelled.",
                color=discord.Color.green()
            )
            await ctx.send(embed=embed)
            return

        # Process deletion
        total_messages = len(pending['messages'])
        deleted_count = 0
        failed_count = 0
        
        status_msg = await ctx.send(embed=discord.Embed(
            title="Deleting Messages",
            description=f"Starting deletion of {total_messages} messages...",
            color=discord.Color.blue()
        ))

        # Group messages by channel for bulk deletion
        messages_by_channel = {}
        for message in pending['messages']:
            if message.channel.id not in messages_by_channel:
                messages_by_channel[message.channel.id] = {
                    'channel': message.channel,
                    'recent': [],  # Messages < 14 days old
                    'old': []      # Messages > 14 days old
                }
            
            # Check if message is less than 14 days old
            if (ctx.message.created_at - message.created_at).days < 14:
                messages_by_channel[message.channel.id]['recent'].append(message)
            else:
                messages_by_channel[message.channel.id]['old'].append(message)

        # Process each channel
        for channel_data in messages_by_channel.values():
            channel = channel_data['channel']
            recent_messages = channel_data['recent']
            old_messages = channel_data['old']

            # Bulk delete recent messages in chunks of 100
            if recent_messages:
                chunks = [recent_messages[i:i + 100] for i in range(0, len(recent_messages), 100)]
                for chunk in chunks:
                    try:
                        await channel.delete_messages(chunk)
                        deleted_count += len(chunk)
                        
                        # Update status every chunk
                        await status_msg.edit(embed=discord.Embed(
                            title="Deleting Messages",
                            description=f"Progress: {deleted_count + failed_count}/{total_messages}\n"
                                      f"Successfully deleted: {deleted_count}\n"
                                      f"Failed: {failed_count}",
                            color=discord.Color.blue()
                        ))
                        
                        # Small delay between chunks to avoid rate limits
                        await asyncio.sleep(1)
                    except Exception as e:
                        failed_count += len(chunk)

            # Delete old messages individually (can't bulk delete)
            if old_messages:
                for i, message in enumerate(old_messages):
                    try:
                        await message.delete()
                        deleted_count += 1
                        
                        # Update status every 20 messages for old messages
                        if (i + 1) % 20 == 0:
                            await status_msg.edit(embed=discord.Embed(
                                title="Deleting Messages",
                                description=f"Progress: {deleted_count + failed_count}/{total_messages}\n"
                                          f"Successfully deleted: {deleted_count}\n"
                                          f"Failed: {failed_count}",
                                color=discord.Color.blue()
                            ))
                    except:
                        failed_count += 1

                    # Only add delay every 5 messages for old messages
                    if (i + 1) % 5 == 0:
                        await asyncio.sleep(1)

        del self.pending_cclear[ctx.author.id]
        await status_msg.delete()

        # Send completion message
        embed = discord.Embed(
            title="Messages Deleted",
            description=f"Successfully deleted {deleted_count} messages.\n"
                      f"Failed to delete {failed_count} messages.",
            color=discord.Color.green()
        )
        await ctx.send(embed=embed)

    def is_cache_recent(self):
        """Check if cache exists and is less than 24 hours old"""
        try:
            if not os.path.exists(self.last_scan_file) or not os.path.exists(self.message_cache_file):
                return False

            with open(self.last_scan_file, 'r') as f:
                last_scan = datetime.fromisoformat(f.read().strip())
                
            # Check if cache is less than 24 hours old
            return (datetime.utcnow() - last_scan).total_seconds() < 86400
        except:
            return False

    @ban.error
    @kick.error
    @mute.error
    @unmute.error
    @addbalance.error
    @removebalance.error
    @grant.error
    @ungrant.error
    @jail.error
    @unjail.error
    @clear.error
    @cclear.error
    async def admin_command_error(self, ctx, error):
        if isinstance(error, commands.MissingPermissions):
            embed = discord.Embed(
                title="Permission Denied",
                description="You don't have permission to use this command.",
                color=discord.Color.red()
            )
            await ctx.send(embed=embed)
            return True  # Signal that we handled this error
        elif isinstance(error, commands.MemberNotFound):
            embed = discord.Embed(
                title="Error",
                description="Member not found.",
                color=discord.Color.red()
            )
            await ctx.send(embed=embed)
            return True  # Signal that we handled this error
        elif isinstance(error, commands.BadArgument):
            embed = discord.Embed(
                title="Error",
                description="Please provide a valid number of messages to delete.",
                color=discord.Color.red()
            )
            await ctx.send(embed=embed)
            return True
        elif isinstance(error, commands.MissingRequiredArgument):
            embed = discord.Embed(
                title="Error",
                description="Please specify the number of messages to delete.",
                color=discord.Color.red()
            )
            await ctx.send(embed=embed)
            return True
        elif isinstance(error, commands.CommandError):
            embed = discord.Embed(
                title="Error",
                description=str(error),
                color=discord.Color.red()
            )
            await ctx.send(embed=embed)
            return True  # Signal that we handled this error
        return False  # Signal that we did not handle this error

async def setup(client):
    await client.add_cog(AdminCog(client))