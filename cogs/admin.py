import discord
from discord import app_commands
from discord.ext import commands
import subprocess
import sys
import os

class Admin(commands.Cog):
    def __init__(self, bot):
        self.bot = bot

    @app_commands.command(name='update', description='Update the bot from GitHub and restart')
    @app_commands.checks.has_permissions(administrator=True)
    async def update(self, interaction: discord.Interaction):
        await interaction.response.defer()
        
        embed = discord.Embed(
            title="🔄 Updating Bot",
            description="Pulling latest changes from GitHub...",
            color=discord.Color.blue()
        )
        await interaction.followup.send(embed=embed)
        
        try:
            # Check if git is available
            git_check = subprocess.run(
                ['git', '--version'],
                capture_output=True,
                text=True,
                shell=True  # Use shell on Windows
            )
            
            if git_check.returncode != 0:
                embed = discord.Embed(
                    title="❌ Git Not Found",
                    description="Git is not installed or not in PATH.\n\n**To fix:**\n1. Download Git from [git-scm.com](https://git-scm.com/download/win)\n2. Install it and restart your computer\n3. Or manually update files from GitHub",
                    color=discord.Color.red()
                )
                await interaction.followup.send(embed=embed)
                return
            
            # Pull latest changes from git
            result = subprocess.run(
                ['git', 'pull'],
                capture_output=True,
                text=True,
                cwd=os.path.dirname(os.path.dirname(__file__)),
                shell=True  # Use shell on Windows
            )
            
            if result.returncode != 0:
                embed = discord.Embed(
                    title="❌ Update Failed",
                    description=f"```\n{result.stderr}\n```",
                    color=discord.Color.red()
                )
                await interaction.followup.send(embed=embed)
                return
            
            # Check if there were updates
            if "Already up to date" in result.stdout or "Already up-to-date" in result.stdout:
                embed = discord.Embed(
                    title="✅ Already Up to Date",
                    description="No updates available.",
                    color=discord.Color.green()
                )
                await interaction.followup.send(embed=embed)
                return
            
            # Update successful
            embed = discord.Embed(
                title="✅ Update Successful",
                description=f"```\n{result.stdout}\n```\n\n🔄 Restarting bot...",
                color=discord.Color.green()
            )
            await interaction.followup.send(embed=embed)
            
            # Restart the bot
            await self.bot.close()
            os.execv(sys.executable, ['python'] + sys.argv)
            
        except FileNotFoundError:
            embed = discord.Embed(
                title="❌ Git Not Installed",
                description="Git is not installed on this system.\n\n**To install Git:**\n1. Download from [git-scm.com](https://git-scm.com/download/win)\n2. Run the installer\n3. Restart your computer\n4. Try `/update` again",
                color=discord.Color.red()
            )
            await interaction.followup.send(embed=embed)
        except Exception as e:
            embed = discord.Embed(
                title="❌ Error",
                description=f"An error occurred: {str(e)}\n\nYou can manually update by downloading the latest files from GitHub.",
                color=discord.Color.red()
            )
            await interaction.followup.send(embed=embed)

    @app_commands.command(name='restart', description='Restart the bot')
    @app_commands.checks.has_permissions(administrator=True)
    async def restart(self, interaction: discord.Interaction):
        embed = discord.Embed(
            title="🔄 Restarting Bot",
            description="Bot will restart now...",
            color=discord.Color.blue()
        )
        await interaction.response.send_message(embed=embed)
        
        await self.bot.close()
        os.execv(sys.executable, ['python'] + sys.argv)

    @app_commands.command(name='sync', description='Manually sync slash commands')
    @app_commands.checks.has_permissions(administrator=True)
    async def sync(self, interaction: discord.Interaction):
        await interaction.response.defer()
        
        try:
            synced = await self.bot.tree.sync()
            embed = discord.Embed(
                title="✅ Commands Synced",
                description=f"Successfully synced {len(synced)} command(s).",
                color=discord.Color.green()
            )
            await interaction.followup.send(embed=embed)
        except Exception as e:
            embed = discord.Embed(
                title="❌ Sync Failed",
                description=f"Error: {str(e)}",
                color=discord.Color.red()
            )
            await interaction.followup.send(embed=embed)

    @app_commands.command(name='reload', description='Reload a specific cog')
    @app_commands.describe(cog='The name of the cog to reload (e.g., itemmarket, tickets, admin)')
    @app_commands.checks.has_permissions(administrator=True)
    async def reload(self, interaction: discord.Interaction, cog: str):
        await interaction.response.defer()
        
        try:
            # Unload the cog
            await self.bot.unload_extension(f'cogs.{cog}')
            # Reload the cog
            await self.bot.load_extension(f'cogs.{cog}')
            
            embed = discord.Embed(
                title="✅ Cog Reloaded",
                description=f"Successfully reloaded `{cog}` cog.",
                color=discord.Color.green()
            )
            await interaction.followup.send(embed=embed)
        except Exception as e:
            embed = discord.Embed(
                title="❌ Reload Failed",
                description=f"Error: {str(e)}",
                color=discord.Color.red()
            )
            await interaction.followup.send(embed=embed)

    @app_commands.command(name='reloadall', description='Reload all cogs at once')
    @app_commands.checks.has_permissions(administrator=True)
    async def reload_all(self, interaction: discord.Interaction):
        await interaction.response.defer()
        
        try:
            # Get all loaded cogs
            cog_names = list(self.bot.cogs.keys())
            
            reloaded = []
            failed = []
            
            for cog_name in cog_names:
                # Don't reload the Admin cog while we're using it
                if cog_name == 'Admin':
                    continue
                    
                try:
                    # Find the extension name
                    extension_name = f'cogs.{cog_name.lower()}'
                    await self.bot.reload_extension(extension_name)
                    reloaded.append(cog_name)
                except Exception as e:
                    failed.append(f"{cog_name}: {str(e)}")
            
            # Reload Admin cog last
            try:
                await self.bot.reload_extension('cogs.admin')
                reloaded.append('Admin')
            except Exception as e:
                failed.append(f"Admin: {str(e)}")
            
            embed = discord.Embed(
                title="🔄 Reload All Cogs",
                color=discord.Color.green() if not failed else discord.Color.orange()
            )
            
            if reloaded:
                embed.add_field(
                    name=f"✅ Reloaded ({len(reloaded)})",
                    value="\n".join(reloaded),
                    inline=False
                )
            
            if failed:
                embed.add_field(
                    name=f"❌ Failed ({len(failed)})",
                    value="\n".join(failed),
                    inline=False
                )
            
            await interaction.followup.send(embed=embed)
            
        except Exception as e:
            embed = discord.Embed(
                title="❌ Reload All Failed",
                description=f"Error: {str(e)}",
                color=discord.Color.red()
            )
            await interaction.followup.send(embed=embed)

    @app_commands.command(name='resetallconfigs', description='Delete ALL config/data files (chat_config.json, itemmarket.json, etc.)')
    @app_commands.checks.has_permissions(administrator=True)
    async def reset_all_configs(self, interaction: discord.Interaction):
        try:
            await interaction.response.defer(ephemeral=True)
            
            # List of config files to delete
            config_files = [
                'chat_config.json',
                'itemmarket.json',
                'itemmarket_config.json'
            ]
            
            deleted = []
            not_found = []
            
            for file in config_files:
                if os.path.exists(file):
                    os.remove(file)
                    deleted.append(file)
                else:
                    not_found.append(file)
            
            embed = discord.Embed(
                title="⚠️ All Configs Reset",
                description=f"**Deleted {len(deleted)} file(s):**\n" + "\n".join(f"✅ {f}" for f in deleted),
                color=discord.Color.red()
            )
            
            if not_found:
                embed.add_field(
                    name="Not Found",
                    value="\n".join(f"❌ {f}" for f in not_found),
                    inline=False
                )
            
            embed.add_field(
                name="⚠️ Important",
                value="All configurations have been deleted. You need to run setup commands again and `/restart` the bot.",
                inline=False
            )
            
            await interaction.followup.send(embed=embed, ephemeral=True)
        
        except Exception as e:
            import traceback
            error_details = ''.join(traceback.format_exception(type(e), e, e.__traceback__))
            
            if len(error_details) > 1000:
                error_details = error_details[-1000:]
            
            embed = discord.Embed(
                title="❌ Error Resetting Configs",
                description=f"**Error Type:** `{type(e).__name__}`\n**Error Message:** {str(e)}",
                color=discord.Color.red()
            )
            embed.add_field(name="Full Error Details", value=f"```python\n{error_details}\n```", inline=False)
            
            await interaction.followup.send(embed=embed, ephemeral=True)

async def setup(bot):
    await bot.add_cog(Admin(bot))
