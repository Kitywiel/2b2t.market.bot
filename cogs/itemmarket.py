import discord
from discord import app_commands
from discord.ext import commands
import json
import os
from datetime import datetime

class ItemMarket(commands.Cog):
    def __init__(self, bot):
        self.bot = bot
        self.market_file = 'itemmarket.json'
        self.config_file = 'itemmarket_config.json'
        self.load_data()

    def load_data(self):
        """Load item market data from JSON file"""
        if os.path.exists(self.market_file):
            with open(self.market_file, 'r') as f:
                self.items = json.load(f)
        else:
            self.items = []
            self.save_data()
        
        if os.path.exists(self.config_file):
            with open(self.config_file, 'r') as f:
                self.config = json.load(f)
        else:
            self.config = {}
            self.save_config()

    def save_data(self):
        """Save item market data to JSON file"""
        with open(self.market_file, 'w') as f:
            json.dump(self.items, f, indent=4)
    
    def save_config(self):
        """Save config data to JSON file"""
        with open(self.config_file, 'w') as f:
            json.dump(self.config, f, indent=4)
    
    def get_item_channel(self, guild_id):
        """Get the configured item send channel for a guild"""
        return self.config.get(str(guild_id), {}).get('item_channel_id')

    @app_commands.command(name='itemmarket', description='Add an item to the market')
    @app_commands.describe(
        name='The name of the item',
        price='The price of the item',
        imgurl='URL to the item image',
        amount='The quantity available',
        itemid='Unique item identifier'
    )
    async def item_market(
        self, 
        interaction: discord.Interaction, 
        name: str, 
        price: str, 
        imgurl: str, 
        amount: int, 
        itemid: str
    ):
        await interaction.response.defer()

        try:
            # Create item entry
            item_entry = {
                'name': name,
                'price': price,
                'imgurl': imgurl,
                'amount': amount,
                'itemid': itemid,
                'seller_id': interaction.user.id,
                'seller_name': str(interaction.user),
                'timestamp': datetime.now().isoformat(),
                'guild_id': interaction.guild.id if interaction.guild else None,
                'message_id': None  # Will be set when posted to channel
            }

            # Add to items list
            self.items.append(item_entry)
            item_index = len(self.items) - 1
            self.save_data()

            # Create market listing embed with new layout
            embed = discord.Embed(
                title=name,
                color=discord.Color.blue()
            )
            
            # Set image at the top
            if imgurl:
                embed.set_image(url=imgurl)
            
            # Price field
            embed.add_field(name="💰 Price", value=price, inline=False)
            
            # Amount, Item ID, and Seller on same line
            embed.add_field(name="📦 Amount", value=str(amount), inline=True)
            embed.add_field(name="🆔 Item ID", value=itemid, inline=True)
            embed.add_field(name="👤 Seller", value=interaction.user.mention, inline=True)
            
            # Upload time at the footer
            embed.set_footer(text=f"Listed on {datetime.now().strftime('%Y-%m-%d %H:%M:%S')}")
            embed.timestamp = datetime.now()

            # Create buy button
            view = BuyButton(self, item_index)
            
            # Send to configured channel if available
            channel_id = self.get_item_channel(interaction.guild.id)
            if channel_id:
                channel = interaction.guild.get_channel(channel_id)
                if channel:
                    message = await channel.send(embed=embed, view=view)
                    # Store message ID for later editing/deletion
                    self.items[item_index]['message_id'] = message.id
                    self.save_data()
                    
                    await interaction.followup.send(
                        f"✅ Item listed in {channel.mention}!",
                        ephemeral=True
                    )
                else:
                    await interaction.followup.send(embed=embed, view=view)
            else:
                await interaction.followup.send(embed=embed, view=view)

        except Exception as e:
            import traceback
            error_details = ''.join(traceback.format_exception(type(e), e, e.__traceback__))
            
            embed = discord.Embed(
                title="❌ Error Adding Item",
                description=f"**Error Type:** `{type(e).__name__}`\n**Error Message:** {str(e)}",
                color=discord.Color.red()
            )
            
            # Add full traceback in a code block (truncate if too long)
            if len(error_details) > 1000:
                error_details = error_details[-1000:]  # Last 1000 chars
            
            embed.add_field(
                name="Full Error Details",
                value=f"```python\n{error_details}\n```",
                inline=False
            )
            
            await interaction.followup.send(embed=embed, ephemeral=True)

    @app_commands.command(name='setupmarket', description='Setup the item market system')
    @app_commands.describe(item_channel='The channel where items will be posted')
    @app_commands.checks.has_permissions(administrator=True)
    async def setup_market(self, interaction: discord.Interaction, item_channel: discord.TextChannel):
        try:
            guild_id_str = str(interaction.guild.id)
            
            if guild_id_str not in self.config:
                self.config[guild_id_str] = {}
            
            self.config[guild_id_str]['item_channel_id'] = item_channel.id
            self.save_config()
            
            embed = discord.Embed(
                title="✅ Market System Configured",
                description="The item market has been set up!",
                color=discord.Color.green()
            )
            embed.add_field(
                name="📦 Item Channel",
                value=item_channel.mention,
                inline=False
            )
            embed.add_field(
                name="How to use",
                value=(
                    "• Use `/itemmarket` to list items\n"
                    "• Items will be posted in the configured channel\n"
                    "• Use `/removeitem` to delete listings\n"
                    "• Use `/updateitem` to edit listings"
                ),
                inline=False
            )
            
            await interaction.response.send_message(embed=embed)
        
        except Exception as e:
            import traceback
            error_details = ''.join(traceback.format_exception(type(e), e, e.__traceback__))
            
            embed = discord.Embed(
                title="❌ Error in Setup",
                description=f"**Error Type:** `{type(e).__name__}`\n**Error Message:** {str(e)}",
                color=discord.Color.red()
            )
            
            if len(error_details) > 1000:
                error_details = error_details[-1000:]
            
            embed.add_field(
                name="Full Error Details",
                value=f"```python\n{error_details}\n```",
                inline=False
            )
            
            try:
                await interaction.response.send_message(embed=embed, ephemeral=True)
            except:
                await interaction.followup.send(embed=embed, ephemeral=True)

    @app_commands.command(name='removeitem', description='Remove an item from the market')
    @app_commands.describe(message_id='The message ID of the item listing to remove')
    async def remove_item(self, interaction: discord.Interaction, message_id: str):
        await interaction.response.defer(ephemeral=True)
        
        try:
            msg_id = int(message_id)
        except ValueError:
            await interaction.followup.send("❌ Invalid message ID format!", ephemeral=True)
            return
        
        # Find item by message ID
        item_index = None
        item = None
        for i, itm in enumerate(self.items):
            if itm.get('message_id') == msg_id:
                item_index = i
                item = itm
                break
        
        if not item:
            await interaction.followup.send("❌ Item not found with that message ID!", ephemeral=True)
            return
        
        # Check permissions: must be admin or the seller
        is_admin = interaction.user.guild_permissions.administrator
        is_seller = item['seller_id'] == interaction.user.id
        
        if not (is_admin or is_seller):
            await interaction.followup.send(
                "❌ You don't have permission to remove this item!\n"
                "You must be an administrator or the seller.",
                ephemeral=True
            )
            return
        
        # Delete the message if it exists
        channel_id = self.get_item_channel(interaction.guild.id)
        if channel_id:
            channel = interaction.guild.get_channel(channel_id)
            if channel:
                try:
                    message = await channel.fetch_message(msg_id)
                    await message.delete()
                except:
                    pass  # Message might already be deleted
        
        # Remove from database
        self.items.pop(item_index)
        self.save_data()
        
        embed = discord.Embed(
            title="✅ Item Removed",
            description=f"**{item['name']}** has been removed from the market.",
            color=discord.Color.green()
        )
        await interaction.followup.send(embed=embed, ephemeral=True)

    @app_commands.command(name='updateitem', description='Update an item listing')
    @app_commands.describe(
        message_id='The message ID of the item to update',
        name='New item name (optional)',
        price='New price (optional)',
        imgurl='New image URL (optional)',
        amount='New amount (optional)',
        itemid='New item ID (optional)'
    )
    async def update_item(
        self,
        interaction: discord.Interaction,
        message_id: str,
        name: str = None,
        price: str = None,
        imgurl: str = None,
        amount: int = None,
        itemid: str = None
    ):
        await interaction.response.defer(ephemeral=True)
        
        try:
            msg_id = int(message_id)
        except ValueError:
            await interaction.followup.send("❌ Invalid message ID format!", ephemeral=True)
            return
        
        # Find item by message ID
        item_index = None
        item = None
        for i, itm in enumerate(self.items):
            if itm.get('message_id') == msg_id:
                item_index = i
                item = itm
                break
        
        if not item:
            await interaction.followup.send("❌ Item not found with that message ID!", ephemeral=True)
            return
        
        # Check permissions: must be admin or the seller
        is_admin = interaction.user.guild_permissions.administrator
        is_seller = item['seller_id'] == interaction.user.id
        
        if not (is_admin or is_seller):
            await interaction.followup.send(
                "❌ You don't have permission to update this item!\n"
                "You must be an administrator or the seller.",
                ephemeral=True
            )
            return
        
        # Update fields if provided
        if name:
            item['name'] = name
        if price:
            item['price'] = price
        if imgurl:
            item['imgurl'] = imgurl
        if amount is not None:
            item['amount'] = amount
        if itemid:
            item['itemid'] = itemid
        
        self.save_data()
        
        # Update the message if it exists
        channel_id = self.get_item_channel(interaction.guild.id)
        if channel_id:
            channel = interaction.guild.get_channel(channel_id)
            if channel:
                try:
                    message = await channel.fetch_message(msg_id)
                    
                    # Recreate the embed with updated info
                    embed = discord.Embed(
                        title=item['name'],
                        color=discord.Color.blue()
                    )
                    
                    if item.get('imgurl'):
                        embed.set_image(url=item['imgurl'])
                    
                    embed.add_field(name="💰 Price", value=item['price'], inline=False)
                    embed.add_field(name="📦 Amount", value=str(item['amount']), inline=True)
                    embed.add_field(name="🆔 Item ID", value=item['itemid'], inline=True)
                    embed.add_field(name="👤 Seller", value=f"<@{item['seller_id']}>", inline=True)
                    
                    embed.set_footer(text=f"Listed on {item['timestamp'][:19]} | Updated")
                    
                    # Recreate the buy button
                    view = BuyButton(self, item_index)
                    
                    await message.edit(embed=embed, view=view)
                except Exception as e:
                    await interaction.followup.send(
                        f"⚠️ Item updated in database but couldn't update message: {str(e)}",
                        ephemeral=True
                    )
                    return
        
        embed = discord.Embed(
            title="✅ Item Updated",
            description=f"**{item['name']}** has been updated successfully.",
            color=discord.Color.green()
        )
        await interaction.followup.send(embed=embed, ephemeral=True)

    @app_commands.command(name='viewmarket', description='View all items in the market')
    async def view_market(self, interaction: discord.Interaction):
        await interaction.response.defer()

        if not self.items:
            embed = discord.Embed(
                title="📦 Item Market",
                description="The market is currently empty. Use `/itemmarket` to add items!",
                color=discord.Color.blue()
            )
            await interaction.followup.send(embed=embed)
            return

        # Show latest 10 items
        recent_items = self.items[-10:]
        
        embed = discord.Embed(
            title="📦 Item Market",
            description=f"Showing {len(recent_items)} of {len(self.items)} items",
            color=discord.Color.blue()
        )

        for item in recent_items:
            field_value = (
                f"💰 **Price:** {item['price']}\n"
                f"📦 **Amount:** {item['amount']}\n"
                f"🆔 **ID:** {item['itemid']}\n"
                f"👤 **Seller:** <@{item['seller_id']}>"
            )
            embed.add_field(
                name=f"{item['name']}", 
                value=field_value, 
                inline=False
            )

        embed.set_footer(text="Use /searchmarket <itemid> to find specific items")
        
        await interaction.followup.send(embed=embed)

    @app_commands.command(name='searchmarket', description='Search for an item by ID')
    @app_commands.describe(itemid='The item ID to search for')
    async def search_market(self, interaction: discord.Interaction, itemid: str):
        await interaction.response.defer()

        # Find items with matching ID
        matching_items = [item for item in self.items if item['itemid'].lower() == itemid.lower()]

        if not matching_items:
            embed = discord.Embed(
                title="❌ Not Found",
                description=f"No items found with ID: `{itemid}`",
                color=discord.Color.red()
            )
            await interaction.followup.send(embed=embed, ephemeral=True)
            return

        item = matching_items[0]
        
        embed = discord.Embed(
            title=f"📦 {item['name']}",
            color=discord.Color.green()
        )
        embed.add_field(name="💰 Price", value=item['price'], inline=True)
        embed.add_field(name="📦 Amount", value=str(item['amount']), inline=True)
        embed.add_field(name="🆔 Item ID", value=item['itemid'], inline=True)
        embed.add_field(name="👤 Seller", value=f"<@{item['seller_id']}>", inline=True)
        
        if item.get('imgurl'):
            embed.set_image(url=item['imgurl'])
        
        embed.set_footer(text=f"Listed on {item['timestamp'][:10]}")
        
        await interaction.followup.send(embed=embed)


class BuyButton(discord.ui.View):
    def __init__(self, cog, item_index):
        super().__init__(timeout=None)
        self.cog = cog
        self.item_index = item_index

    @discord.ui.button(label="💰 Buy", style=discord.ButtonStyle.green)
    async def buy_button(self, interaction: discord.Interaction, button: discord.ui.Button):
        # Check if item still exists
        if self.item_index >= len(self.cog.items):
            await interaction.response.send_message(
                "❌ This item is no longer available.",
                ephemeral=True
            )
            return
        
        item = self.cog.items[self.item_index]
        
        # Show modal to ask for amount
        modal = BuyModal(self.cog, self.item_index, item)
        await interaction.response.send_modal(modal)


class BuyModal(discord.ui.Modal, title="Purchase Item"):
    def __init__(self, cog, item_index, item):
        super().__init__()
        self.cog = cog
        self.item_index = item_index
        self.item = item
        
        self.amount_input = discord.ui.TextInput(
            label="How many do you want to buy?",
            placeholder=f"Max available: {item['amount']}",
            required=True,
            max_length=10
        )
        self.add_item(self.amount_input)

    async def on_submit(self, interaction: discord.Interaction):
        # Refresh item data to get current amount
        if self.item_index >= len(self.cog.items):
            await interaction.response.send_message(
                "❌ This item is no longer available.",
                ephemeral=True
            )
            return
        
        current_item = self.cog.items[self.item_index]
        
        try:
            buy_amount = int(self.amount_input.value)
        except ValueError:
            await interaction.response.send_message(
                "❌ Please enter a valid number!",
                ephemeral=True
            )
            return
        
        if buy_amount <= 0:
            await interaction.response.send_message(
                "❌ Amount must be greater than 0!",
                ephemeral=True
            )
            return
        
        if buy_amount > current_item['amount']:
            await interaction.response.send_message(
                f"❌ Not enough stock! Only {current_item['amount']} available.\nYou tried to buy {buy_amount}.",
                ephemeral=True
            )
            return
        
        # Create purchase confirmation embed
        embed = discord.Embed(
            title="✅ Purchase Request Sent",
            description=f"You want to buy **{buy_amount}x {current_item['name']}**",
            color=discord.Color.green()
        )
        embed.add_field(name="💰 Total Price", value=f"{buy_amount}x {current_item['price']}", inline=False)
        embed.add_field(name="👤 Seller", value=f"<@{current_item['seller_id']}>", inline=False)
        embed.add_field(
            name="📩 Next Steps",
            value=f"Contact the seller <@{current_item['seller_id']}> to complete the transaction.",
            inline=False
        )
        
        await interaction.response.send_message(embed=embed, ephemeral=True)
        
        # Notify the seller
        try:
            seller = await interaction.client.fetch_user(current_item['seller_id'])
            seller_embed = discord.Embed(
                title="🔔 New Purchase Request",
                description=f"**{interaction.user}** wants to buy your item!",
                color=discord.Color.blue()
            )
            seller_embed.add_field(name="Item", value=current_item['name'], inline=True)
            seller_embed.add_field(name="Amount", value=str(buy_amount), inline=True)
            seller_embed.add_field(name="Buyer", value=interaction.user.mention, inline=False)
            
            await seller.send(embed=seller_embed)
        except:
            pass  # Seller might have DMs disabled


async def setup(bot):
    await bot.add_cog(ItemMarket(bot))

