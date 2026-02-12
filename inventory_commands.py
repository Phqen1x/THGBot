import discord
from discord import app_commands
from discord.ext import commands
from typing import Optional
import json


class InventoryCog(commands.Cog):
    """Discord commands for inventory management."""

    def __init__(self, bot: commands.Bot, inventory_manager):
        self.bot = bot
        self.inventory = inventory_manager
        self.gamemaker_role_name = "Gamemaker"

    def has_gamemaker_role(self, interaction: discord.Interaction) -> bool:
        """Check if user has Gamemaker role."""
        if not interaction.user.roles:
            return False
        return any(role.name == self.gamemaker_role_name for role in interaction.user.roles)

    async def check_gamemaker_permission(self, interaction: discord.Interaction) -> bool:
        """Verify Gamemaker role and defer response."""
        if not self.has_gamemaker_role(interaction):
            await interaction.response.send_message(
                "❌ You do not have permission to use this command. (Gamemaker role required)",
                ephemeral=True
            )
            return False
        return True

    def _format_inventory_embed(
        self, 
        tribute_id: str, 
        items: dict, 
        capacity: int,
        title: str = "Inventory",
        error: Optional[str] = None
    ) -> discord.Embed:
        """Format inventory data as a Discord embed."""
        color = discord.Color.red() if error else discord.Color.blue()
        embed = discord.Embed(
            title=f"{title}: {tribute_id}",
            color=color
        )

        if error:
            embed.description = error
            return embed

        if not items:
            embed.description = "*(Inventory is empty)*"
        else:
            item_list = "\n".join(f"{key}. {value}" for key, value in sorted(items.items(), key=lambda x: int(x[0])))
            embed.add_field(name="Items", value=item_list, inline=False)

        item_count = len(items)
        embed.add_field(name="Item Count", value=f"{item_count}/{capacity}", inline=False)

        if item_count > capacity:
            embed.add_field(
                name="⚠️ WARNING",
                value=f"Inventory capacity ({capacity}) has been exceeded.",
                inline=False
            )

        return embed

    @app_commands.command(name="inventory-get", description="View a tribute's inventory")
    @app_commands.describe(tribute_id="The tribute ID to view")
    async def get_inventory(self, interaction: discord.Interaction, tribute_id: str):
        if not await self.check_gamemaker_permission(interaction):
            return

        await interaction.response.defer(ephemeral=True)
        
        success, data = self.inventory.get_inventory(tribute_id)
        
        if success:
            embed = self._format_inventory_embed(
                tribute_id,
                data["items"],
                data["capacity"],
                "Inventory"
            )
        else:
            embed = self._format_inventory_embed(
                tribute_id,
                {},
                0,
                "Inventory",
                error=data["error"]
            )

        await interaction.followup.send(embed=embed, ephemeral=True)

    @app_commands.command(name="inventory-add", description="Add an item to a tribute's inventory")
    @app_commands.describe(
        tribute_id="The tribute ID",
        item="The item name to add"
    )
    async def add_to_inventory(self, interaction: discord.Interaction, tribute_id: str, item: str):
        if not await self.check_gamemaker_permission(interaction):
            return

        await interaction.response.defer(ephemeral=True)

        success, data = self.inventory.add_to_inventory(tribute_id, item)

        if success:
            embed = self._format_inventory_embed(
                tribute_id,
                data["items"],
                data["capacity"],
                f"Added '{item}' to"
            )
        else:
            embed = self._format_inventory_embed(
                tribute_id,
                {},
                0,
                "Add to Inventory",
                error=data["error"]
            )

        await interaction.followup.send(embed=embed, ephemeral=True)

    @app_commands.command(name="inventory-remove", description="Remove an item from a tribute's inventory")
    @app_commands.describe(
        tribute_id="The tribute ID",
        item="The item name to remove"
    )
    async def remove_from_inventory(self, interaction: discord.Interaction, tribute_id: str, item: str):
        if not await self.check_gamemaker_permission(interaction):
            return

        await interaction.response.defer(ephemeral=True)

        success, data = self.inventory.remove_from_inventory(tribute_id, item)

        if success:
            embed = self._format_inventory_embed(
                tribute_id,
                data["items"],
                data["capacity"],
                f"Removed '{item}' from"
            )
        else:
            embed = self._format_inventory_embed(
                tribute_id,
                {},
                0,
                "Remove from Inventory",
                error=data["error"]
            )

        await interaction.followup.send(embed=embed, ephemeral=True)

    @app_commands.command(name="inventory-search", description="Search for which tributes have an item")
    @app_commands.describe(item="The item name to search for")
    async def search_inventories(self, interaction: discord.Interaction, item: str):
        if not await self.check_gamemaker_permission(interaction):
            return

        await interaction.response.defer(ephemeral=True)

        success, data = self.inventory.search_inventories(item)

        embed = discord.Embed(
            title=f"Search Results: '{item}'",
            color=discord.Color.blue()
        )

        tributes = data.get("tributes", [])
        if tributes:
            tribute_list = "\n".join(tributes)
            embed.add_field(name="Tributes with this item", value=tribute_list, inline=False)
        else:
            embed.description = "No tributes found with this item."

        await interaction.followup.send(embed=embed, ephemeral=True)

    @app_commands.command(name="inventory-clear", description="Clear a tribute's entire inventory")
    @app_commands.describe(tribute_id="The tribute ID to clear")
    async def clear_inventory(self, interaction: discord.Interaction, tribute_id: str):
        if not await self.check_gamemaker_permission(interaction):
            return

        await interaction.response.defer(ephemeral=True)

        success, data = self.inventory.clear_inventory(tribute_id)

        if success:
            embed = discord.Embed(
                title="Inventory Cleared",
                description=data["message"],
                color=discord.Color.green()
            )
        else:
            embed = discord.Embed(
                title="Clear Inventory",
                description=data["error"],
                color=discord.Color.red()
            )

        await interaction.followup.send(embed=embed, ephemeral=True)

    @app_commands.command(name="inventory-create", description="Create a new tribute inventory")
    @app_commands.describe(
        tribute_id="The tribute ID",
        capacity="Soft capacity limit (default: 10)"
    )
    async def create_inventory(
        self,
        interaction: discord.Interaction,
        tribute_id: str,
        capacity: Optional[int] = 10
    ):
        if not await self.check_gamemaker_permission(interaction):
            return

        await interaction.response.defer(ephemeral=True)

        self.inventory.create_tribute_inventory(tribute_id, capacity)

        embed = discord.Embed(
            title="Inventory Created",
            description=f"Created new inventory for tribute: {tribute_id}",
            color=discord.Color.green()
        )
        embed.add_field(name="Capacity", value=str(capacity), inline=False)

        await interaction.followup.send(embed=embed, ephemeral=True)


async def setup(bot: commands.Bot, inventory_manager):
    """Setup inventory cog."""
    await bot.add_cog(InventoryCog(bot, inventory_manager))
