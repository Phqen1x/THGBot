import discord
from discord import app_commands
import json


def _format_inventory_embed(
    tribute_id: str, 
    items: dict, 
    capacity: int,
    title: str = "Inventory",
    error: str = None
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


def has_gamemaker_role(interaction: discord.Interaction) -> bool:
    """Check if user has Gamemaker role."""
    if not interaction.user.roles:
        return False
    return any(role.name == "Gamemaker" for role in interaction.user.roles)


def register_inventory_commands(bot, inventory_manager):
    """Register inventory commands with the bot."""
    
    @bot.tree.command(name="inventory-create", description="Create a new tribute inventory")
    @app_commands.describe(
        tribute_id="The tribute ID",
        capacity="Soft capacity limit (default: 10)"
    )
    async def inventory_create(
        interaction: discord.Interaction,
        tribute_id: str,
        capacity: int = 10
    ):
        if not has_gamemaker_role(interaction):
            await interaction.response.send_message(
                "❌ You do not have permission to use this command. (Gamemaker role required)",
                ephemeral=True
            )
            return

        await interaction.response.defer(ephemeral=True)

        inventory_manager.create_tribute_inventory(tribute_id, capacity)

        embed = discord.Embed(
            title="Inventory Created",
            description=f"Created new inventory for tribute: {tribute_id}",
            color=discord.Color.green()
        )
        embed.add_field(name="Capacity", value=str(capacity), inline=False)

        await interaction.followup.send(embed=embed, ephemeral=True)

    @bot.tree.command(name="inventory-get", description="View a tribute's inventory")
    @app_commands.describe(tribute_id="The tribute ID to view")
    async def inventory_get(interaction: discord.Interaction, tribute_id: str):
        if not has_gamemaker_role(interaction):
            await interaction.response.send_message(
                "❌ You do not have permission to use this command. (Gamemaker role required)",
                ephemeral=True
            )
            return

        await interaction.response.defer(ephemeral=True)
        
        success, data = inventory_manager.get_inventory(tribute_id)
        
        if success:
            embed = _format_inventory_embed(
                tribute_id,
                data["items"],
                data["capacity"],
                "Inventory"
            )
        else:
            embed = _format_inventory_embed(
                tribute_id,
                {},
                0,
                "Inventory",
                error=data["error"]
            )

        await interaction.followup.send(embed=embed, ephemeral=True)

    @bot.tree.command(name="inventory-add", description="Add an item to a tribute's inventory")
    @app_commands.describe(
        tribute_id="The tribute ID",
        item="The item name to add"
    )
    async def inventory_add(interaction: discord.Interaction, tribute_id: str, item: str):
        if not has_gamemaker_role(interaction):
            await interaction.response.send_message(
                "❌ You do not have permission to use this command. (Gamemaker role required)",
                ephemeral=True
            )
            return

        await interaction.response.defer(ephemeral=True)

        success, data = inventory_manager.add_to_inventory(tribute_id, item)

        if success:
            embed = _format_inventory_embed(
                tribute_id,
                data["items"],
                data["capacity"],
                f"Added '{item}' to"
            )
        else:
            embed = _format_inventory_embed(
                tribute_id,
                {},
                0,
                "Add to Inventory",
                error=data["error"]
            )

        await interaction.followup.send(embed=embed, ephemeral=True)

    @bot.tree.command(name="inventory-remove", description="Remove an item from a tribute's inventory")
    @app_commands.describe(
        tribute_id="The tribute ID",
        item="The item name to remove"
    )
    async def inventory_remove(interaction: discord.Interaction, tribute_id: str, item: str):
        if not has_gamemaker_role(interaction):
            await interaction.response.send_message(
                "❌ You do not have permission to use this command. (Gamemaker role required)",
                ephemeral=True
            )
            return

        await interaction.response.defer(ephemeral=True)

        success, data = inventory_manager.remove_from_inventory(tribute_id, item)

        if success:
            embed = _format_inventory_embed(
                tribute_id,
                data["items"],
                data["capacity"],
                f"Removed '{item}' from"
            )
        else:
            embed = _format_inventory_embed(
                tribute_id,
                {},
                0,
                "Remove from Inventory",
                error=data["error"]
            )

        await interaction.followup.send(embed=embed, ephemeral=True)

    @bot.tree.command(name="inventory-search", description="Search for which tributes have an item")
    @app_commands.describe(item="The item name to search for")
    async def inventory_search(interaction: discord.Interaction, item: str):
        if not has_gamemaker_role(interaction):
            await interaction.response.send_message(
                "❌ You do not have permission to use this command. (Gamemaker role required)",
                ephemeral=True
            )
            return

        await interaction.response.defer(ephemeral=True)

        success, data = inventory_manager.search_inventories(item)

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

    @bot.tree.command(name="inventory-clear", description="Clear a tribute's entire inventory")
    @app_commands.describe(tribute_id="The tribute ID to clear")
    async def inventory_clear(interaction: discord.Interaction, tribute_id: str):
        if not has_gamemaker_role(interaction):
            await interaction.response.send_message(
                "❌ You do not have permission to use this command. (Gamemaker role required)",
                ephemeral=True
            )
            return

        await interaction.response.defer(ephemeral=True)

        success, data = inventory_manager.clear_inventory(tribute_id)

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
