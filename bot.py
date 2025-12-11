import discord
from discord import app_commands
from discord.ext import commands
import os
import asyncio
from dotenv import load_dotenv

# Load environment variables
load_dotenv()

# Bot configuration
intents = discord.Intents.default()
intents.message_content = True
intents.guilds = True
intents.members = True

bot = commands.Bot(command_prefix='!', intents=intents)

async def load_cogs():
    """Load all cogs from the cogs directory"""
    if os.path.exists('cogs'):
        for filename in os.listdir('cogs'):
            if filename.endswith('.py') and not filename.startswith('_'):
                try:
                    await bot.load_extension(f'cogs.{filename[:-3]}')
                    print(f'Loaded cog: {filename[:-3]}')
                except Exception as e:
                    print(f'Failed to load cog {filename}: {e}')

@bot.event
async def on_ready():
    print(f'{bot.user} has connected to Discord!')
    print(f'Bot is in {len(bot.guilds)} guilds')
    
    # Load cogs
    await load_cogs()
    
    try:
        # Clear and resync commands
        bot.tree.clear_commands(guild=None)
        synced = await bot.tree.sync()
        print(f'Synced {len(synced)} slash command(s)')
    except Exception as e:
        print(f'Failed to sync commands: {e}')

@bot.tree.error
async def on_app_command_error(interaction: discord.Interaction, error: app_commands.AppCommandError):
    """Global error handler for slash commands"""
    # Handle missing permissions
    if isinstance(error, app_commands.MissingPermissions):
        try:
            await interaction.response.send_message(
                f"❌ You don't have permission to use this command.\n**Required:** {', '.join(error.missing_permissions)}",
                ephemeral=True
            )
        except:
            pass
        return
    
    # Handle command invoke errors
    if isinstance(error, app_commands.CommandInvokeError):
        original_error = error.original
        if isinstance(original_error, discord.errors.NotFound):
            # Interaction expired, silently ignore
            return
    
    # Log other errors
    print(f'Error in command {interaction.command.name if interaction.command else "unknown"}: {error}')
    
    try:
        if not interaction.response.is_done():
            await interaction.response.send_message(
                "❌ An error occurred while processing this command.",
                ephemeral=True
            )
        else:
            await interaction.followup.send(
                "❌ An error occurred while processing this command.",
                ephemeral=True
            )
    except:
        pass  # Can't send error message

@bot.event
async def on_message(message):
    # Ignore messages from the bot itself
    if message.author == bot.user:
        return
    
    # Process commands
    await bot.process_commands(message)

@bot.command(name='hello', help='Responds with a greeting')
async def hello(ctx):
    await ctx.send(f'Hello {ctx.author.mention}! 👋')

@bot.command(name='ping', help='Shows the bot latency')
async def ping(ctx):
    latency = round(bot.latency * 1000)
    await ctx.send(f'Pong! Latency: {latency}ms')

@bot.command(name='info', help='Shows bot information')
async def info(ctx):
    embed = discord.Embed(
        title="Bot Information",
        description="2b2t Market Bot",
        color=discord.Color.blue()
    )
    embed.add_field(name="Servers", value=len(bot.guilds), inline=True)
    embed.add_field(name="Users", value=len(bot.users), inline=True)
    embed.add_field(name="Prefix", value="!", inline=True)
    await ctx.send(embed=embed)

# Slash Commands
@bot.tree.command(name='hello', description='Get a friendly greeting from the bot')
async def slash_hello(interaction: discord.Interaction):
    try:
        await interaction.response.send_message(f'Hello {interaction.user.mention}! 👋')
    except discord.errors.NotFound:
        pass  # Interaction expired

@bot.tree.command(name='ping', description='Check the bot\'s latency')
async def slash_ping(interaction: discord.Interaction):
    try:
        latency = round(bot.latency * 1000)
        await interaction.response.send_message(f'Pong! Latency: {latency}ms')
    except discord.errors.NotFound:
        pass  # Interaction expired

@bot.tree.command(name='info', description='Display bot information')
async def slash_info(interaction: discord.Interaction):
    try:
        embed = discord.Embed(
            title="Bot Information",
            description="2b2t Market Bot",
            color=discord.Color.blue()
        )
        embed.add_field(name="Servers", value=len(bot.guilds), inline=True)
        embed.add_field(name="Users", value=len(bot.users), inline=True)
        embed.add_field(name="Latency", value=f"{round(bot.latency * 1000)}ms", inline=True)
        await interaction.response.send_message(embed=embed)
    except discord.errors.NotFound:
        pass  # Interaction expired

@bot.tree.command(name='userinfo', description='Get information about a user')
@app_commands.describe(user='The user to get information about')
async def slash_userinfo(interaction: discord.Interaction, user: discord.Member = None):
    try:
        user = user or interaction.user
        embed = discord.Embed(
            title=f"User Info - {user.name}",
            color=discord.Color.green()
        )
        embed.set_thumbnail(url=user.display_avatar.url)
        embed.add_field(name="Username", value=f"{user.name}#{user.discriminator}", inline=True)
        embed.add_field(name="ID", value=user.id, inline=True)
        embed.add_field(name="Nickname", value=user.nick or "None", inline=True)
        embed.add_field(name="Account Created", value=user.created_at.strftime("%Y-%m-%d"), inline=True)
        embed.add_field(name="Joined Server", value=user.joined_at.strftime("%Y-%m-%d"), inline=True)
        embed.add_field(name="Roles", value=len(user.roles), inline=True)
        await interaction.response.send_message(embed=embed)
    except discord.errors.NotFound:
        pass  # Interaction expired

@bot.tree.command(name='serverinfo', description='Get information about the server')
async def slash_serverinfo(interaction: discord.Interaction):
    try:
        guild = interaction.guild
        embed = discord.Embed(
            title=f"Server Info - {guild.name}",
            color=discord.Color.purple()
        )
        if guild.icon:
            embed.set_thumbnail(url=guild.icon.url)
        embed.add_field(name="Server ID", value=guild.id, inline=True)
        embed.add_field(name="Owner", value=guild.owner.mention, inline=True)
        embed.add_field(name="Members", value=guild.member_count, inline=True)
        embed.add_field(name="Channels", value=len(guild.channels), inline=True)
        embed.add_field(name="Roles", value=len(guild.roles), inline=True)
        embed.add_field(name="Created", value=guild.created_at.strftime("%Y-%m-%d"), inline=True)
        await interaction.response.send_message(embed=embed)
    except discord.errors.NotFound:
        pass  # Interaction expired

@bot.tree.command(name='notify', description='Ping a user with a custom message')
@app_commands.describe(user='The user to ping', message='The message to send')
async def notify_user(interaction: discord.Interaction, user: discord.Member, message: str):
    try:
        await interaction.response.send_message(
            f"{user.mention} - {message}\n\n*Sent by {interaction.user.mention}*"
        )
    except discord.errors.NotFound:
        pass  # Interaction expired

# Run the bot
if __name__ == '__main__':
    TOKEN = os.getenv('DISCORD_BOT_TOKEN')
    if not TOKEN:
        print("Error: DISCORD_BOT_TOKEN not found in .env file")
        print("Please create a .env file with your Discord bot token")
        exit(1)
    
    bot.run(TOKEN)
