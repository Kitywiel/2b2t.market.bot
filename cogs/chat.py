import discord
from discord import app_commands
from discord.ext import commands
import json
import os
from datetime import datetime
import aiohttp


class Chat(commands.Cog):
    def __init__(self, bot):
        self.bot = bot
        self.config_file = 'chat_config.json'
        self.webhook_file = 'chat_webhooks.json'
        self.is_ready = False
        self.load_data()
        self.load_webhooks()
        print(f"[INIT] Chat cog initialized. Config: {len(self.config)} guilds, Webhooks: {len(self.webhooks)} guilds")

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
            
            print(f"[LOAD] Loaded config for {len(self.config)} guild(s)")
        else:
            self.config = {}
            self.save_config()
            print("[LOAD] No config file found, created new one")
    
    def save_config(self):
        """Save config data to JSON file"""
        with open(self.config_file, 'w') as f:
            json.dump(self.config, f, indent=4)
    
    def load_webhooks(self):
        """Load webhook URLs from JSON file"""
        if os.path.exists(self.webhook_file):
            with open(self.webhook_file, 'r') as f:
                self.webhooks = json.load(f)
            print(f"[LOAD] Loaded webhooks for {len(self.webhooks)} guild(s)")
        else:
            self.webhooks = {}
            self.save_webhooks()
            print("[LOAD] No webhook file found, created new one")
    
    def save_webhooks(self):
        """Save webhook URLs to JSON file"""
        with open(self.webhook_file, 'w') as f:
            json.dump(self.webhooks, f, indent=4)

    @commands.Cog.listener()
    async def on_ready(self):
        """Called when bot is ready"""
        self.is_ready = True
        print(f"[READY] Chat cog is ready. Monitoring {sum(len(setups) for setups in self.config.values())} setup(s) across {len(self.config)} guild(s)")
        
        # Log all active setups
        for guild_id, setups in self.config.items():
            for setup in setups:
                watch_id = setup.get('watch_channel_id')
                forward_id = setup.get('forward_channel_id')
                print(f"[READY] Guild {guild_id}: Watching channel {watch_id} -> Forwarding to {forward_id}")

    @commands.Cog.listener()
    async def on_message(self, message):
        """Listen for bot messages starting with . in the watch channel"""
        try:
            # Wait until cog is fully ready
            if not self.is_ready:
                return
            
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
            
            print(f"[DEBUG] Processing message from {message.author.name} in #{message.channel.name}")
            
            # Track if we've sent a message to avoid duplicates (globally per message)
            message_sent = False
            
            # Check all setups for this guild
            for setup in setups:
                # Skip if we've already processed this dot event
                if message_sent:
                    break
                    
                watch_channel_id = setup.get('watch_channel_id')
                forward_channel_id = setup.get('forward_channel_id')
                
                if not watch_channel_id or not forward_channel_id:
                    continue
                
                # Skip if this message is not in this setup's watch channel
                if message.channel.id != watch_channel_id:
                    continue
                
                print(f"[MATCH] Message matches setup: watch={watch_channel_id} forward={forward_channel_id}")
                
                forward_channel = message.guild.get_channel(forward_channel_id)
                if not forward_channel:
                    print(f"[ERROR] Forward channel {forward_channel_id} not found!")
                    continue
                
                # Get webhooks for this setup
                setup_key = f"{watch_channel_id}_{forward_channel_id}"
                webhook_urls = self.webhooks.get(str(message.guild.id), {}).get(setup_key, [])
                
                # If the message has embeds, forward only ones that start with .
                if message.embeds:
                    for embed in message.embeds:
                        # Skip if we've already sent a message for this dot event
                        if message_sent:
                            continue
                            
                        # Check if embed description contains a username starting with .
                        if embed.description:
                            desc = embed.description.strip()
                            should_forward = False
                            
                            # Remove markdown bold if present
                            if desc.startswith('**'):
                                # Extract text between ** **
                                parts = desc.split('**')
                                if len(parts) >= 2:
                                    username_part = parts[1]
                                    if username_part.startswith('.'):
                                        should_forward = True
                            elif desc.startswith('.'):
                                should_forward = True
                            
                            if should_forward:
                                print(f"[FORWARD] Forwarding dot message: {desc[:50]}...")
                                
                                # Send to webhooks first if available
                                if webhook_urls:
                                    print(f"[WEBHOOK] Attempting to send to {len(webhook_urls)} webhook(s)")
                                    webhook_failed = False
                                    webhook_success = False
                                    for webhook_url in webhook_urls:
                                        try:
                                            async with aiohttp.ClientSession() as session:
                                                webhook = discord.Webhook.from_url(webhook_url, session=session)
                                                await webhook.send(embed=embed)
                                                print(f"[WEBHOOK] ✅ Sent successfully to webhook")
                                                webhook_success = True
                                        except discord.NotFound:
                                            print(f"[WEBHOOK] ❌ Webhook not found (deleted): {webhook_url[:50]}...")
                                            webhook_failed = True
                                        except discord.HTTPException as e:
                                            print(f"[WEBHOOK] ❌ HTTP error {e.status}: {e.text}")
                                            webhook_failed = True
                                        except Exception as e:
                                            print(f"[WEBHOOK] ❌ Error {type(e).__name__}: {e}")
                                            webhook_failed = True
                                    
                                    # Fallback to forward channel if all webhooks failed
                                    if webhook_failed and not webhook_success:
                                        print(f"[CHANNEL] All webhooks failed, sending to channel #{forward_channel.name}")
                                        await forward_channel.send(embed=embed)
                                else:
                                    # Only send to forward channel if no webhooks
                                    print(f"[CHANNEL] No webhooks, sending to #{forward_channel.name}")
                                    await forward_channel.send(embed=embed)
                                
                                message_sent = True
                                
                # If message content starts with ., create embed
                elif message.content.startswith('.') and not message_sent:
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
                    
                    print(f"[FORWARD] Forwarding text message: {message.content[:50]}...")
                    
                    # Send to webhooks first if available
                    if webhook_urls:
                        print(f"[WEBHOOK] Attempting to send to {len(webhook_urls)} webhook(s)")
                        webhook_failed = False
                        webhook_success = False
                        for webhook_url in webhook_urls:
                            try:
                                async with aiohttp.ClientSession() as session:
                                    webhook = discord.Webhook.from_url(webhook_url, session=session)
                                    await webhook.send(embed=embed, username=username)
                                    print(f"[WEBHOOK] ✅ Sent successfully to webhook")
                                    webhook_success = True
                            except discord.NotFound:
                                print(f"[WEBHOOK] ❌ Webhook not found (deleted): {webhook_url[:50]}...")
                                webhook_failed = True
                            except discord.HTTPException as e:
                                print(f"[WEBHOOK] ❌ HTTP error {e.status}: {e.text}")
                                webhook_failed = True
                            except Exception as e:
                                print(f"[WEBHOOK] ❌ Error {type(e).__name__}: {e}")
                                webhook_failed = True
                        
                        # Fallback to forward channel if all webhooks failed
                        if webhook_failed and not webhook_success:
                            print(f"[CHANNEL] All webhooks failed, sending to channel #{forward_channel.name}")
                            await forward_channel.send(embed=embed)
                    else:
                        # Only send to forward channel if no webhooks
                        print(f"[CHANNEL] No webhooks, sending to #{forward_channel.name}")
                        await forward_channel.send(embed=embed)
                    
                    message_sent = True
        except Exception as e:
            import traceback
            error_msg = f"[ERROR] on_message listener crashed: {type(e).__name__}: {e}"
            print(error_msg)
            traceback.print_exc()
            
            # Try to notify in a debug channel if available
            try:
                if message.guild:
                    # Try to send error to the forward channel
                    guild_id_str = str(message.guild.id)
                    setups = self.config.get(guild_id_str, [])
                    if setups:
                        forward_channel_id = setups[0].get('forward_channel_id')
                        if forward_channel_id:
                            forward_channel = message.guild.get_channel(forward_channel_id)
                            if forward_channel:
                                error_embed = discord.Embed(
                                    title="⚠️ Forwarding Error",
                                    description=f"```{error_msg[:1900]}```",
                                    color=discord.Color.red()
                                )
                                await forward_channel.send(embed=error_embed)
            except:
                pass  # Don't crash while trying to report the crash

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

    @app_commands.command(name='checkdotstatus', description='Check if dot notification forwarding is working')
    @app_commands.checks.has_permissions(administrator=True)
    async def check_dot_status(self, interaction: discord.Interaction):
        """Check the health and status of the dot notification system"""
        await interaction.response.defer(ephemeral=True)
        
        try:
            guild_id_str = str(interaction.guild.id)
            setups = self.config.get(guild_id_str, [])
            
            embed = discord.Embed(
                title="🔍 Dot Notification Status",
                color=discord.Color.green()
            )
            
            # Bot status
            embed.add_field(
                name="✅ Bot Status",
                value=f"Online and listening to messages\nLatency: {round(self.bot.latency * 1000)}ms",
                inline=False
            )
            
            # Setup count
            embed.add_field(
                name="📋 Active Setups",
                value=f"{len(setups)} setup(s) configured",
                inline=True
            )
            
            # Check each setup
            if setups:
                for i, setup in enumerate(setups, 1):
                    watch_ch = interaction.guild.get_channel(setup.get('watch_channel_id'))
                    forward_ch = interaction.guild.get_channel(setup.get('forward_channel_id'))
                    
                    watch_status = "✅" if watch_ch else "❌"
                    forward_status = "✅" if forward_ch else "❌"
                    
                    # Check webhook status
                    setup_key = f"{setup.get('watch_channel_id')}_{setup.get('forward_channel_id')}"
                    webhook_urls = self.webhooks.get(guild_id_str, {}).get(setup_key, [])
                    webhook_count = len(webhook_urls)
                    
                    watch_name = watch_ch.mention if watch_ch else "Channel Deleted"
                    forward_name = forward_ch.mention if forward_ch else "Channel Deleted"
                    
                    embed.add_field(
                        name=f"Setup #{i}",
                        value=f"{watch_status} Watch: {watch_name}\n{forward_status} Forward: {forward_name}\n🔗 Webhooks: {webhook_count}",
                        inline=True
                    )
            else:
                embed.add_field(
                    name="⚠️ No Setups",
                    value="No dot notification setups configured. Use `/setupdotnotify` to create one.",
                    inline=False
                )
            
            embed.set_footer(text="This command confirms the bot is running and can process commands.")
            
            await interaction.followup.send(embed=embed, ephemeral=True)
        
        except Exception as e:
            import traceback
            error_details = ''.join(traceback.format_exception(type(e), e, e.__traceback__))
            
            embed = discord.Embed(
                title="❌ Error Checking Status",
                description=f"**Error:** `{type(e).__name__}: {str(e)}`",
                color=discord.Color.red()
            )
            if len(error_details) < 1000:
                embed.add_field(name="Details", value=f"```python\n{error_details}\n```", inline=False)
            
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

    @app_commands.command(name='addwebhook', description='Add a webhook URL to forward messages to other servers')
    @app_commands.describe(
        watch_channel='The watch channel',
        webhook_url='The webhook URL from another server'
    )
    @app_commands.checks.has_permissions(administrator=True)
    async def add_webhook(self, interaction: discord.Interaction, watch_channel: discord.TextChannel, webhook_url: str):
        await interaction.response.defer(ephemeral=True)
        
        try:
            guild_id_str = str(interaction.guild.id)
            
            # Find the setup for this watch channel
            setups = self.config.get(guild_id_str, [])
            matching_setup = None
            
            for setup in setups:
                if setup.get('watch_channel_id') == watch_channel.id:
                    matching_setup = setup
                    break
            
            if not matching_setup:
                embed = discord.Embed(
                    title="❌ No Setup Found",
                    description=f"No dot notification setup found for {watch_channel.mention}. Run `/setupdotnotify` first.",
                    color=discord.Color.red()
                )
                await interaction.followup.send(embed=embed, ephemeral=True)
                return
            
            # Validate webhook URL (accept all Discord webhook formats)
            valid_prefixes = [
                'https://discord.com/api/webhooks/',
                'https://discordapp.com/api/webhooks/',
                'https://ptb.discord.com/api/webhooks/',
                'https://canary.discord.com/api/webhooks/'
            ]
            if not any(webhook_url.startswith(prefix) for prefix in valid_prefixes):
                embed = discord.Embed(
                    title="❌ Invalid Webhook",
                    description="Please provide a valid Discord webhook URL.\nMust start with a Discord webhook URL format.",
                    color=discord.Color.red()
                )
                await interaction.followup.send(embed=embed, ephemeral=True)
                return
            
            # Add webhook
            if guild_id_str not in self.webhooks:
                self.webhooks[guild_id_str] = {}
            
            setup_key = f"{matching_setup['watch_channel_id']}_{matching_setup['forward_channel_id']}"
            
            if setup_key not in self.webhooks[guild_id_str]:
                self.webhooks[guild_id_str][setup_key] = []
            
            if webhook_url not in self.webhooks[guild_id_str][setup_key]:
                self.webhooks[guild_id_str][setup_key].append(webhook_url)
                self.save_webhooks()
                
                embed = discord.Embed(
                    title="✅ Webhook Added",
                    description=f"Webhook added for {watch_channel.mention}\nMessages will now be forwarded to this webhook.",
                    color=discord.Color.green()
                )
            else:
                embed = discord.Embed(
                    title="ℹ️ Already Exists",
                    description="This webhook is already configured.",
                    color=discord.Color.blue()
                )
            
            await interaction.followup.send(embed=embed, ephemeral=True)
        
        except Exception as e:
            import traceback
            error_details = ''.join(traceback.format_exception(type(e), e, e.__traceback__))
            
            if len(error_details) > 1000:
                error_details = error_details[-1000:]
            
            embed = discord.Embed(
                title="❌ Error Adding Webhook",
                description=f"**Error Type:** `{type(e).__name__}`\n**Error Message:** {str(e)}",
                color=discord.Color.red()
            )
            embed.add_field(name="Full Error Details", value=f"```python\n{error_details}\n```", inline=False)
            
            try:
                await interaction.response.send_message(embed=embed, ephemeral=True)
            except:
                try:
                    await interaction.followup.send(embed=embed, ephemeral=True)
                except:
                    pass

    @app_commands.command(name='listwebhooks', description='List all configured webhooks')
    @app_commands.checks.has_permissions(administrator=True)
    async def list_webhooks(self, interaction: discord.Interaction):
        await interaction.response.defer(ephemeral=True)
        
        try:
            guild_id_str = str(interaction.guild.id)
            guild_webhooks = self.webhooks.get(guild_id_str, {})
            
            if not guild_webhooks:
                embed = discord.Embed(
                    title="ℹ️ No Webhooks",
                    description="No webhooks configured for this server.",
                    color=discord.Color.blue()
                )
                await interaction.followup.send(embed=embed, ephemeral=True)
                return
            
            embed = discord.Embed(
                title="📋 Configured Webhooks",
                color=discord.Color.blue()
            )
            
            for setup_key, webhook_list in guild_webhooks.items():
                parts = setup_key.split('_')
                if len(parts) == 2:
                    watch_ch = interaction.guild.get_channel(int(parts[0]))
                    watch_name = watch_ch.mention if watch_ch else f"Channel ID: {parts[0]}"
                    
                    webhook_preview = []
                    for url in webhook_list:
                        # Show last 20 chars of webhook URL
                        webhook_preview.append(f"`...{url[-20:]}`")
                    
                    embed.add_field(
                        name=f"Watch: {watch_name}",
                        value=f"**{len(webhook_list)} webhook(s):**\n" + "\n".join(webhook_preview),
                        inline=False
                    )
            
            await interaction.followup.send(embed=embed, ephemeral=True)
        
        except Exception as e:
            import traceback
            error_details = ''.join(traceback.format_exception(type(e), e, e.__traceback__))
            
            if len(error_details) > 1000:
                error_details = error_details[-1000:]
            
            embed = discord.Embed(
                title="❌ Error Listing Webhooks",
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
