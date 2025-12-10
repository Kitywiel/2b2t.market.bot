import discord


from discord import app_commands
from discord.ext import commands
import json
import os
from datetime import datetime

class TicketSystem(commands.Cog):
    def __init__(self, bot):
        self.bot = bot
        self.tickets_file = 'tickets.json'
        self.config_file = 'ticket_config.json'
        self.load_data()

    def load_data(self):
        """Load ticket data from JSON file"""
        if os.path.exists(self.tickets_file):
            with open(self.tickets_file, 'r') as f:
                self.tickets = json.load(f)
        else:
            self.tickets = {}
            self.save_tickets()

        if os.path.exists(self.config_file):
            with open(self.config_file, 'r') as f:
                self.config = json.load(f)
        else:
            self.config = {}
            self.save_config()

    def save_tickets(self):
        """Save ticket data to JSON file"""
        with open(self.tickets_file, 'w') as f:
            json.dump(self.tickets, f, indent=4)

    def save_config(self):
        """Save config data to JSON file"""
        with open(self.config_file, 'w') as f:
            json.dump(self.config, f, indent=4)

    def get_ticket_category(self, guild_id):
        """Get the ticket category for a guild"""
        return self.config.get(str(guild_id), {}).get('category_id')

    def get_support_role(self, guild_id):
        """Get the support role for a guild"""
        return self.config.get(str(guild_id), {}).get('support_role_id')

    def get_ticket_counter(self, guild_id):
        """Get and increment the ticket counter"""
        guild_id_str = str(guild_id)
        if guild_id_str not in self.config:
            self.config[guild_id_str] = {}
        
        counter = self.config[guild_id_str].get('ticket_counter', 0) + 1
        self.config[guild_id_str]['ticket_counter'] = counter
        self.save_config()
        return counter

    @app_commands.command(name='ticket', description='Create a new support ticket')
    @app_commands.describe(reason='The reason for opening this ticket')
    async def create_ticket(self, interaction: discord.Interaction, reason: str = None):
        guild = interaction.guild
        user = interaction.user

        # Check if user already has an open ticket
        for ticket_id, ticket_data in self.tickets.items():
            if ticket_data.get('user_id') == user.id and ticket_data.get('status') == 'open':
                channel = guild.get_channel(ticket_data.get('channel_id'))
                if channel:
                    await interaction.response.send_message(
                        f"❌ You already have an open ticket: {channel.mention}",
                        ephemeral=True
                    )
                    return

        await interaction.response.defer(ephemeral=True)

        try:
            # Get or create ticket category
            category_id = self.get_ticket_category(guild.id)
            category = None
            
            if category_id:
                category = guild.get_channel(category_id)
            
            if not category:
                # Create new category
                category = await guild.create_category("🎫 Tickets")
                if str(guild.id) not in self.config:
                    self.config[str(guild.id)] = {}
                self.config[str(guild.id)]['category_id'] = category.id
                self.save_config()

            # Get ticket number
            ticket_num = self.get_ticket_counter(guild.id)
            
            # Create ticket channel
            channel_name = f"ticket-{ticket_num:04d}"
            
            # Set permissions
            overwrites = {
                guild.default_role: discord.PermissionOverwrite(read_messages=False),
                user: discord.PermissionOverwrite(read_messages=True, send_messages=True, attach_files=True),
                guild.me: discord.PermissionOverwrite(read_messages=True, send_messages=True, manage_channels=True)
            }

            # Add support role if configured
            support_role_id = self.get_support_role(guild.id)
            if support_role_id:
                support_role = guild.get_role(support_role_id)
                if support_role:
                    overwrites[support_role] = discord.PermissionOverwrite(read_messages=True, send_messages=True)

            channel = await guild.create_text_channel(
                name=channel_name,
                category=category,
                overwrites=overwrites
            )

            # Save ticket data
            ticket_id = f"{guild.id}-{channel.id}"
            self.tickets[ticket_id] = {
                'user_id': user.id,
                'channel_id': channel.id,
                'guild_id': guild.id,
                'ticket_number': ticket_num,
                'status': 'open',
                'reason': reason,
                'created_at': datetime.now().isoformat()
            }
            self.save_tickets()

            # Create ticket embed
            embed = discord.Embed(
                title=f"🎫 Ticket #{ticket_num:04d}",
                description=f"Thank you for creating a ticket, {user.mention}!\nSupport will be with you shortly.",
                color=discord.Color.green()
            )
            embed.add_field(name="Opened by", value=user.mention, inline=True)
            embed.add_field(name="Status", value="🟢 Open", inline=True)
            
            if reason:
                embed.add_field(name="Reason", value=reason, inline=False)
            
            embed.set_footer(text=f"Created at {datetime.now().strftime('%Y-%m-%d %H:%M:%S')}")

            # Create close button
            view = TicketControls(self)
            await channel.send(embed=embed, view=view)

            await interaction.followup.send(
                f"✅ Ticket created! {channel.mention}",
                ephemeral=True
            )

        except Exception as e:
            await interaction.followup.send(
                f"❌ Error creating ticket: {str(e)}",
                ephemeral=True
            )

    @app_commands.command(name='closeticket', description='Close the current ticket')
    async def close_ticket(self, interaction: discord.Interaction):
        channel = interaction.channel
        
        # Find ticket
        ticket_id = f"{interaction.guild.id}-{channel.id}"
        
        if ticket_id not in self.tickets:
            await interaction.response.send_message(
                "❌ This is not a ticket channel!",
                ephemeral=True
            )
            return

        ticket = self.tickets[ticket_id]
        
        if ticket['status'] != 'open':
            await interaction.response.send_message(
                "❌ This ticket is already closed!",
                ephemeral=True
            )
            return

        await interaction.response.defer()

        # Update ticket status
        ticket['status'] = 'closed'
        ticket['closed_at'] = datetime.now().isoformat()
        ticket['closed_by'] = interaction.user.id
        self.save_tickets()

        # Send closing message
        embed = discord.Embed(
            title="🔒 Ticket Closed",
            description=f"This ticket has been closed by {interaction.user.mention}.",
            color=discord.Color.red()
        )
        embed.set_footer(text="This channel will be deleted in 10 seconds.")
        
        await interaction.followup.send(embed=embed)

        # Delete channel after delay
        await channel.send("Deleting channel in 10 seconds...")
        await discord.utils.sleep_until(discord.utils.utcnow() + discord.timedelta(seconds=10))
        await channel.delete()

    @app_commands.command(name='addtoticket', description='Add a user to the current ticket')
    @app_commands.describe(user='The user to add to this ticket')
    async def add_to_ticket(self, interaction: discord.Interaction, user: discord.Member):
        channel = interaction.channel
        ticket_id = f"{interaction.guild.id}-{channel.id}"
        
        if ticket_id not in self.tickets:
            await interaction.response.send_message(
                "❌ This is not a ticket channel!",
                ephemeral=True
            )
            return

        await channel.set_permissions(user, read_messages=True, send_messages=True)
        
        await interaction.response.send_message(
            f"✅ Added {user.mention} to the ticket!",
            ephemeral=True
        )
        await channel.send(f"{user.mention} has been added to this ticket.")

    @app_commands.command(name='removeticket', description='Remove a user from the current ticket')
    @app_commands.describe(user='The user to remove from this ticket')
    async def remove_from_ticket(self, interaction: discord.Interaction, user: discord.Member):
        channel = interaction.channel
        ticket_id = f"{interaction.guild.id}-{channel.id}"
        
        if ticket_id not in self.tickets:
            await interaction.response.send_message(
                "❌ This is not a ticket channel!",
                ephemeral=True
            )
            return

        ticket = self.tickets[ticket_id]
        if ticket['user_id'] == user.id:
            await interaction.response.send_message(
                "❌ You cannot remove the ticket creator!",
                ephemeral=True
            )
            return

        await channel.set_permissions(user, overwrite=None)
        
        await interaction.response.send_message(
            f"✅ Removed {user.mention} from the ticket!",
            ephemeral=True
        )
        await channel.send(f"{user.mention} has been removed from this ticket.")

    @app_commands.command(name='setuptickets', description='Setup the ticket system for this server')
    @app_commands.describe(support_role='The role that can manage tickets')
    @app_commands.checks.has_permissions(administrator=True)
    async def setup_tickets(self, interaction: discord.Interaction, support_role: discord.Role = None):
        guild_id_str = str(interaction.guild.id)
        
        if guild_id_str not in self.config:
            self.config[guild_id_str] = {}
        
        if support_role:
            self.config[guild_id_str]['support_role_id'] = support_role.id
        
        self.save_config()
        
        embed = discord.Embed(
            title="✅ Ticket System Setup",
            description="The ticket system has been configured!",
            color=discord.Color.green()
        )
        
        if support_role:
            embed.add_field(name="Support Role", value=support_role.mention, inline=False)
        
        embed.add_field(
            name="How to use",
            value="Users can create tickets with `/ticket [reason]`\nStaff can close tickets with `/closeticket`",
            inline=False
        )
        
        await interaction.response.send_message(embed=embed)

    @app_commands.command(name='ticketstats', description='View ticket statistics')
    async def ticket_stats(self, interaction: discord.Interaction):
        guild_tickets = [t for t in self.tickets.values() if t['guild_id'] == interaction.guild.id]
        
        open_tickets = len([t for t in guild_tickets if t['status'] == 'open'])
        closed_tickets = len([t for t in guild_tickets if t['status'] == 'closed'])
        total_tickets = len(guild_tickets)
        
        embed = discord.Embed(
            title="📊 Ticket Statistics",
            color=discord.Color.blue()
        )
        embed.add_field(name="🟢 Open", value=open_tickets, inline=True)
        embed.add_field(name="🔴 Closed", value=closed_tickets, inline=True)
        embed.add_field(name="📋 Total", value=total_tickets, inline=True)
        
        await interaction.response.send_message(embed=embed)


class TicketControls(discord.ui.View):
    def __init__(self, cog):
        super().__init__(timeout=None)
        self.cog = cog

    @discord.ui.button(label="Close Ticket", style=discord.ButtonStyle.danger, emoji="🔒")
    async def close_button(self, interaction: discord.Interaction, button: discord.ui.Button):
        channel = interaction.channel
        ticket_id = f"{interaction.guild.id}-{channel.id}"
        
        if ticket_id not in self.cog.tickets:
            await interaction.response.send_message(
                "❌ This is not a ticket channel!",
                ephemeral=True
            )
            return

        ticket = self.cog.tickets[ticket_id]
        
        if ticket['status'] != 'open':
            await interaction.response.send_message(
                "❌ This ticket is already closed!",
                ephemeral=True
            )
            return

        await interaction.response.defer()

        # Update ticket status
        ticket['status'] = 'closed'
        ticket['closed_at'] = datetime.now().isoformat()
        ticket['closed_by'] = interaction.user.id
        self.cog.save_tickets()

        # Send closing message
        embed = discord.Embed(
            title="🔒 Ticket Closed",
            description=f"This ticket has been closed by {interaction.user.mention}.",
            color=discord.Color.red()
        )
        embed.set_footer(text="This channel will be deleted in 10 seconds.")
        
        await interaction.followup.send(embed=embed)

        # Delete channel after delay
        await discord.utils.sleep_until(discord.utils.utcnow() + discord.timedelta(seconds=10))
        await channel.delete()


async def setup(bot):
    await bot.add_cog(TicketSystem(bot))
