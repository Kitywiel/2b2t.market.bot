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
        self.load_data()

    def load_data(self):
        """Load item market data from JSON file"""
        if os.path.exists(self.market_file):
            with open(self.market_file, 'r') as f:
                self.items = json.load(f)
        else:
            self.items = []
            self.save_data()

    def save_data(self):
        """Save item market data to JSON file"""
        with open(self.market_file, 'w') as f:
            json.dump(self.items, f, indent=4)

    @app_commands.command(name='itemmarket', description='Add an item to the market')
    @app_commands.describe(
        name='The name of the item',
        price='The price of the item',
        fotourl='URL to the item photo',
        amount='The quantity available',
        itemid='Unique item identifier'
    )
    async def item_market(
        self, 
        interaction: discord.Interaction, 
        name: str, 
        price: str, 
        fotourl: str, 
        amount: int, 
        itemid: str
    ):
        await interaction.response.defer()

        try:
            # Create item entry
            item_entry = {
                'name': name,
                'price': price,
                'fotourl': fotourl,
                'amount': amount,
                'itemid': itemid,
                'seller_id': interaction.user.id,
                'seller_name': str(interaction.user),
                'timestamp': datetime.now().isoformat(),
                'guild_id': interaction.guild.id if interaction.guild else None
            }

            # Add to items list
            self.items.append(item_entry)
            self.save_data()

            # Create confirmation embed
            embed = discord.Embed(
                title="✅ Item Added to Market",
                description=f"**{name}** has been listed!",
                color=discord.Color.green()
            )
            embed.add_field(name="💰 Price", value=price, inline=True)
            embed.add_field(name="📦 Amount", value=str(amount), inline=True)
            embed.add_field(name="🆔 Item ID", value=itemid, inline=True)
            embed.add_field(name="👤 Seller", value=interaction.user.mention, inline=True)
            
            # Add photo if URL is provided
            if fotourl:
                embed.set_thumbnail(url=fotourl)
            
            embed.set_footer(text=f"Total items in market: {len(self.items)}")
            embed.timestamp = datetime.now()

            await interaction.followup.send(embed=embed)

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
        
        if item.get('fotourl'):
            embed.set_image(url=item['fotourl'])
        
        embed.set_footer(text=f"Listed on {item['timestamp'][:10]}")
        
        await interaction.followup.send(embed=embed)


async def setup(bot):
    await bot.add_cog(ItemMarket(bot))
