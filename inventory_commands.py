import discord
from discord import app_commands
import json


def _format_inventory_embed(
    tribute_id: str, 
    items: dict, 
    capacity: int,
    equipped: dict = None,
    equipped_capacity: int = None,
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

    # Equipped section (displayed first)
    if equipped is not None:
        if not equipped:
            embed.add_field(name="⚔️ Equipped", value="*(No equipped items)*", inline=False)
        else:
            equipped_list = "\n".join(f"{key}. {value}" for key, value in sorted(equipped.items(), key=lambda x: int(x[0])))
            embed.add_field(name="⚔️ Equipped", value=equipped_list, inline=False)
        
        equipped_count = len(equipped)
        if equipped_capacity:
            embed.add_field(name="Equipped Count", value=f"{equipped_count}/{equipped_capacity}", inline=True)
            if equipped_count > equipped_capacity:
                embed.add_field(
                    name="⚠️ WARNING",
                    value=f"Equipped capacity ({equipped_capacity}) has been exceeded.",
                    inline=False
                )

    # Items section
    if not items:
        embed.add_field(name="📦 Inventory", value="*(Inventory is empty)*", inline=False)
    else:
        item_list = "\n".join(f"{key}. {value}" for key, value in sorted(items.items(), key=lambda x: int(x[0])))
        embed.add_field(name="📦 Inventory", value=item_list, inline=False)

    item_count = len(items)
    embed.add_field(name="Inventory Count", value=f"{item_count}/{capacity}", inline=True)

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
                equipped=data.get("equipped"),
                equipped_capacity=data.get("equipped_capacity"),
                title="Inventory"
            )
        else:
            embed = _format_inventory_embed(
                tribute_id,
                {},
                0,
                title="Inventory",
                error=data["error"]
            )

        await interaction.followup.send(embed=embed, ephemeral=True)

    @bot.tree.command(name="inventory-add", description="Add an item to a tribute's inventory or equipped section")
    @app_commands.describe(
        tribute_id="The tribute ID",
        item="The item name to add",
        equipped="Add to equipped section instead of inventory (default: False)"
    )
    async def inventory_add(interaction: discord.Interaction, tribute_id: str, item: str, equipped: bool = False):
        if not has_gamemaker_role(interaction):
            await interaction.response.send_message(
                "❌ You do not have permission to use this command. (Gamemaker role required)",
                ephemeral=True
            )
            return

        await interaction.response.defer(ephemeral=True)

        if equipped:
            success, data = inventory_manager.add_to_equipped(tribute_id, item)
            action = f"Added '{item}' to equipped for"
        else:
            success, data = inventory_manager.add_to_inventory(tribute_id, item)
            action = f"Added '{item}' to"

        if success:
            embed = _format_inventory_embed(
                tribute_id,
                data["items"],
                data["capacity"],
                equipped=data.get("equipped"),
                equipped_capacity=data.get("equipped_capacity"),
                title=action
            )
        else:
            embed = _format_inventory_embed(
                tribute_id,
                {},
                0,
                title="Add to Inventory",
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
                equipped=data.get("equipped"),
                equipped_capacity=data.get("equipped_capacity"),
                title=f"Removed '{item}' from"
            )
        else:
            embed = _format_inventory_embed(
                tribute_id,
                {},
                0,
                title="Remove from Inventory",
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

    @bot.tree.command(name="inventory-equip", description="Move an item from inventory to equipped")
    @app_commands.describe(
        tribute_id="The tribute ID",
        item_number="The item number to equip"
    )
    async def inventory_equip(interaction: discord.Interaction, tribute_id: str, item_number: int):
        if not has_gamemaker_role(interaction):
            await interaction.response.send_message(
                "❌ You do not have permission to use this command. (Gamemaker role required)",
                ephemeral=True
            )
            return

        await interaction.response.defer(ephemeral=True)

        success, data = inventory_manager.equip_item(tribute_id, str(item_number))

        if success:
            embed = _format_inventory_embed(
                tribute_id,
                data["items"],
                data["capacity"],
                equipped=data.get("equipped"),
                equipped_capacity=data.get("equipped_capacity"),
                title="Item Equipped"
            )
            embed.description = data.get("message")
        else:
            embed = discord.Embed(
                title="Equip Item",
                description=data["error"],
                color=discord.Color.red()
            )

        await interaction.followup.send(embed=embed, ephemeral=True)

    @bot.tree.command(name="inventory-unequip", description="Move an item from equipped back to inventory")
    @app_commands.describe(
        tribute_id="The tribute ID",
        item_number="The equipped item number to unequip"
    )
    async def inventory_unequip(interaction: discord.Interaction, tribute_id: str, item_number: int):
        if not has_gamemaker_role(interaction):
            await interaction.response.send_message(
                "❌ You do not have permission to use this command. (Gamemaker role required)",
                ephemeral=True
            )
            return

        await interaction.response.defer(ephemeral=True)

        success, data = inventory_manager.unequip_item(tribute_id, str(item_number))

        if success:
            embed = _format_inventory_embed(
                tribute_id,
                data["items"],
                data["capacity"],
                equipped=data.get("equipped"),
                equipped_capacity=data.get("equipped_capacity"),
                title="Item Unequipped"
            )
            embed.description = data.get("message")
        else:
            embed = discord.Embed(
                title="Unequip Item",
                description=data["error"],
                color=discord.Color.red()
            )

        await interaction.followup.send(embed=embed, ephemeral=True)
