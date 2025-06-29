import discord
from discord.ext import commands
import random
import os
from datetime import datetime, timedelta
import time
import re
import asyncio
from typing import Optional, Tuple
import pytz
import requests
import io
from PIL import Image, ImageDraw, ImageFont
import textwrap
import traceback

class OtherCog(commands.Cog):
    def __init__(self, client):
        self.client = client
        self.afk_users = {}  # Store user_id: (reason, timestamp, command_timestamp)
        self.reminder_tasks = {}  # Store user_id: list of asyncio tasks
        
        # Create fonts directory if it doesn't exist
        os.makedirs('data/fonts', exist_ok=True)
        
        # Font paths - we'll use default fonts if custom ones aren't available
        self.font_path = self.get_font_path()
        print(f"Font path: {self.font_path}")
    
    def parse_time(self, time_str: str, reason: str) -> Tuple[Optional[datetime], str]:
        """Parse various time formats and return a datetime object and the cleaned reason"""
        now = datetime.now()
        
        # Handle relative time formats (15m, 2h, 3d)
        relative_match = re.match(r'^(\d+)([smhd])$', time_str.lower())
        if relative_match:
            amount, unit = relative_match.groups()
            amount = int(amount)
            delta = {
                's': timedelta(seconds=amount),
                'm': timedelta(minutes=amount),
                'h': timedelta(hours=amount),
                'd': timedelta(days=amount)
            }[unit]
            return now + delta, reason
            
        # Handle "tomorrow" or "tm"
        if time_str.lower() in ['tomorrow', 'tm']:
            return now + timedelta(days=1), reason
            
        # Handle HH:MM format (both 24h and 12h with am/pm)
        time_match = re.match(r'^(\d{1,2})(?::(\d{2}))?\s*(am|pm)?$', time_str.lower())
        if time_match:
            hour, minute, meridiem = time_match.groups()
            hour = int(hour)
            minute = int(minute) if minute else 0
            
            if meridiem:
                if meridiem == 'pm' and hour < 12:
                    hour += 12
                elif meridiem == 'am' and hour == 12:
                    hour = 0
                    
            target = now.replace(hour=hour, minute=minute, second=0, microsecond=0)
            if target <= now:
                target += timedelta(days=1)
            return target, reason
            
        # Handle date formats (15.05 or 15.05.26 or 15.05.2026)
        date_match = re.match(r'^(\d{1,2})\.(\d{1,2})(?:\.(\d{2}|\d{4}))?$', time_str)
        if date_match:
            day, month, year = date_match.groups()
            day = int(day)
            month = int(month)
            
            if year:
                year = int(year)
                if year < 100:
                    year += 2000
            else:
                year = now.year
                
            try:
                target = datetime(year, month, day, 0, 0, 0)
                if target <= now:
                    if not year:
                        target = target.replace(year=target.year + 1)
                return target, reason
            except ValueError:
                return None, reason
                
        # Handle full datetime format (15.07:15:25:00 or 15.07:15:25)
        datetime_match = re.match(r'^(\d{1,2})\.(\d{1,2}):(\d{1,2}):(\d{1,2})(?::(\d{1,2}))?$', time_str)
        if datetime_match:
            day, month, hour, minute, second = datetime_match.groups()
            try:
                target = now.replace(
                    day=int(day),
                    month=int(month),
                    hour=int(hour),
                    minute=int(minute),
                    second=int(second) if second else 0,
                    microsecond=0
                )
                if target <= now:
                    target = target.replace(year=target.year + 1)
                return target, reason
            except ValueError:
                return None, reason
                
        return None, reason
        
    async def send_reminder(self, ctx, user_id: int, channel_id: int, remind_time: datetime, reason: str):
        """Send a reminder to the user at the specified time"""
        try:
            await asyncio.sleep((remind_time - datetime.now()).total_seconds())
            channel = self.client.get_channel(channel_id)
            if channel:
                user = await self.client.fetch_user(user_id)
                embed = discord.Embed(
                    title="Reminder",
                    description=f"{user.mention}, here's your reminder: {reason}",
                    color=0x00FF00
                )
                await channel.send(embed=embed)
        except asyncio.CancelledError:
            pass
        finally:
            if user_id in self.reminder_tasks:
                self.reminder_tasks[user_id] = [task for task in self.reminder_tasks[user_id] if not task.done()]
                
    @commands.command(aliases=['rm'])
    async def remindme(self, ctx, time_str: str, *, reason: str = "No reason provided"):
        """Set a reminder with various time formats"""
        remind_time, cleaned_reason = self.parse_time(time_str, reason)
        
        if not remind_time:
            embed = discord.Embed(
                title="Invalid Time Format",
                description="Please use one of these formats:\n"
                           "• `-rm 20:00 reason` (24h format)\n"
                           "• `-rm 8pm reason` (12h format)\n"
                           "• `-rm 15m reason` (15 minutes, also s/h/d)\n"
                           "• `-rm tomorrow reason` or `-rm tm reason`\n"
                           "• `-rm 15.05 reason` (date)\n"
                           "• `-rm 15.05.26 reason` (date with year)\n"
                           "• `-rm 15.07:15:25 reason` (full datetime)",
                color=0xFF0000
            )
            await ctx.send(embed=embed)
            return
            
        # Don't allow reminders more than a year in the future
        if remind_time > datetime.now() + timedelta(days=365):
            await ctx.send("Reminders cannot be set more than a year in the future.")
            return
            
        # Create and store the reminder task
        if ctx.author.id not in self.reminder_tasks:
            self.reminder_tasks[ctx.author.id] = []
            
        reminder_task = asyncio.create_task(
            self.send_reminder(ctx, ctx.author.id, ctx.channel.id, remind_time, cleaned_reason)
        )
        self.reminder_tasks[ctx.author.id].append(reminder_task)
        
        # Calculate time difference for display
        time_diff = remind_time - datetime.now()
        days = time_diff.days
        hours, remainder = divmod(time_diff.seconds, 3600)
        minutes, seconds = divmod(remainder, 60)
        
        time_parts = []
        if days > 0:
            time_parts.append(f"{days} days")
        if hours > 0:
            time_parts.append(f"{hours} hours")
        if minutes > 0:
            time_parts.append(f"{minutes} minutes")
        if seconds > 0 and not (days or hours or minutes):
            time_parts.append(f"{seconds} seconds")
            
        time_str = ", ".join(time_parts)
        
        embed = discord.Embed(
            title="Reminder Set",
            description=f"I'll remind you in {time_str}\n"
                       f"**Reason:** {cleaned_reason}\n"
                       f"**Time:** <t:{int(remind_time.timestamp())}:F>",
            color=0x00FF00
        )
        await ctx.send(embed=embed)
    
    @commands.command()
    async def afk(self, ctx, *, reason="AFK"):
        """Set your AFK status with an optional reason"""
        current_time = time.time()
        self.afk_users[ctx.author.id] = (reason, current_time, current_time)
        
        embed = discord.Embed(
            description=f"{ctx.author.mention} is now AFK - {reason}",
            color=0x808080
        )
        await ctx.send(embed=embed)
    
    @commands.Cog.listener()
    async def on_message(self, message):
        if message.author.bot:
            return

        # Check if the message author was AFK and is now back
        if message.author.id in self.afk_users:
            reason, afk_timestamp, command_timestamp = self.afk_users[message.author.id]
            
            # Ignore if this is the command message or messages sent within 1 second of the command
            if time.time() - command_timestamp <= 1:
                return
                
            del self.afk_users[message.author.id]
            elapsed = time.time() - afk_timestamp
            minutes = int(elapsed / 60)
            hours = int(minutes / 60)
            
            if hours > 0:
                time_text = f"{hours} hours and {minutes % 60} minutes"
            else:
                time_text = f"{minutes} minutes"
            
            embed = discord.Embed(
                description=f"👋 {message.author.mention} has returned after being AFK for {time_text}",
                color=0x00FF00
            )
            await message.channel.send(embed=embed)
            
        # Check if any mentioned users are AFK
        for mention in message.mentions:
            if mention.id in self.afk_users:
                reason, timestamp, _ = self.afk_users[mention.id]
                elapsed = time.time() - timestamp
                minutes = int(elapsed / 60)
                hours = int(minutes / 60)
                
                if hours > 0:
                    time_text = f"{hours} hours and {minutes % 60} minutes"
                else:
                    time_text = f"{minutes} minutes"
                
                embed = discord.Embed(
                    description=f"{mention.mention} is AFK: {reason} - Been Away for {time_text}",
                    color=0xFF0000
                )
                await message.channel.send(embed=embed)

    @commands.command()
    async def code(self, ctx):
        await ctx.send("zgte5dr6ftgzhujikokztrdeswa536edfr65fm ,WU83 34 FTZFTBFTBF7677U6")
    
    @commands.command()
    async def geschichte(self, ctx):
        await ctx.send("ich habe mal david in migros getroffen und ein foto mit david gemacht. das hat mich glücklich gemacht. dann hatten wir französisch...")
    
    @commands.command()
    async def info(self, ctx):
        embed = discord.Embed(
            title="Leurs: Discord Balance Bot",
            description="A Discord bot for managing balances and other utilities.",
            color=0xFFFFFF
        )
        
        embed.add_field(name="GitHub Repository", value="https://github.com/IM23d/discord-balance-bot", inline=False)
        embed.add_field(name="Developers", value="@bettercallmilan, @FlorianRuby & @seakyy", inline=True)
        embed.add_field(name="Contributors", value="@lhilfiker", inline=True)
        embed.add_field(name="Version", value="1.0.0", inline=True)
        embed.add_field(name="Commands", value="Use `-help` to see all available commands", inline=False)
        
        embed.set_footer(text="Leurs: Discord Balance Bot")
        
        await ctx.send(embed=embed)
        

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

    @commands.command()
    async def hi(self, ctx):
        await ctx.send("Hi I'm coffee!")
    
    @commands.command() # please work git
    async def lyric(self, ctx):
        random_num_lyric = random.randint(1, 7)
        file_path = f"data/{random_num_lyric}.txt" # comment 

        if os.path.exists(file_path):
            with open(file_path, 'r') as file:
                content = file.read()
            await ctx.send(content)
        else:
            await ctx.send("Couldn't find the lyric file")

    @commands.command()
    async def github(self, ctx):
        await ctx.send("https://docs.github.com/en/pull-requests/collaborating-with-pull-requests/proposing-changes-to-your-work-with-pull-requests/creating-a-pull-request")
    
    @commands.command(aliases=['list', 'reminders'])
    async def remindme_list(self, ctx):
        """List all your active reminders"""
        if ctx.author.id not in self.reminder_tasks or not self.reminder_tasks[ctx.author.id]:
            embed = discord.Embed(
                title="Your Reminders",
                description="You don't have any active reminders.",
                color=0x808080
            )
            await ctx.send(embed=embed)
            return

        # Clean up completed tasks first
        self.reminder_tasks[ctx.author.id] = [task for task in self.reminder_tasks[ctx.author.id] if not task.done()]
        
        if not self.reminder_tasks[ctx.author.id]:
            embed = discord.Embed(
                title="Your Reminders",
                description="You don't have any active reminders.",
                color=0x808080
            )
            await ctx.send(embed=embed)
            return

        # Get reminder details from task names
        reminders = []
        now = datetime.now()
        
        for task in self.reminder_tasks[ctx.author.id]:
            # Extract reminder time and reason from the task's internal data
            # The send_reminder coroutine contains these as arguments
            coro = task.get_coro()
            frame = coro.cr_frame
            remind_time = frame.f_locals.get('remind_time')
            reason = frame.f_locals.get('reason')
            
            if remind_time and reason:
                time_diff = remind_time - now
                days = time_diff.days
                hours, remainder = divmod(time_diff.seconds, 3600)
                minutes, seconds = divmod(remainder, 60)
                
                time_parts = []
                if days > 0:
                    time_parts.append(f"{days} days")
                if hours > 0:
                    time_parts.append(f"{hours} hours")
                if minutes > 0:
                    time_parts.append(f"{minutes} minutes")
                if seconds > 0 and not (days or hours or minutes):
                    time_parts.append(f"{seconds} seconds")
                
                time_until = ", ".join(time_parts)
                reminders.append({
                    'time': remind_time,
                    'reason': reason,
                    'time_until': time_until
                })
        
        # Sort reminders by time
        reminders.sort(key=lambda x: x['time'])
        
        # Create embed with reminder list
        embed = discord.Embed(
            title="📝 Your Reminders",
            color=0x00FF00
        )
        
        for i, reminder in enumerate(reminders, 1):
            embed.add_field(
                name=f"Reminder #{i}",
                value=f"**Time:** <t:{int(reminder['time'].timestamp())}:F>\n"
                      f"**Relative:** <t:{int(reminder['time'].timestamp())}:R>\n"
                      f"**Reason:** {reminder['reason']}",
                inline=False
            )
            
        await ctx.send(embed=embed)
    
    def get_font_path(self):
        """Get the font path, downloading it if necessary"""
        # Check if we have a font in data/fonts
        font_path = 'data/fonts/arial.ttf'
        
        # If the font doesn't exist, use a system font
        if not os.path.exists(font_path):
            # Try to use a system font that's likely to exist
            system_fonts = [
                '/usr/share/fonts/TTF/Arial.ttf',  # Linux
                '/usr/share/fonts/truetype/msttcorefonts/Arial.ttf',  # Some Linux
                '/Library/Fonts/Arial.ttf',  # macOS
                'C:\\Windows\\Fonts\\arial.ttf'  # Windows
            ]
            
            for font in system_fonts:
                if os.path.exists(font):
                    return font
            
            # If no system font found, download a free font
            try:
                font_url = "https://github.com/googlefonts/roboto/raw/main/src/hinted/Roboto-Regular.ttf"
                response = requests.get(font_url)
                if response.status_code == 200:
                    os.makedirs(os.path.dirname(font_path), exist_ok=True)
                    with open(font_path, 'wb') as f:
                        f.write(response.content)
                    return font_path
            except Exception as e:
                print(f"Error downloading font: {e}")
            
            # If all else fails, we'll use default font in PIL
            return None
    
    async def create_quote_image(self, avatar_url, message_content, username):
        """Create a quote image with user's avatar and message content"""
        try:
            # Download the user's avatar
            response = requests.get(avatar_url)
            avatar_image = Image.open(io.BytesIO(response.content))
            
            # Create a square image (1:1 aspect ratio)
            size = 1000  # Standard size - we'll scale the image later
            
            # Resize avatar to fill the entire background
            # Calculate dimensions to maintain aspect ratio while filling the square
            width, height = avatar_image.size
            
            # Determine which dimension to use for cropping
            if width > height:
                # Image is wider than tall
                new_width = int(width * size / height)
                new_height = size
                left_crop = (new_width - size) // 2
                top_crop = 0
            else:
                # Image is taller than wide
                new_width = size
                new_height = int(height * size / width)
                left_crop = 0
                top_crop = (new_height - size) // 2
                
            # Resize and crop to fill the square
            avatar_image = avatar_image.resize((new_width, new_height), Image.Resampling.LANCZOS)
            avatar_image = avatar_image.crop((left_crop, top_crop, left_crop + size, top_crop + size))
            
            # Create the base image using the avatar
            quote_img = avatar_image.copy()
            
            # Add a dark overlay to make text more readable
            overlay = Image.new('RGBA', (size, size), (0, 0, 0, 230))  # Very dark overlay
            quote_img = Image.alpha_composite(quote_img.convert('RGBA'), overlay)
            
            # Convert to RGB for final output
            quote_img = quote_img.convert('RGB')
            
            # Create a blank image for the text with transparent background
            text_img = Image.new('RGBA', (size, size), (0, 0, 0, 0))
            draw = ImageDraw.Draw(text_img)
            
            # Try to find a system font that works well
            system_fonts = [
                '/usr/share/fonts/TTF/DejaVuSans-Bold.ttf',  # Linux
                '/usr/share/fonts/truetype/dejavu/DejaVuSans-Bold.ttf',  # Ubuntu
                '/Library/Fonts/Arial Bold.ttf',  # macOS
                'C:\\Windows\\Fonts\\arialbd.ttf',  # Windows
                # Add fallbacks
                '/usr/share/fonts/TTF/Arial.ttf',
                '/usr/share/fonts/truetype/msttcorefonts/Arial.ttf',
                self.font_path
            ]
            
            font_path = None
            for font in system_fonts:
                if font and os.path.exists(font):
                    font_path = font
                    break
            
            # If no font found, we'll have to use default
            if not font_path:
                # Create a simple text overlay with basic text
                draw.text((50, 50), f'"{message_content}"', fill=(255, 255, 255), font=ImageFont.load_default())
                draw.text((50, 100), f"- {username}", fill=(255, 255, 255), font=ImageFont.load_default())
            else:
                # Custom line wrapping function that wraps after 3-5 words
                def wrap_text(text, words_per_line=4):
                    words = text.split()
                    lines = []
                    current_line = []
                    
                    for word in words:
                        current_line.append(word)
                        if len(current_line) >= words_per_line:
                            lines.append(' '.join(current_line))
                            current_line = []
                    
                    # Add any remaining words
                    if current_line:
                        lines.append(' '.join(current_line))
                    
                    return '\n'.join(lines)
                
                # Wrap the text with 3-5 words per line
                wrapped_text = wrap_text(message_content, 4)  # 4 words per line on average
                
                # Add quotation marks
                quote_text = f'"{wrapped_text}"'
                
                # Calculate text size based on image dimensions
                # We'll make the text take up about 80% of the image width
                target_text_width = int(size * 0.8)
                
                # Start with a reasonable size and adjust
                test_size = 20
                max_size = 500
                
                # Find the largest font size that fits within our target width
                font_size = test_size
                for test_size in range(20, max_size, 10):
                    try:
                        test_font = ImageFont.truetype(font_path, test_size)
                        # Check the width of the longest line
                        longest_line = max(wrapped_text.split('\n'), key=len)
                        bbox = draw.textbbox((0, 0), f'"{longest_line}"', font=test_font)
                        if bbox[2] - bbox[0] > target_text_width:
                            break
                        font_size = test_size
                    except Exception:
                        break
                
                try:
                    quote_font = ImageFont.truetype(font_path, font_size)
                    username_font = ImageFont.truetype(font_path, font_size // 2)  # Username half the size
                    
                    # Get text dimensions
                    quote_bbox = draw.textbbox((0, 0), quote_text, font=quote_font)
                    quote_width = quote_bbox[2] - quote_bbox[0]
                    quote_height = quote_bbox[3] - quote_bbox[1]
                    
                    # Center the text
                    quote_x = (size - quote_width) // 2
                    quote_y = (size - quote_height) // 2 - size // 8  # Slightly above center
                    
                    # Draw text with shadow for better visibility
                    shadow_offset = max(3, font_size // 20)  # Scale shadow with font size
                    
                    # Draw shadow
                    for dx, dy in [(shadow_offset, shadow_offset), (-shadow_offset, shadow_offset),
                                  (shadow_offset, -shadow_offset), (-shadow_offset, -shadow_offset)]:
                        draw.text((quote_x + dx, quote_y + dy), quote_text, fill=(0, 0, 0), font=quote_font)
                    
                    # Draw main text
                    draw.text((quote_x, quote_y), quote_text, fill=(255, 255, 255), font=quote_font)
                    
                    # Add username
                    username_text = f"- {username}"
                    username_bbox = draw.textbbox((0, 0), username_text, font=username_font)
                    username_width = username_bbox[2] - username_bbox[0]
                    
                    # Position username at bottom right
                    username_x = size - username_width - (size // 20)
                    username_y = size - (size // 5)
                    
                    # Draw username shadow
                    for dx, dy in [(shadow_offset//2, shadow_offset//2), (-shadow_offset//2, shadow_offset//2),
                                  (shadow_offset//2, -shadow_offset//2), (-shadow_offset//2, -shadow_offset//2)]:
                        draw.text((username_x + dx, username_y + dy), username_text, fill=(0, 0, 0), font=username_font)
                    
                    # Draw username
                    draw.text((username_x, username_y), username_text, fill=(255, 255, 255), font=username_font)
                    
                except Exception:
                    # Fallback to basic text
                    draw.text((50, 50), f'"{message_content}"', fill=(255, 255, 255), font=ImageFont.load_default())
                    draw.text((50, 100), f"- {username}", fill=(255, 255, 255), font=ImageFont.load_default())
            
            # Composite the text onto the background
            quote_img = Image.alpha_composite(quote_img.convert('RGBA'), text_img)
            
            # IMPORTANT: Scale up the final image to ensure it's large enough
            final_size = 2000  # Final output size
            quote_img = quote_img.resize((final_size, final_size), Image.Resampling.LANCZOS)
            
            # Save the image to a bytes buffer
            buffer = io.BytesIO()
            quote_img.convert('RGB').save(buffer, format='PNG')
            buffer.seek(0)
            
            return buffer
        except Exception as e:
            return None
    
    @commands.command()
    async def quote(self, ctx):
        """Create a quote image from a replied message"""
        try:
            # Send a temporary confirmation message
            temp_msg = await ctx.send("Generating quote image...")
            
            # Check if the command is replying to a message
            if not ctx.message.reference:
                await temp_msg.edit(content="You need to reply to a message to quote it!")
                return
            
            # Get the message being replied to
            try:
                replied_msg = await ctx.channel.fetch_message(ctx.message.reference.message_id)
            except discord.NotFound:
                await temp_msg.edit(content="I couldn't find the message you're replying to.")
                return
            except Exception:
                await temp_msg.edit(content="Error fetching the message.")
                return
            
            # Get the message author's avatar URL
            avatar_url = replied_msg.author.display_avatar.url
            
            # Create the quote image
            image_buffer = await self.create_quote_image(
                avatar_url, 
                replied_msg.content, 
                replied_msg.author.display_name
            )
            
            if image_buffer:
                # Send the image
                await ctx.send(file=discord.File(fp=image_buffer, filename='quote.png'))
                # Delete the temporary message
                await temp_msg.delete()
            else:
                await temp_msg.edit(content="Failed to create quote image.")
        except Exception:
            await ctx.send("An error occurred while creating the quote image.")
    
    @commands.command(aliases=['av'])
    async def avatar(self, ctx, member: discord.Member = None):
        """Display a user's global avatar in high quality"""
        # If no member is specified, use the command author
        member = member or ctx.author
        
        # Create an embed with the avatar
        embed = discord.Embed(
            title=f"{member.display_name}'s Avatar",
            color=0x00FFFF
        )
        
        # Get the global avatar URL with maximum size (4096)
        avatar_url = member.avatar.with_size(4096).url if member.avatar else member.default_avatar.url
        
        # Set the image in the embed
        embed.set_image(url=avatar_url)
        
        await ctx.send(embed=embed)
    
    @commands.command(aliases=['sav'])
    async def serveravatar(self, ctx, member: discord.Member = None):
        """Display a user's server-specific avatar in high quality"""
        # If no member is specified, use the command author
        member = member or ctx.author
        
        # Check if the user has a server-specific avatar
        if not member.guild_avatar:
            await ctx.send(f"{member.display_name} doesn't have a server-specific avatar.")
            return
        
        # Create an embed with the server avatar
        embed = discord.Embed(
            title=f"{member.display_name}'s Server Avatar",
            color=0x00FFFF
        )
        
        # Get the server avatar URL with maximum size (4096)
        avatar_url = member.guild_avatar.with_size(4096).url
        
        # Set the image in the embed
        embed.set_image(url=avatar_url)
        
        await ctx.send(embed=embed)
    
    @commands.command()
    async def banner(self, ctx, user: discord.User = None):
        """Display a user's banner in high quality"""
        # If no user is specified, use the command author
        user = user or ctx.author
        
        # Fetch the user to get the banner info
        try:
            user = await self.client.fetch_user(user.id)
            
            # Check if the user has a banner
            if not user.banner:
                await ctx.send(f"{user.display_name} doesn't have a banner.")
                return
            
            # Create an embed with the banner
            embed = discord.Embed(
                title=f"{user.display_name}'s Banner",
                color=0x00FFFF
            )
            
            # Get the banner URL with maximum size (4096)
            banner_url = user.banner.with_size(4096).url
            
            # Set the image in the embed
            embed.set_image(url=banner_url)
            
            await ctx.send(embed=embed)
        except Exception as e:
            await ctx.send(f"Error fetching banner: {str(e)}")
    
    @commands.command()
    async def sbanner(self, ctx, member: discord.Member = None):
        """Display a user's server banner in high quality"""
        # If no member is specified, use the command author
        member = member or ctx.author
        
        try:
            # Check if the user has a server banner
            if not hasattr(member, 'guild_banner') or not member.guild_banner:
                await ctx.send(f"{member.display_name} doesn't have a server banner.")
                return
            
            # Create an embed with the server banner
            embed = discord.Embed(
                title=f"{member.display_name}'s Server Banner",
                color=0x00FFFF
            )
            
            # Get the server banner URL with maximum size (4096)
            banner_url = member.guild_banner.with_size(4096).url
            
            # Set the image in the embed
            embed.set_image(url=banner_url)
            
            await ctx.send(embed=embed)
        except Exception as e:
            await ctx.send(f"Error fetching server banner: {str(e)}")
    