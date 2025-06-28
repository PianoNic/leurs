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

class OtherCog(commands.Cog):
    def __init__(self, client):
        self.client = client
        self.afk_users = {}  # Store user_id: (reason, timestamp, command_timestamp)
        self.reminder_tasks = {}  # Store user_id: list of asyncio tasks
    
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
    