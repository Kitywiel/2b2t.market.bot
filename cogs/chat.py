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
            
            # Migrate old format to new format
            for guild_id, data in list(self.config.items()):
                if isinstance(data, dict) and 'watch_channel_id' in data:
                    # Old format: convert to list
                    self.config[guild_id] = [{
                        'watch_channel_id': data['watch_channel_id'],
                        'forward_channel_id': data['forward_channel_id']
                    }]
                    self.save_config()
        else:
            self.config = {}
            self.save_config()
    
    def save_config(self):
        """Save config data to JSON file"""
        with open(self.config_file, 'w') as f:
            json.dump(self.config, f, indent=4)

    @commands.Cog.listener()
    async def on_message(self, message):
        """Listen for bot messages starting with . in the watch channel"""
        try:
            # Only process bot messages (from 2b2t.vc), not user messages
            if not message.author.bot:
                return
            
            # Don't process our own bot's messages
            if message.author.id == self.bot.user.id:
                return
            
            if not message.guild:
                return
            
            guild_id_str = str(message.guild.id)
            setups = self.config.get(guild_id_str, [])
            
            if not setups:
                return
            
            # Check all setups for this guild
            for setup in setups:
                watch_channel_id = setup.get('watch_channel_id')
                forward_channel_id = setup.get('forward_channel_id')
                
                if not watch_channel_id or not forward_channel_id:
                    continue
                
                # Skip if this message is not in this setup's watch channel
                if message.channel.id != watch_channel_id:
                    continue
                
                forward_channel = message.guild.get_channel(forward_channel_id)
                if not forward_channel:
                    continue
                
                # If the message has embeds, forward only ones that start with .
                if message.embeds:
                    for embed in message.embeds:
                        # Check if embed description contains a username starting with .
                        if embed.description:
                            desc = embed.description.strip()
                            # Remove markdown bold if present
                            if desc.startswith('**'):
                                # Extract text between ** **
                                parts = desc.split('**')
                                if len(parts) >= 2:
                                    username_part = parts[1]
                                    if username_part.startswith('.'):
                                        sent_msg = await forward_channel.send(embed=embed)
                                        # Publish if in announcement channel
                                        if hasattr(forward_channel, 'is_news') and forward_channel.is_news():
                                            try:
                                                await sent_msg.publish()
                                            except:
                                                pass
                            elif desc.startswith('.'):
                                sent_msg = await forward_channel.send(embed=embed)
                                # Publish if in announcement channel
                                if hasattr(forward_channel, 'is_news') and forward_channel.is_news():
                                    try:
                                        await sent_msg.publish()
                                    except:
                                        pass
                # If message content starts with ., create embed
                elif message.content.startswith('.'):
                    # Extract username from message like ".Username connected"
                    username = "Unknown"
                    parts = message.content.split()
                    if len(parts) > 0:
                        username = parts[0][1:]
                    
                    # Create embed from text message
                    embed = discord.Embed(
                        description=message.content,
                        color=discord.Color.blue()
                    )
                    embed.set_author(name=username, icon_url=message.author.display_avatar.url)
                    embed.timestamp = message.created_at
                    
                    sent_msg = await forward_channel.send(embed=embed)
                    # Publish if in announcement channel
                    if hasattr(forward_channel, 'is_news') and forward_channel.is_news():
                        try:
                            await sent_msg.publish()
                        except:
                            pass
        except Exception as e:
            import traceback
            print(f"Error in on_message listener: {e}")
            traceback.print_exc()

    @app_commands.command(name='setupdotnotify', description='Setup the dot notification forwarding system')
    @app_commands.describe(
        watch_channel='Channel to watch for dot commands',
        forward_channel='Channel to forward dot messages to'
    )
    @app_commands.checks.has_permissions(administrator=True)
    async def setup_dot_notify(self, interaction: discord.Interaction, watch_channel: discord.TextChannel, forward_channel: discord.TextChannel):
        await interaction.response.defer()
        
        try:
            guild_id_str = str(interaction.guild.id)
            
            if guild_id_str not in self.config:
                self.config[guild_id_str] = []
            
            # Check if this exact combination already exists
            existing = False
            for setup in self.config[guild_id_str]:
                if setup.get('watch_channel_id') == watch_channel.id and setup.get('forward_channel_id') == forward_channel.id:
                    existing = True
                    break
            
            if not existing:
                self.config[guild_id_str].append({
                    'watch_channel_id': watch_channel.id,
                    'forward_channel_id': forward_channel.id
                })
                self.save_config()
                
                embed = discord.Embed(
                    title="✅ Dot Notification Configured",
                    description="The dot notification forwarding system has been set up!",
                    color=discord.Color.green()
                )
            else:
                embed = discord.Embed(
                    title="ℹ️ Already Configured",
                    description="This exact setup already exists.",
                    color=discord.Color.blue()
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

    @app_commands.command(name='cleardotnotify', description='Clear a specific dot notification setup')
    @app_commands.describe(
        watch_channel='The watch channel to remove (leave empty to clear all)'
    )
    @app_commands.checks.has_permissions(administrator=True)
    async def clear_dot_notify(self, interaction: discord.Interaction, watch_channel: discord.TextChannel = None):
        try:
            guild_id_str = str(interaction.guild.id)
            
            if guild_id_str not in self.config or not self.config[guild_id_str]:
                await interaction.response.send_message(
                    embed=discord.Embed(
                        title="ℹ️ No Setup Found",
                        description="There is no dot notification setup for this server.",
                        color=discord.Color.blue()
                    ),
                    ephemeral=True
                )
                return
            
            if watch_channel:
                # Remove specific setup
                original_count = len(self.config[guild_id_str])
                self.config[guild_id_str] = [
                    setup for setup in self.config[guild_id_str]
                    if setup.get('watch_channel_id') != watch_channel.id
                ]
                
                if len(self.config[guild_id_str]) < original_count:
                    self.save_config()
                    embed = discord.Embed(
                        title="✅ Dot Notification Cleared",
                        description=f"Removed setup for {watch_channel.mention}",
                        color=discord.Color.green()
                    )
                else:
                    embed = discord.Embed(
                        title="ℹ️ No Setup Found",
                        description=f"No setup found for {watch_channel.mention}",
                        color=discord.Color.blue()
                    )
            else:
                # Clear all setups
                del self.config[guild_id_str]
                self.save_config()
                embed = discord.Embed(
                    title="✅ All Dot Notifications Cleared",
                    description="All dot notification setups have been removed.",
                    color=discord.Color.green()
                )
            
            await interaction.response.send_message(embed=embed, ephemeral=True)
        
        except Exception as e:
            import traceback
            error_details = ''.join(traceback.format_exception(type(e), e, e.__traceback__))
            
            if len(error_details) > 1000:
                error_details = error_details[-1000:]
            
            embed = discord.Embed(
                title="❌ Error Clearing Setup",
                description=f"**Error Type:** `{type(e).__name__}`\n**Error Message:** {str(e)}",
                color=discord.Color.red()
            )
            embed.add_field(name="Full Error Details", value=f"```python\n{error_details}\n```", inline=False)
            
            try:
                await interaction.response.send_message(embed=embed, ephemeral=True)
            except:
                await interaction.followup.send(embed=embed, ephemeral=True)


    @app_commands.command(name='listdotnotify', description='List all dot notification setups')
    @app_commands.checks.has_permissions(administrator=True)
    async def list_dot_notify(self, interaction: discord.Interaction):
        await interaction.response.defer(ephemeral=True)
        
        try:
            guild_id_str = str(interaction.guild.id)
            setups = self.config.get(guild_id_str, [])
            
            if not setups:
                embed = discord.Embed(
                    title="ℹ️ No Setups Found",
                    description="There are no dot notification setups for this server.",
                    color=discord.Color.blue()
                )
            else:
                embed = discord.Embed(
                    title="📋 Dot Notification Setups",
                    description=f"Found {len(setups)} setup(s):",
                    color=discord.Color.blue()
                )
                
                for i, setup in enumerate(setups, 1):
                    watch_ch = interaction.guild.get_channel(setup.get('watch_channel_id'))
                    forward_ch = interaction.guild.get_channel(setup.get('forward_channel_id'))
                    
                    watch_name = watch_ch.mention if watch_ch else f"Unknown ({setup.get('watch_channel_id')})"
                    forward_name = forward_ch.mention if forward_ch else f"Unknown ({setup.get('forward_channel_id')})"
                    
                    embed.add_field(
                        name=f"Setup #{i}",
                        value=f"👀 Watch: {watch_name}\n📨 Forward: {forward_name}",
                        inline=False
                    )
            
            await interaction.followup.send(embed=embed, ephemeral=True)
        
        except Exception as e:
            import traceback
            error_details = ''.join(traceback.format_exception(type(e), e, e.__traceback__))
            
            if len(error_details) > 1000:
                error_details = error_details[-1000:]
            
            embed = discord.Embed(
                title="❌ Error Listing Setups",
                description=f"**Error Type:** `{type(e).__name__}`\n**Error Message:** {str(e)}",
                color=discord.Color.red()
            )
            embed.add_field(name="Full Error Details", value=f"```python\n{error_details}\n```", inline=False)
            
            await interaction.followup.send(embed=embed, ephemeral=True)

    @app_commands.command(name='resetdotconfig', description='Delete the entire dot config file and start fresh')
    @app_commands.checks.has_permissions(administrator=True)
    async def reset_dot_config(self, interaction: discord.Interaction):
        try:
            await interaction.response.defer(ephemeral=True)
            
            self.config = {}
            self.save_config()
            
            embed = discord.Embed(
                title="✅ Config Reset",
                description="The entire dot notification config has been cleared. You can now set up fresh.",
                color=discord.Color.green()
            )
            await interaction.followup.send(embed=embed, ephemeral=True)
        
        except Exception as e:
            import traceback
            error_details = ''.join(traceback.format_exception(type(e), e, e.__traceback__))
            
            if len(error_details) > 1000:
                error_details = error_details[-1000:]
            
            embed = discord.Embed(
                title="❌ Error Resetting Config",
                description=f"**Error Type:** `{type(e).__name__}`\n**Error Message:** {str(e)}",
                color=discord.Color.red()
            )
            embed.add_field(name="Full Error Details", value=f"```python\n{error_details}\n```", inline=False)
            
            await interaction.followup.send(embed=embed, ephemeral=True)

    @app_commands.command(name='debugdot', description='Show recent bot messages for debugging')
    @app_commands.checks.has_permissions(administrator=True)
    async def debug_dot(self, interaction: discord.Interaction):
        await interaction.response.defer(ephemeral=True)
        
        try:
            guild_id_str = str(interaction.guild.id)
            setups = self.config.get(guild_id_str, [])
            
            if not setups:
                await interaction.followup.send("No setups configured!", ephemeral=True)
                return
            
            # Get the watch channel from first setup
            watch_channel_id = setups[0].get('watch_channel_id')
            watch_channel = interaction.guild.get_channel(watch_channel_id)
            
            if not watch_channel:
                await interaction.followup.send("Watch channel not found!", ephemeral=True)
                return
            
            # Fetch last 10 messages from watch channel
            messages = [msg async for msg in watch_channel.history(limit=10)]
            
            embed = discord.Embed(
                title="🔍 Debug: Recent Messages",
                description=f"Showing last {len(messages)} messages from {watch_channel.mention}",
                color=discord.Color.blue()
            )
            
            for msg in messages:
                if msg.author.bot:
                    embed_info = ""
                    if msg.embeds:
                        for i, emb in enumerate(msg.embeds):
                            desc_preview = (emb.description[:50] + "...") if emb.description and len(emb.description) > 50 else (emb.description or "No description")
                            embed_info += f"\nEmbed {i}: `{desc_preview}`"
                    else:
                        embed_info = f"\nText: `{msg.content[:50]}`"
                    
                    embed.add_field(
                        name=f"Bot: {msg.author.name}",
                        value=embed_info,
                        inline=False
                    )
            
            await interaction.followup.send(embed=embed, ephemeral=True)
        
        except Exception as e:
            import traceback
            error_details = ''.join(traceback.format_exception(type(e), e, e.__traceback__))
            
            if len(error_details) > 1000:
                error_details = error_details[-1000:]
            
            embed = discord.Embed(
                title="❌ Error in Debug",
                description=f"**Error Type:** `{type(e).__name__}`\n**Error Message:** {str(e)}",
                color=discord.Color.red()
            )
            embed.add_field(name="Full Error Details", value=f"```python\n{error_details}\n```", inline=False)
            
            await interaction.followup.send(embed=embed, ephemeral=True)


async def setup(bot):
    await bot.add_cog(Chat(bot))
