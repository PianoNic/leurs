import discord
from discord.ext import commands
import requests
import io
from PIL import Image, ImageDraw, ImageFont
import textwrap
import os
import traceback

class QuoteCog(commands.Cog):
    def __init__(self, bot):
        self.bot = bot
        # Create fonts directory if it doesn't exist
        os.makedirs('data/fonts', exist_ok=True)
        
        # Font paths - we'll use default fonts if custom ones aren't available
        self.font_path = self.get_font_path()
        print(f"Font path: {self.font_path}")
        
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
            print(f"Creating quote image with avatar URL: {avatar_url}")
            print(f"Message content: {message_content}")
            print(f"Username: {username}")
            
            # Download the user's avatar
            response = requests.get(avatar_url)
            print(f"Avatar download status: {response.status_code}")
            avatar_image = Image.open(io.BytesIO(response.content))
            
            # Resize avatar to 128x128 pixels
            avatar_image = avatar_image.resize((128, 128))
            
            # Make avatar circular by creating a mask
            mask = Image.new('L', (128, 128), 0)
            draw = ImageDraw.Draw(mask)
            draw.ellipse((0, 0, 128, 128), fill=255)
            
            # Apply mask to avatar
            circular_avatar = Image.new('RGBA', (128, 128))
            circular_avatar.paste(avatar_image, (0, 0), mask)
            
            # Prepare the quote text
            # Wrap text to fit in the image
            wrapper = textwrap.TextWrapper(width=40)
            wrapped_text = wrapper.fill(message_content)
            
            # Calculate image dimensions based on text length
            text_lines = wrapped_text.count('\n') + 1
            img_height = max(200, 150 + (text_lines * 30))
            
            # Create a new image with white background
            quote_img = Image.new('RGB', (600, img_height), (255, 255, 255))
            draw = ImageDraw.Draw(quote_img)
            
            # Load font
            try:
                font = ImageFont.truetype(self.font_path, 20) if self.font_path else ImageFont.load_default()
                username_font = ImageFont.truetype(self.font_path, 24) if self.font_path else ImageFont.load_default()
                print(f"Loaded fonts successfully")
            except Exception as e:
                print(f"Error loading font: {e}")
                font = ImageFont.load_default()
                username_font = ImageFont.load_default()
            
            # Add avatar to the image
            quote_img.paste(circular_avatar, (20, 20), circular_avatar)
            
            # Add username
            draw.text((170, 30), username, fill=(0, 0, 0), font=username_font)
            
            # Add message content
            draw.text((170, 80), wrapped_text, fill=(0, 0, 0), font=font)
            
            # Save the image to a bytes buffer
            buffer = io.BytesIO()
            quote_img.save(buffer, format='PNG')
            buffer.seek(0)
            print("Image created and saved to buffer successfully")
            
            return buffer
        except Exception as e:
            print(f"Error in create_quote_image: {e}")
            traceback.print_exc()
            return None
    
    @commands.command()
    async def quote(self, ctx):
        """Create a quote image from a replied message"""
        try:
            await ctx.send("Quote command received, processing...")
            
            # Check if the command is replying to a message
            if not ctx.message.reference:
                await ctx.send("You need to reply to a message to quote it!")
                return
            
            await ctx.send(f"Found reference message ID: {ctx.message.reference.message_id}")
            
            # Get the message being replied to
            try:
                replied_msg = await ctx.channel.fetch_message(ctx.message.reference.message_id)
                await ctx.send(f"Found message from: {replied_msg.author.display_name}")
                await ctx.send(f"Message content: {replied_msg.content[:100]}...")
            except discord.NotFound:
                await ctx.send("I couldn't find the message you're replying to.")
                return
            except Exception as e:
                await ctx.send(f"Error fetching message: {str(e)}")
                return
            
            # Get the message author's avatar URL
            avatar_url = replied_msg.author.display_avatar.url
            await ctx.send(f"Avatar URL: {avatar_url}")
            
            # Create the quote image
            await ctx.send("Creating quote image...")
            image_buffer = await self.create_quote_image(
                avatar_url, 
                replied_msg.content, 
                replied_msg.author.display_name
            )
            
            if image_buffer:
                # Send the image
                await ctx.send("Image created, sending...")
                await ctx.send(file=discord.File(fp=image_buffer, filename='quote.png'))
            else:
                await ctx.send("Failed to create quote image.")
        except Exception as e:
            await ctx.send(f"Error in quote command: {str(e)}")
            traceback.print_exc()

async def setup(bot):
    await bot.add_cog(QuoteCog(bot)) 