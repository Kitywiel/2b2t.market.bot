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

async def setup(bot):
    await bot.add_cog(Admin(bot))
