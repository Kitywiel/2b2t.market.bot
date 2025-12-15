import discord
from discord import app_commands
from discord.ext import commands
import json
import os
from datetime import datetime


class Chat(commands.Cog):
    def __init__(self, bot):
        self.bot = bot
        self.config_file = 'chat_config.json'
        self.load_data()

    def load_data(self):
        """Load chat config data from JSON file"""
        if os.path.exists(self.config_file):
            with open(self.config_file, 'r') as f:
                self.config = json.load(f)
        else:
            self.config = {}
            self.save_config()
    
    def save_config(self):
        """Save config data to JSON file"""
        with open(self.config_file, 'w') as f:
            json.dump(self.config, f, indent=4)

    @commands.Cog.listener()
    async def on_message(self, message):
        """Listen for messages starting with . in the watch channel"""
        if message.author.bot:
            return
        
        if not message.guild:
            return
        
        guild_id_str = str(message.guild.id)
        config = self.config.get(guild_id_str, {})
        
        watch_channel_id = config.get('watch_channel_id')
        forward_channel_id = config.get('forward_channel_id')
        
        if not watch_channel_id or not forward_channel_id:
            return
        
        if message.channel.id != watch_channel_id:
            return
        
        if not message.content.startswith('.'):
            return
        
        forward_channel = message.guild.get_channel(forward_channel_id)
        if not forward_channel:
            return
        
        try:
            # If the message has embeds, forward them
            if message.embeds:
                for embed in message.embeds:
                    await forward_channel.send(embed=embed)
            else:
                # Create embed from text message
                embed = discord.Embed(
                    description=message.content,
                    color=discord.Color.blue()
                )
                embed.set_author(name=message.author.name, icon_url=message.author.display_avatar.url)
                embed.timestamp = message.created_at
                
                await forward_channel.send(embed=embed)
        except Exception as e:
            print(f"Error forwarding message: {e}")

    @app_commands.command(name='setupchat', description='Setup the chat forwarding system')
    @app_commands.describe(
        watch_channel='Channel to watch for dot commands',
        forward_channel='Channel to forward dot messages to'
    )
    @app_commands.checks.has_permissions(administrator=True)
    async def setup_chat(self, interaction: discord.Interaction, watch_channel: discord.TextChannel, forward_channel: discord.TextChannel):
        await interaction.response.defer()
        
        try:
            guild_id_str = str(interaction.guild.id)
            
            if guild_id_str not in self.config:
                self.config[guild_id_str] = {}
            
            self.config[guild_id_str]['watch_channel_id'] = watch_channel.id
            self.config[guild_id_str]['forward_channel_id'] = forward_channel.id
            
            self.save_config()
            
            embed = discord.Embed(
                title="✅ Chat Forwarding Configured",
                description="The chat forwarding system has been set up!",
                color=discord.Color.green()
            )
            embed.add_field(name="👀 Watch Channel", value=watch_channel.mention, inline=False)
            embed.add_field(name="📨 Forward Channel", value=forward_channel.mention, inline=False)
            embed.add_field(
                name="How it works",
                value="Messages starting with `.` in the watch channel will be forwarded to the forward channel.",
                inline=False
            )
            
            await interaction.followup.send(embed=embed)
        
        except Exception as e:
            import traceback
            error_details = ''.join(traceback.format_exception(type(e), e, e.__traceback__))
            
            if len(error_details) > 1000:
                error_details = error_details[-1000:]
            
            embed = discord.Embed(
                title="❌ Error in Setup",
                description=f"**Error Type:** `{type(e).__name__}`\n**Error Message:** {str(e)}",
                color=discord.Color.red()
            )
            embed.add_field(name="Full Error Details", value=f"```python\n{error_details}\n```", inline=False)
            
            await interaction.followup.send(embed=embed, ephemeral=True)


async def setup(bot):
    await bot.add_cog(Chat(bot))
