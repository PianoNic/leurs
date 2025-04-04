import discord
from discord.ext import commands
import datetime
import math
from database import db

class BalanceLeaderboardView(discord.ui.View):
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
        user_list = await self.cog.get_leaderboard_data()
        
        # Paginate results (10 per page)
        total_pages = max(1, math.ceil(len(user_list) / 10))
        
        # Ensure page is within valid range
        new_page = max(1, min(new_page, total_pages))
        
        start_idx = (new_page - 1) * 10
        end_idx = min(start_idx + 10, len(user_list))
        
        # Create embed
        embed = discord.Embed(
            title=f"💰 Balance Leaderboard",
            description=f"Top members ranked by total wealth.",
            color=discord.Color.gold()
        )
        
        # Add leaderboard entries
        if not user_list:
            embed.description = "No users have any money yet!"
        else:
            # Get rank emojis for top 3
            rank_emoji = {0: "🥇", 1: "🥈", 2: "🥉"}
            
            for idx, user_data in enumerate(user_list[start_idx:end_idx], start=start_idx + 1):
                member = user_data["member"]
                user_id = user_data["id"]
                position = idx - 1 + start_idx  # Zero-based position
                
                # Get appropriate emoji based on rank
                prefix = rank_emoji.get(position, f"{idx}.")
                
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
                field_value = f"**{user_data['total']} coins**"
                
                embed.add_field(name=field_name, value=field_value, inline=False)
                
                # Show first-place user as thumbnail
                if position == 0 and icon_url:
                    embed.set_thumbnail(url=icon_url)
        
        embed.set_footer(text=f"Page {new_page}/{total_pages} • Requested by {self.ctx.author.name}", 
                         icon_url=self.ctx.author.avatar.url if self.ctx.author.avatar else self.ctx.author.default_avatar.url)
        embed.timestamp = datetime.datetime.utcnow()
        
        # Create new view with updated page
        new_view = BalanceLeaderboardView(self.cog, self.ctx, new_page, total_pages)
        new_view.message = self.message
        
        # Update the message
        await self.message.edit(embed=embed, view=new_view)

    async def prev_callback(self, interaction: discord.Interaction):
        await interaction.response.defer()
        await self.update_page(self.page - 1)

    async def next_callback(self, interaction: discord.Interaction):
        await interaction.response.defer()
        await self.update_page(self.page + 1)

class EconomyCog(commands.Cog):
    def __init__(self, client):
        self.client = client
        
    @commands.command()
    async def balance(self, ctx):
        await self.open_account(ctx.author)
        
        # Get user's bank account
        account = await self.get_account(ctx.author.id)
        wallet_amt = account['wallet']
        bank_amt = account['bank']

        em = discord.Embed(title=f"{ctx.author.name}'s balance", color=discord.Color.from_rgb(255, 255, 255))
        em.add_field(name="Wallet balance", value=wallet_amt)
        em.add_field(name="Bank balance", value=bank_amt)
        await ctx.send(embed=em)

    @commands.command()
    async def bal(self, ctx):
        await self.balance(ctx)

    @commands.command()
    async def dep(self, ctx, amount=None):
        await self.deposit(ctx, amount)

    @commands.command()
    async def wit(self, ctx, amount=None):
        await self.withdraw(ctx, amount)

    @commands.command()
    @commands.cooldown(1, 86400, commands.BucketType.user)  # 1 day cooldown
    async def beg(self, ctx):
        import random
        
        await self.open_account(ctx.author)
        account = await self.get_account(ctx.author.id)
        
        earnings = random.randrange(101)  # amount the user gets for -beg = max 101
        
        embed = discord.Embed(
            title="Begging Results",
            description=f"Diddy gave you **{earnings} coins**!",
            color=discord.Color.green()
        )
        
        embed.set_thumbnail(url=ctx.author.avatar.url if ctx.author.avatar else ctx.author.default_avatar.url)
        
        new_balance = account['wallet'] + earnings
        embed.add_field(
            name="New Wallet Balance", 
            value=f"{new_balance} coins",
            inline=False
        )
        
        embed.set_footer(text=f"Requested by {ctx.author.name}", icon_url=ctx.author.avatar.url if ctx.author.avatar else ctx.author.default_avatar.url)
        embed.timestamp = datetime.datetime.utcnow()
        
        await ctx.send(embed=embed)
        
        # Update user's wallet in the database
        await self.update_balance(ctx.author.id, 'wallet', earnings)

    @beg.error  # error handling for -beg
    async def beg_error(self, ctx, error):
        if isinstance(error, commands.CommandOnCooldown):
            hours, remainder = divmod(error.retry_after, 3600)
            minutes, seconds = divmod(remainder, 60)
            
            embed = discord.Embed(
                title="Cooldown Active",
                description="You've already begged recently!",
                color=discord.Color.red()
            )
            
            embed.add_field(
                name="Time Remaining",
                value=f"{int(hours)}h {int(minutes)}m {int(seconds)}s",
                inline=False
            )
                        
            embed.set_footer(text=f"Requested by {ctx.author.name}", icon_url=ctx.author.avatar.url if ctx.author.avatar else ctx.author.default_avatar.url)
            embed.timestamp = datetime.datetime.utcnow()
            
            await ctx.send(embed=embed)
        else:
            embed = discord.Embed(
                title="Error Occurred",
                description=f"An unexpected error happened: {str(error)}",
                color=discord.Color.dark_red()
            )
            embed.set_footer(text="Please report this to the admins")
            await ctx.send(embed=embed)
    
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
    
    async def update_balance(self, user_id, balance_type, amount):
        """Update a user's balance."""
        if balance_type not in ['wallet', 'bank']:
            raise ValueError("balance_type must be 'wallet' or 'bank'")
            
        await db.execute(f'''
            UPDATE bank_accounts 
            SET {balance_type} = {balance_type} + $1
            WHERE user_id = $2
        ''', amount, user_id)
        
    async def set_balance(self, user_id, balance_type, amount):
        """Set a user's balance to a specific amount."""
        if balance_type not in ['wallet', 'bank']:
            raise ValueError("balance_type must be 'wallet' or 'bank'")
            
        await db.execute(f'''
            UPDATE bank_accounts 
            SET {balance_type} = $1
            WHERE user_id = $2
        ''', amount, user_id)
    
    async def get_leaderboard_data(self):
        """Get leaderboard data sorted by total wealth."""
        # Get all user accounts from the database
        rows = await db.fetch('''
            SELECT user_id, wallet, bank, (wallet + bank) as total
            FROM bank_accounts
            ORDER BY total DESC
        ''')
        
        user_list = []
        
        # Process the user data 
        for row in rows:
            try:
                # Try to get the member object 
                member = self.client.get_user(int(row['user_id']))
                
                # Create user entry
                user_entry = {
                    "id": str(row['user_id']),
                    "wallet": row['wallet'],
                    "bank": row['bank'],
                    "total": row['total'],
                    "member": member
                }
                user_list.append(user_entry)
            except Exception as e:
                continue
        
        return user_list