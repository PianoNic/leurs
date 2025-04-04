import discord
from discord.ext import commands
import random
import datetime
from typing import Dict, List
from database import db

class JobMarketView(discord.ui.View):
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
        # Get all available jobs
        all_jobs = await self.cog.get_all_jobs()
        
        # Calculate total pages
        jobs_per_page = 3
        total_jobs = len(all_jobs)
        total_pages = (total_jobs + jobs_per_page - 1) // jobs_per_page
        
        # Ensure page is within valid range
        new_page = max(1, min(new_page, total_pages))
        
        # Get jobs for current page
        start_idx = (new_page - 1) * jobs_per_page
        end_idx = min(start_idx + jobs_per_page, total_jobs)
        current_jobs = all_jobs[start_idx:end_idx]
        
        user_id = str(self.ctx.author.id)
        user_jobs = await self.cog.get_user_jobs(user_id)
        
        embed = discord.Embed(
            title="📋 Job Market",
            description=f"Here are all available jobs (Page {new_page}/{total_pages}):",
            color=discord.Color.blue()
        )
        
        for job in current_jobs:
            job_name = job['name']
            status = "✅ Unlocked" if job_name in user_jobs else "🔒 Locked"
            value = f"Base Pay: {job['base_pay']} coins\n"
            value += f"Bonus Chance: {float(job['bonus_chance'])*100}%\n"
            value += f"Bonus Amount: {job['bonus_amount']} coins"
            if job_name not in user_jobs:
                value += f"\nCost to Unlock: {job['cost']} coins"
            
            embed.add_field(
                name=f"{status} {job_name}",
                value=value,
                inline=False
            )
        
        embed.add_field(
            name="📝 Commands",
            value="`-buyjob <job>` - Purchase a job to unlock it\n"
                  "`-work <job>` - Work at a job you've unlocked\n"
                  "`-jobs` - View this job market",
            inline=False
        )
        
        embed.set_footer(text="Work once per day to earn coins!")
        
        # Create new view for the updated page
        new_view = JobMarketView(self.cog, self.ctx, new_page, total_pages)
        new_view.message = self.message
        
        # Update the message
        await self.message.edit(embed=embed, view=new_view)

    async def prev_callback(self, interaction: discord.Interaction):
        await interaction.response.defer()
        await self.update_page(self.page - 1)

    async def next_callback(self, interaction: discord.Interaction):
        await interaction.response.defer()
        await self.update_page(self.page + 1)

class JobMarketCog(commands.Cog):
    def __init__(self, client):
        self.client = client
    
    async def get_all_jobs(self):
        """Get all available jobs from the database."""
        jobs = await db.fetch('''
            SELECT * FROM jobs ORDER BY name
        ''')
        
        return [dict(job) for job in jobs]
    
    async def get_user_jobs(self, user_id):
        """Get list of jobs unlocked by a specific user."""
        rows = await db.fetch('''
            SELECT job_name FROM user_jobs 
            WHERE user_id = $1
        ''', int(user_id))
        
        return [row['job_name'] for row in rows]
    
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
    async def jobs(self, ctx, page: int = 1):
        """Display available jobs in the job market."""
        await self.open_account(ctx.author)
        
        # Get all available jobs
        all_jobs = await self.get_all_jobs()
        
        # Calculate total pages
        jobs_per_page = 3
        total_jobs = len(all_jobs)
        total_pages = (total_jobs + jobs_per_page - 1) // jobs_per_page
        
        # Ensure page is within valid range
        page = max(1, min(page, total_pages))
        
        # Get jobs for current page
        start_idx = (page - 1) * jobs_per_page
        end_idx = min(start_idx + jobs_per_page, total_jobs)
        current_jobs = all_jobs[start_idx:end_idx]
        
        user_id = str(ctx.author.id)
        user_jobs = await self.get_user_jobs(user_id)
        
        embed = discord.Embed(
            title="📋 Job Market",
            description=f"Here are all available jobs (Page {page}/{total_pages}):",
            color=discord.Color.blue()
        )
        
        for job in current_jobs:
            job_name = job['name']
            status = "✅ Unlocked" if job_name in user_jobs else "🔒 Locked"
            value = f"Base Pay: {job['base_pay']} coins\n"
            value += f"Bonus Chance: {float(job['bonus_chance'])*100}%\n"
            value += f"Bonus Amount: {job['bonus_amount']} coins"
            if job_name not in user_jobs:
                value += f"\nCost to Unlock: {job['cost']} coins"
            
            embed.add_field(
                name=f"{status} {job_name}",
                value=value,
                inline=False
            )
        
        embed.add_field(
            name="📝 Commands",
            value="`-buyjob <job>` - Purchase a job to unlock it\n"
                  "`-work <job>` - Work at a job you've unlocked\n"
                  "`-jobs` - View this job market",
            inline=False
        )
        
        embed.set_footer(text="Work once per day to earn coins!")
        
        # Create view with navigation buttons
        view = JobMarketView(self, ctx, page, total_pages)
        
        # Send or update the message
        if not hasattr(view, 'message'):
            view.message = await ctx.send(embed=embed, view=view)
        else:
            await view.message.edit(embed=embed, view=view)

    @commands.command()
    async def buyjob(self, ctx, *, job_name: str = None):
        """Purchase a job to unlock it."""
        await self.open_account(ctx.author)
        
        if not job_name:
            embed = discord.Embed(
                title="Error",
                description="Please specify a job to purchase. Use -jobs to see available jobs.",
                color=discord.Color.red()
            )
            await ctx.send(embed=embed)
            return
            
        # Standardize job name (first letter of each word uppercase)
        job_name = '-'.join(word.title() for word in job_name.split('-'))
        
        # Check if the job exists
        job = await db.fetchrow('''
            SELECT * FROM jobs WHERE name = $1
        ''', job_name)
        
        if not job:
            embed = discord.Embed(
                title="Error",
                description=f"'{job_name}' is not a valid job. Use -jobs to see available jobs.",
                color=discord.Color.red()
            )
            await ctx.send(embed=embed)
            return
            
        user_id = ctx.author.id
        user_jobs = await self.get_user_jobs(str(user_id))
        
        if job_name in user_jobs:
            embed = discord.Embed(
                title="Error",
                description=f"You already have the {job_name} job unlocked!",
                color=discord.Color.red()
            )
            await ctx.send(embed=embed)
            return
            
        # Check if user has reached the maximum number of jobs
        if len(user_jobs) >= 3:
            embed = discord.Embed(
                title="Error",
                description="You can only have a maximum of 3 jobs at a time! Use `-removejob <job>` to remove a job before buying a new one.",
                color=discord.Color.red()
            )
            await ctx.send(embed=embed)
            return
            
        # Get user's account and check if they have enough money
        account = await self.get_account(user_id)
        
        if account['wallet'] < job['cost']:
            embed = discord.Embed(
                title="Error",
                description=f"You don't have enough coins! You need {job['cost']} coins to unlock this job.",
                color=discord.Color.red()
            )
            await ctx.send(embed=embed)
            return
            
        # Purchase the job using transaction
        async with db.pool.acquire() as conn:
            async with conn.transaction():
                # Deduct cost from wallet
                await conn.execute('''
                    UPDATE bank_accounts 
                    SET wallet = wallet - $1
                    WHERE user_id = $2
                ''', job['cost'], user_id)
                
                # Add job to user's jobs
                await conn.execute('''
                    INSERT INTO user_jobs (user_id, job_name)
                    VALUES ($1, $2)
                    ON CONFLICT (user_id, job_name) DO NOTHING
                ''', user_id, job_name)
        
        # Get updated wallet and jobs list
        updated_account = await self.get_account(user_id)
        updated_jobs = await self.get_user_jobs(str(user_id))
            
        embed = discord.Embed(
            title="🎉 Job Unlocked!",
            description=f"Congratulations! You've unlocked the {job_name} job!",
            color=discord.Color.green()
        )
        
        embed.add_field(
            name="New Wallet Balance",
            value=f"{updated_account['wallet']} coins",
            inline=False
        )
        
        embed.add_field(
            name="Current Jobs",
            value="\n".join(updated_jobs),
            inline=False
        )
        
        embed.set_footer(text=f"Requested by {ctx.author.name}", 
                        icon_url=ctx.author.avatar.url if ctx.author.avatar else ctx.author.default_avatar.url)
        embed.timestamp = datetime.datetime.utcnow()
        
        await ctx.send(embed=embed)

    @commands.command()
    async def removejob(self, ctx, *, job_name: str = None):
        """Remove a job from your current jobs."""
        await self.open_account(ctx.author)
        
        if not job_name:
            embed = discord.Embed(
                title="Error",
                description="Please specify a job to remove. Use -jobs to see your current jobs.",
                color=discord.Color.red()
            )
            await ctx.send(embed=embed)
            return
            
        # Standardize job name
        job_name = '-'.join(word.title() for word in job_name.split('-'))
        
        user_id = ctx.author.id
        user_jobs = await self.get_user_jobs(str(user_id))
        
        if job_name not in user_jobs:
            embed = discord.Embed(
                title="Error",
                description=f"You don't have the {job_name} job!",
                color=discord.Color.red()
            )
            await ctx.send(embed=embed)
            return
            
        # Remove the job
        await db.execute('''
            DELETE FROM user_jobs
            WHERE user_id = $1 AND job_name = $2
        ''', user_id, job_name)
        
        # Get updated jobs list
        updated_jobs = await self.get_user_jobs(str(user_id))
        
        embed = discord.Embed(
            title="🗑️ Job Removed",
            description=f"You've removed the {job_name} job from your current jobs.",
            color=discord.Color.blue()
        )
        
        embed.add_field(
            name="Current Jobs",
            value="\n".join(updated_jobs) if updated_jobs else "No jobs",
            inline=False
        )
        
        embed.set_footer(text=f"Requested by {ctx.author.name}", 
                        icon_url=ctx.author.avatar.url if ctx.author.avatar else ctx.author.default_avatar.url)
        embed.timestamp = datetime.datetime.utcnow()
        
        await ctx.send(embed=embed)

    @commands.command()
    @commands.cooldown(1, 86400, commands.BucketType.user)  # 24 hour cooldown
    async def work(self, ctx):
        """Work at all your jobs to earn money."""
        await self.open_account(ctx.author)
        
        user_id = ctx.author.id
        user_jobs = await self.get_user_jobs(str(user_id))
        
        if not user_jobs:
            embed = discord.Embed(
                title="Error",
                description="You don't have any jobs! Use -jobs to see available jobs.",
                color=discord.Color.red()
            )
            await ctx.send(embed=embed)
            return
            
        total_earnings = 0
        earnings_breakdown = []
        
        # Get job info for each user job
        for job_name in user_jobs:
            job = await db.fetchrow('''
                SELECT * FROM jobs
                WHERE name = $1
            ''', job_name)
            
            if job:
                # Calculate earnings for this job
                earnings = job['base_pay']
                bonus_earned = 0
                
                # Check for bonus
                if random.random() < float(job['bonus_chance']):
                    bonus_earned = job['bonus_amount']
                    earnings += bonus_earned
                    earnings_breakdown.append(f"🎉 {job_name}: {job['base_pay']} coins + {bonus_earned} coins bonus")
                else:
                    earnings_breakdown.append(f"{job_name}: {earnings} coins")
                
                total_earnings += earnings
        
        # Update user's wallet and last_work timestamp
        await db.execute('''
            UPDATE bank_accounts 
            SET wallet = wallet + $1, last_work = $2
            WHERE user_id = $3
        ''', total_earnings, datetime.datetime.utcnow(), user_id)
        
        # Get updated account info
        updated_account = await self.get_account(user_id)
            
        # Create and send embed
        embed = discord.Embed(
            title="💼 Work Results",
            description=f"You worked at your jobs and earned a total of {total_earnings} coins!",
            color=discord.Color.green()
        )
        
        embed.add_field(
            name="Earnings Breakdown",
            value="\n".join(earnings_breakdown),
            inline=False
        )
        
        embed.add_field(
            name="New Wallet Balance",
            value=f"{updated_account['wallet']} coins",
            inline=False
        )
        
        embed.set_footer(text=f"Requested by {ctx.author.name}", 
                        icon_url=ctx.author.avatar.url if ctx.author.avatar else ctx.author.default_avatar.url)
        embed.timestamp = datetime.datetime.utcnow()
        
        await ctx.send(embed=embed)

    @work.error
    async def work_error(self, ctx, error):
        if isinstance(error, commands.CommandOnCooldown):
            hours, remainder = divmod(error.retry_after, 3600)
            minutes, seconds = divmod(remainder, 60)
            
            embed = discord.Embed(
                title="⏰ Cooldown Active",
                description="You've already worked today!",
                color=discord.Color.red()
            )
            
            embed.add_field(
                name="Time Remaining",
                value=f"{int(hours)}h {int(minutes)}m {int(seconds)}s",
                inline=False
            )
            
            embed.set_footer(text=f"Requested by {ctx.author.name}", 
                           icon_url=ctx.author.avatar.url if ctx.author.avatar else ctx.author.default_avatar.url)
            embed.timestamp = datetime.datetime.utcnow()
            
            await ctx.send(embed=embed)
        else:
            embed = discord.Embed(
                title="Error",
                description=f"An unexpected error occurred: {str(error)}",
                color=discord.Color.red()
            )
            await ctx.send(embed=embed)

    @commands.command()
    async def myjobs(self, ctx):
        """Display your currently owned jobs."""
        await self.open_account(ctx.author)
        
        user_id = str(ctx.author.id)
        user_jobs = await self.get_user_jobs(user_id)
        
        if not user_jobs:
            embed = discord.Embed(
                title="💼 Your Jobs",
                description="You don't have any jobs yet! Use `-jobs` to see available jobs and `-buyjob <job>` to purchase one.",
                color=discord.Color.blue()
            )
            embed.set_footer(text=f"Requested by {ctx.author.name}", 
                           icon_url=ctx.author.avatar.url if ctx.author.avatar else ctx.author.default_avatar.url)
            embed.timestamp = datetime.datetime.utcnow()
            await ctx.send(embed=embed)
            return
            
        embed = discord.Embed(
            title="💼 Your Jobs",
            description=f"You currently have {len(user_jobs)} job(s):",
            color=discord.Color.blue()
        )
        
        for job_name in user_jobs:
            job = await db.fetchrow('''
                SELECT * FROM jobs
                WHERE name = $1
            ''', job_name)
            
            if job:
                value = f"Base Pay: {job['base_pay']} coins\n"
                value += f"Bonus Chance: {float(job['bonus_chance'])*100}%\n"
                value += f"Bonus Amount: {job['bonus_amount']} coins"
                
                embed.add_field(
                    name=f"✅ {job_name}",
                    value=value,
                    inline=False
                )
        
        embed.add_field(
            name="📝 Commands",
            value="`-work` - Work at all your jobs\n"
                  "`-removejob <job>` - Remove a job from your list\n"
                  "`-jobs` - View the job market",
            inline=False
        )
        
        embed.set_footer(text=f"Requested by {ctx.author.name}", 
                        icon_url=ctx.author.avatar.url if ctx.author.avatar else ctx.author.default_avatar.url)
        embed.timestamp = datetime.datetime.utcnow()
        
        await ctx.send(embed=embed)

async def setup(client):
    await client.add_cog(JobMarketCog(client))