import discord
from discord.ext import commands
import json
import os
import math
import datetime
import random

class LevelsCog(commands.Cog):
    def __init__(self, client):
        self.client = client
        # XP settings
        self.base_xp = 15  # Base XP per message
        self.xp_per_level = 7500  # XP needed for each level (500 messages = one level)
        self.message_count = {}  # Track messages per minute
        self.window_start = {}  # Track when the 60-second window started
        
    @commands.Cog.listener()
    async def on_message(self, message):
        # Don't process bot messages or commands
        if message.author.bot or message.content.startswith(self.client.command_prefix):
            return
            
        # Handle XP gain
        await self.add_xp(message.author, message.channel)
        
    async def add_xp(self, user, channel):
        # Anti-spam mechanism (max 60 messages per minute)
        user_id = str(user.id)
        current_time = datetime.datetime.now().timestamp()
        
        # Initialize tracking for new users
        if user_id not in self.message_count:
            self.message_count[user_id] = 0
            self.window_start[user_id] = current_time
        
        # Check if 60 seconds have passed, reset if true
        if current_time - self.window_start[user_id] > 60:
            self.message_count[user_id] = 0
            self.window_start[user_id] = current_time
        
        # Increment message count and check if under limit
        self.message_count[user_id] += 1
        if self.message_count[user_id] > 60:
            return  # Over rate limit, don't add XP
                
        # Add XP with some randomness
        xp_gained = self.base_xp + random.randint(-5, 5)
        if xp_gained < 5:
            xp_gained = 5  # Minimum XP gain
            
        # Get current user data
        users = await self.get_levels_data()
        await self.check_user(user)
        
        # Get current level
        current_level = users[user_id]["level"]
        current_xp = users[user_id]["xp"]
        new_xp = current_xp + xp_gained
        
        # Calculate if user leveled up
        level_up = False
        new_level = math.floor(new_xp / self.xp_per_level)
        
        if new_level > current_level:
            level_up = True
            users[user_id]["level"] = new_level
            
        # Update user data
        users[user_id]["xp"] = new_xp
        users[user_id]["total_messages"] += 1
        users[user_id]["last_message"] = current_time
        
        # Save data
        with open('data/levels.json', 'w') as f:
            json.dump(users, f)
            
        # Send level up message if user leveled up
        if level_up and channel:
            embed = discord.Embed(
                title="LEVEL UP! 🎉",
                description=f"Congratulations {user.mention}! You've reached **Level {new_level}**!",
                color=discord.Color.gold()
            )
            embed.set_thumbnail(url=user.avatar.url if user.avatar else user.default_avatar.url)
            await channel.send(embed=embed)
    
    @commands.command(aliases=["xp", "lvl"])
    async def level(self, ctx, member: discord.Member = None):
        """Check your level or another member's level"""
        if member is None:
            member = ctx.author
            
        await self.check_user(member)
        users = await self.get_levels_data()
        user_id = str(member.id)
        
        # Get user data
        xp = users[user_id]["xp"]
        level = users[user_id]["level"]
        total_messages = users[user_id]["total_messages"]
        
        # Calculate progress to next level
        xp_for_current_level = level * self.xp_per_level
        xp_for_next_level = (level + 1) * self.xp_per_level
        current_level_xp = xp - xp_for_current_level
        needed_for_next_level = xp_for_next_level - xp_for_current_level
        percentage = min(100, max(0, int((current_level_xp / needed_for_next_level) * 100)))
        
        # Create progress bar
        progress_bar = self.create_progress_bar(percentage)
        
        # Create embed
        embed = discord.Embed(
            title=f"{member.name}'s Level Stats",
            color=discord.Color.blue()
        )
        
        embed.add_field(name="Level", value=f"**{level}**", inline=True)
        embed.add_field(name="Total XP", value=f"**{xp}**", inline=True)
        embed.add_field(name="Messages", value=f"**{total_messages}**", inline=True)
        embed.add_field(name=f"Progress to Level {level+1}", value=f"{progress_bar} **{percentage}%**\n{current_level_xp}/{needed_for_next_level} XP", inline=False)
        
        embed.set_thumbnail(url=member.avatar.url if member.avatar else member.default_avatar.url)
        embed.set_footer(text=f"Requested by {ctx.author.name}", icon_url=ctx.author.avatar.url if ctx.author.avatar else ctx.author.default_avatar.url)
        embed.timestamp = datetime.datetime.utcnow()
        
        await ctx.send(embed=embed)
        
    def create_progress_bar(self, percentage, length=10):
        """Creates a text-based progress bar"""
        filled_bars = math.floor(percentage / (100 / length))
        empty_bars = length - filled_bars
        return "🟦" * filled_bars + "⬜" * empty_bars
        
    @commands.command(aliases=["lvltop"])
    async def levels(self, ctx, page: int = 1):
        """Show the server's level leaderboard"""
        # Get all user data from the database file directly
        users = await self.get_levels_data()
        
        # Create list from all users in the database
        user_list = []
        
        # First, add all existing database entries
        for user_id, user_data in users.items():
            try:
                # Try to get the member object, fetch from Discord if needed
                member = ctx.guild.get_member(int(user_id))
                
                # Include all users in the database
                if 'xp' in user_data:
                    # Get user data
                    user_entry = {
                        "id": user_id,
                        "xp": user_data["xp"],
                        "level": user_data["level"],
                        "total_messages": user_data["total_messages"],
                        "member": member
                    }
                    user_list.append(user_entry)
            except Exception as e:
                # Skip problematic entries
                continue
        
        # Now sort and display
        # Sort by level first, then by XP (both descending)
        user_list.sort(key=lambda x: (x["level"], x["xp"]), reverse=True)
        
        # Paginate results (10 per page)
        total_pages = max(1, math.ceil(len(user_list) / 10))
        
        # Ensure page is within valid range
        page = max(1, min(page, total_pages))
        
        start_idx = (page - 1) * 10
        end_idx = min(start_idx + 10, len(user_list))
        
        # Create embed
        embed = discord.Embed(
            title=f"🏆 Level Leaderboard",
            description=f"Top members ranked by level and XP.",
            color=discord.Color.gold()
        )
        
        # Add leaderboard entries
        if not user_list:
            embed.description = "No users have earned XP yet! Send some messages to start gaining levels."
        else:
            # Get rank emojis for top 3
            rank_emoji = {0: "🥇", 1: "🥈", 2: "🥉"}
            
            for idx, user_data in enumerate(user_list[start_idx:end_idx], start=start_idx + 1):
                member = user_data["member"]
                user_id = user_data["id"]
                position = idx - 1 + start_idx  # Zero-based position
                
                # Get appropriate emoji based on rank
                prefix = rank_emoji.get(position, f"{idx}.")
                
                # Get XP progress percentage to next level
                level = user_data["level"]
                xp = user_data["xp"]
                xp_for_current_level = level * self.xp_per_level
                xp_for_next_level = (level + 1) * self.xp_per_level
                current_level_xp = xp - xp_for_current_level
                needed_for_next_level = xp_for_next_level - xp_for_current_level
                percentage = min(100, max(0, int((current_level_xp / needed_for_next_level) * 100)))
                
                # Create a mini progress bar (5 spaces)
                progress = self.create_progress_bar(percentage, 5)
                
                # Get the name and icon url
                if member:
                    name = member.name
                    icon_url = member.avatar.url if member.avatar else member.default_avatar.url
                else:
                    # Try to fetch user info from Discord
                    try:
                        user = await self.client.fetch_user(int(user_id))
                        name = user.name
                        icon_url = user.avatar.url if user.avatar else user.default_avatar.url
                    except:
                        # If all else fails, use a generic name
                        name = f"User-{user_id[-4:]}"
                        icon_url = None
                
                # Create embed field
                field_name = f"{prefix} {name}"
                field_value = f"Level: **{level}** | XP: **{xp}** | Messages: **{user_data['total_messages']}**\n{progress} **{percentage}%** to Level {level+1}"
                
                embed.add_field(name=field_name, value=field_value, inline=False)
                
                # Show first-place user as thumbnail
                if position == 0 and icon_url:
                    embed.set_thumbnail(url=icon_url)
        
        embed.set_footer(text=f"Page {page}/{total_pages} • Requested by {ctx.author.name}", 
                         icon_url=ctx.author.avatar.url if ctx.author.avatar else ctx.author.default_avatar.url)
        embed.timestamp = datetime.datetime.utcnow()
        
        # Create view with pagination buttons
        view = LevelLeaderboardView(self, ctx, page, total_pages)
        
        # Send embed with view
        view.message = await ctx.send(embed=embed, view=view)
        
    async def check_user(self, user):
        """Check if user exists in database, create if not"""
        users = await self.get_levels_data()
        user_id = str(user.id)
        
        if user_id not in users:
            users[user_id] = {
                "xp": 0,
                "level": 0,
                "total_messages": 0,
                "last_message": 0
            }
            
            # Save updated data
            with open('data/levels.json', 'w') as f:
                json.dump(users, f)
                
        return True
        
    async def get_levels_data(self):
        """Get level data from JSON file"""
        if not os.path.exists('data'):
            os.makedirs('data')
        
        if not os.path.exists('data/levels.json'):
            with open('data/levels.json', 'w') as f:
                json.dump({}, f)

        with open('data/levels.json', 'r') as f:
            content = f.read().strip()
            if not content:
                users = {}
            else:
                try:
                    users = json.loads(content)
                except json.JSONDecodeError:
                    users = {}
            
        if not content:
            with open('data/levels.json', 'w') as f:
                json.dump(users, f)
                
        return users

class LevelLeaderboardView(discord.ui.View):
    def __init__(self, cog, ctx, page, total_pages):
        super().__init__(timeout=60)
        self.cog = cog
        self.ctx = ctx
        self.page = page
        self.total_pages = total_pages
        
        # Add previous page button if not on first page
        if page > 1:
            prev_button = discord.ui.Button(
                label="Previous",
                style=discord.ButtonStyle.primary,
                emoji="⬅️",
                custom_id="prev_page",
                row=0
            )
            prev_button.callback = self.prev_callback
            self.add_item(prev_button)
        
        # Add next page button if not on last page
        if page < total_pages:
            next_button = discord.ui.Button(
                label="Next",
                style=discord.ButtonStyle.primary,
                emoji="➡️",
                custom_id="next_page",
                row=0
            )
            next_button.callback = self.next_callback
            self.add_item(next_button)

    async def interaction_check(self, interaction: discord.Interaction) -> bool:
        if interaction.user != self.ctx.author:
            await interaction.response.send_message("This menu is not for you!", ephemeral=True)
            return False
        return True

    async def on_timeout(self):
        for item in self.children:
            item.disabled = True
        try:
            await self.message.edit(view=self)
        except:
            pass

    async def update_page(self, new_page: int):
        # Get all user data from database 
        users = await self.cog.get_levels_data()
        
        # Create list from all users in the database
        user_list = []
        
        # Add all existing database entries
        for user_id, user_data in users.items():
            try:
                # Try to get the member object
                member = self.ctx.guild.get_member(int(user_id))
                
                # Include all users in the database
                if 'xp' in user_data:
                    # Get user data
                    user_entry = {
                        "id": user_id,
                        "xp": user_data["xp"],
                        "level": user_data["level"],
                        "total_messages": user_data["total_messages"],
                        "member": member
                    }
                    user_list.append(user_entry)
            except Exception as e:
                # Skip problematic entries
                continue
        
        # Sort by level first, then by XP (both descending)
        user_list.sort(key=lambda x: (x["level"], x["xp"]), reverse=True)
        
        # Paginate results (10 per page)
        total_pages = max(1, math.ceil(len(user_list) / 10))
        
        # Ensure page is within valid range
        new_page = max(1, min(new_page, total_pages))
        
        start_idx = (new_page - 1) * 10
        end_idx = min(start_idx + 10, len(user_list))
        
        # Create embed
        embed = discord.Embed(
            title=f"🏆 Level Leaderboard",
            description=f"Top members ranked by level and XP.",
            color=discord.Color.gold()
        )
        
        # Add leaderboard entries
        if not user_list:
            embed.description = "No users have earned XP yet! Send some messages to start gaining levels."
        else:
            # Get rank emojis for top 3
            rank_emoji = {0: "🥇", 1: "🥈", 2: "🥉"}
            
            for idx, user_data in enumerate(user_list[start_idx:end_idx], start=start_idx + 1):
                member = user_data["member"]
                user_id = user_data["id"]
                position = idx - 1 + start_idx  # Zero-based position
                
                # Get appropriate emoji based on rank
                prefix = rank_emoji.get(position, f"{idx}.")
                
                # Get XP progress percentage to next level
                level = user_data["level"]
                xp = user_data["xp"]
                xp_for_current_level = level * self.cog.xp_per_level
                xp_for_next_level = (level + 1) * self.cog.xp_per_level
                current_level_xp = xp - xp_for_current_level
                needed_for_next_level = xp_for_next_level - xp_for_current_level
                percentage = min(100, max(0, int((current_level_xp / needed_for_next_level) * 100)))
                
                # Create a mini progress bar (5 spaces)
                progress = self.cog.create_progress_bar(percentage, 5)
                
                # Get the name and icon url
                if member:
                    name = member.name
                    icon_url = member.avatar.url if member.avatar else member.default_avatar.url
                else:
                    # Try to fetch user info from Discord
                    try:
                        user = await self.cog.client.fetch_user(int(user_id))
                        name = user.name
                        icon_url = user.avatar.url if user.avatar else user.default_avatar.url
                    except:
                        # If all else fails, use a generic name
                        name = f"User-{user_id[-4:]}"
                        icon_url = None
                
                # Create embed field
                field_name = f"{prefix} {name}"
                field_value = f"Level: **{level}** | XP: **{xp}** | Messages: **{user_data['total_messages']}**\n{progress} **{percentage}%** to Level {level+1}"
                
                embed.add_field(name=field_name, value=field_value, inline=False)
                
                # Show first-place user as thumbnail
                if position == 0 and icon_url:
                    embed.set_thumbnail(url=icon_url)
        
        embed.set_footer(text=f"Page {new_page}/{total_pages} • Requested by {self.ctx.author.name}", 
                         icon_url=self.ctx.author.avatar.url if self.ctx.author.avatar else self.ctx.author.default_avatar.url)
        embed.timestamp = datetime.datetime.utcnow()
        
        # Create new view with updated page
        new_view = LevelLeaderboardView(self.cog, self.ctx, new_page, total_pages)
        new_view.message = self.message
        
        # Update the message
        await self.message.edit(embed=embed, view=new_view)

    async def prev_callback(self, interaction: discord.Interaction):
        await interaction.response.defer()
        await self.update_page(self.page - 1)

    async def next_callback(self, interaction: discord.Interaction):
        await interaction.response.defer()
        await self.update_page(self.page + 1)

async def setup(client):
    await client.add_cog(LevelsCog(client)) 