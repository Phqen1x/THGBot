"""
Tribute management commands for THGBot with unified data view.
Allows Gamemakers to create, view, and manage tribute records with all associated data.
"""

import discord
from database import SQLDatabase
from inventory import Inventory
from confirmationview import ConfirmationView
from typing import Optional
import time
import os
import logging
import datetime

logger = logging.getLogger(__name__)


def register_tribute_commands(bot, db: SQLDatabase):
    """Register all tribute commands with the bot."""

    async def log_to_channel(
        interaction: discord.Interaction, title: str, description: str, color=None
    ):
        """Helper function to send logs to the configured log channel."""
        try:
            guild_id = str(interaction.guild.id)
            if guild_id not in bot.config or not bot.config[guild_id].get(
                "log_channel_id"
            ):
                return

            log_channel = bot.get_channel(bot.config[guild_id]["log_channel_id"])
            if not log_channel:
                return

            log_embed = discord.Embed(
                title=title,
                description=description,
                color=color or discord.Color.blue(),
            )
            log_embed.set_author(
                name=f"{interaction.user.name}", icon_url=f"{interaction.user.avatar}"
            )
            if interaction.guild.icon:
                log_embed.set_thumbnail(url=interaction.guild.icon.url)
            log_embed.timestamp = datetime.datetime.now()
            await log_channel.send(embed=log_embed)
        except Exception as e:
            logger.error(f"Failed to log to channel: {e}")

    async def get_category_channels(interaction: discord.Interaction, current: str):
        """Autocomplete function to get channels from configured category."""
        try:
            guild_id = str(interaction.guild.id)
            if guild_id not in bot.config or not bot.config[guild_id].get(
                "category_id"
            ):
                return []

            category = interaction.guild.get_channel(
                bot.config[guild_id]["category_id"]
            )
            if not category or not isinstance(category, discord.CategoryChannel):
                return []

            # Get all text channels in the category
            channels = [
                ch for ch in category.channels if isinstance(ch, discord.TextChannel)
            ]

            # Filter by current input
            matching = [ch for ch in channels if current.lower() in ch.name.lower()]

            # Return as Choice objects for autocomplete
            return [
                discord.app_commands.Choice(name=ch.name, value=str(ch.id))
                for ch in matching[:25]
            ]
        except Exception as e:
            logger.error(f"Error in get_category_channels: {e}")
            return []

    @bot.tree.command(name="create-tribute", description="Create a new tribute")
    @discord.app_commands.describe(
        tribute_id="Tribute ID (e.g., D1F, D1M)",
        tribute_name="Tribute name (e.g., John Doe)",
        user="Discord user to link to this tribute",
        prompt_channel="Channel where prompts will be sent (must be in configured category)",
        inventory_capacity="Number of inventory slots (default: 10)",
        equipped_capacity="Number of equipped slots (default: 5)",
        face_claim="(Optional) Image file or URL for character face claim",
    )
    @discord.app_commands.autocomplete(prompt_channel=get_category_channels)
    async def create_tribute(
        interaction: discord.Interaction,
        tribute_id: str,
        tribute_name: str,
        user: discord.User,
        prompt_channel: str,
        inventory_capacity: int = 10,
        equipped_capacity: int = 5,
        face_claim: Optional[discord.Attachment] = None,
    ):
        """Create a new tribute with ID, name, Discord user link, channel, and optional face claim."""

        # Check Gamemaker role
        if not any(role.name == "Gamemaker" for role in interaction.user.roles):
            await interaction.response.send_message(
                "❌ Permission Denied: You must have the Gamemaker role.",
                ephemeral=True,
            )
            return

        # Validate tribute_id format
        tribute_id = tribute_id.strip().upper()
        if len(tribute_id) > 5 or not tribute_id[1].isdigit():
            await interaction.response.send_message(
                f"❌ Invalid tribute ID format: `{tribute_id}`. Format should be like D1F, D1M, etc.",
                ephemeral=True,
            )
            return

        # Validate and get channel
        try:
            prompt_channel_id = int(prompt_channel)
            channel = interaction.guild.get_channel(prompt_channel_id)

            if not channel:
                await interaction.response.send_message(
                    "❌ Channel not found.", ephemeral=True
                )
                return

            if not isinstance(channel, discord.TextChannel):
                await interaction.response.send_message(
                    "❌ Prompt channel must be a text channel.", ephemeral=True
                )
                return

            # Validate channel is in configured category
            guild_id = str(interaction.guild.id)
            if guild_id in bot.config and bot.config[guild_id].get("category_id"):
                category = interaction.guild.get_channel(
                    bot.config[guild_id]["category_id"]
                )
                if category and channel.category_id != category.id:
                    await interaction.response.send_message(
                        f"❌ Prompt channel must be in the configured category.",
                        ephemeral=True,
                    )
                    return

        except (ValueError, AttributeError):
            await interaction.response.send_message(
                "❌ Invalid channel specified.", ephemeral=True
            )
            return

            return

        # Create user mention string
        user_mention = f"<@{user.id}>"
        guild_id = interaction.guild.id if interaction.guild else None

        try:
            # Handle face claim - use attachment URL if provided
            face_claim_url = None
            if face_claim:
                face_claim_url = face_claim.url

            tribute = db.create_tribute(
                tribute_id=tribute_id,
                tribute_name=tribute_name,
                user_id=user.id,
                user_mention=user_mention,
                guild_id=guild_id,
                face_claim_url=face_claim_url,
                prompt_channel_id=prompt_channel_id,
            )

            # Auto-create empty inventory for this tribute with specified capacity
            try:
                bot.storage.create_inventory(
                    tribute_id,
                    capacity=inventory_capacity,
                    equipped_capacity=equipped_capacity,
                )
                bot.inventory.create_tribute_inventory(
                    tribute_id,
                    capacity=inventory_capacity,
                    equipped_capacity=equipped_capacity,
                )
                logger.info(
                    f"Created inventory for tribute {tribute_id} with capacity {inventory_capacity}, equipped capacity {equipped_capacity}"
                )
            except Exception as inv_err:
                # Log but don't fail - tribute still created
                logger.warning(
                    f"Could not create inventory for {tribute_id}: {inv_err}"
                )

            embed = discord.Embed(
                title="✅ Tribute Created", color=discord.Color.green()
            )
            embed.add_field(name="Tribute ID", value=tribute["tribute_id"], inline=True)
            embed.add_field(
                name="Tribute Name", value=tribute["tribute_name"], inline=True
            )
            embed.add_field(
                name="Discord User", value=tribute["user_mention"], inline=True
            )
            embed.add_field(
                name="User ID", value=f"`{tribute['user_id']}`", inline=False
            )
            if face_claim_url:
                embed.set_thumbnail(url=face_claim_url)
                embed.add_field(name="Face Claim", value="✅ Attached", inline=False)
            if tribute["created_at"]:
                embed.add_field(
                    name="Created", value=f"<t:{tribute['created_at']}>", inline=False
                )
            embed.add_field(
                name="Prompt Channel", value=f"<#{prompt_channel_id}>", inline=True
            )
            embed.add_field(
                name="Inventory Capacity",
                value=f"{inventory_capacity} slots",
                inline=True,
            )
            embed.add_field(
                name="Equipped Capacity",
                value=f"{equipped_capacity} slots",
                inline=True,
            )
            embed.add_field(
                name="Inventory", value="✅ Empty inventory created", inline=False
            )
            embed.set_footer(text=f"Created by {interaction.user.name}")

            await interaction.response.send_message(embed=embed, ephemeral=True)

            # Log the command execution
            await log_to_channel(
                interaction,
                "📋 Tribute Created",
                f"**{tribute['tribute_id']}** - {tribute['tribute_name']} ({tribute['user_mention']})\nCapacity: {inventory_capacity}",
                discord.Color.green(),
            )

        except Exception as e:
            if "UNIQUE constraint failed" in str(e):
                await interaction.response.send_message(
                    f"❌ Error: Tribute ID `{tribute_id}` already exists.",
                    ephemeral=True,
                )
            else:
                await interaction.response.send_message(
                    f"❌ Error: Failed to create tribute. {str(e)}", ephemeral=True
                )

    @bot.tree.command(
        name="view-tribute", description="View tribute details with all associated data"
    )
    @discord.app_commands.describe(
        tribute_id="Tribute ID (e.g., D1F)",
        show="What to show: files, prompt, inventory, or leave empty for all",
    )
    async def view_tribute(
        interaction: discord.Interaction, tribute_id: str, show: Optional[str] = None
    ):
        """Display complete tribute data including inventory, prompt, and files."""

        tribute_id = tribute_id.strip().upper()

        try:
            tribute_data = db.get_tribute(tribute_id)

            if not tribute_data:
                await interaction.response.send_message(
                    f"❌ Tribute not found: `{tribute_id}`", ephemeral=True
                )
                return

            # Create main embed
            embed = discord.Embed(
                title=f"👤 {tribute_data['tribute_name']}", color=discord.Color.blue()
            )

            # Tribute info
            embed.add_field(
                name="Tribute ID", value=tribute_data["tribute_id"], inline=True
            )
            embed.add_field(
                name="Discord User", value=tribute_data["user_mention"], inline=True
            )
            if tribute_data["created_at"]:
                embed.add_field(
                    name="Created",
                    value=f"<t:{tribute_data['created_at']}>",
                    inline=True,
                )

            # Show selected sections or all
            show_all = show is None or show.lower() == "all"

            # Inventory section - get from storage manager
            if show_all or (show and "inventory" in show.lower()):
                inv_data = bot.storage.get_inventory(tribute_id)
                if inv_data:
                    items = inv_data.get("items", {})
                    equipped = inv_data.get("equipped", {})
                    capacity = inv_data.get("capacity", 10)
                    equipped_capacity = inv_data.get("equipped_capacity", 5)

                    # Equipped first, then inventory
                    equipped_str = (
                        "\n".join([f"#{num}: {name}" for num, name in equipped.items()])
                        if equipped
                        else "Empty"
                    )
                    embed.add_field(
                        name=f"⚔️ Equipped ({len(equipped)}/{equipped_capacity} items)",
                        value=equipped_str,
                        inline=False,
                    )

                    items_str = (
                        "\n".join([f"#{num}: {name}" for num, name in items.items()])
                        if items
                        else "Empty"
                    )
                    embed.add_field(
                        name=f"📦 Inventory ({len(items)}/{capacity} items)",
                        value=items_str,
                        inline=False,
                    )

            # Prompt section
            if show_all or (show and "prompt" in show.lower()):
                prompt_data = bot.storage.get_prompt(tribute_id)
                if prompt_data:
                    prompt_text = prompt_data.get("message", "")
                    prompt_text = (
                        prompt_text[:1024] if len(prompt_text) > 1024 else prompt_text
                    )
                    embed.add_field(name="💬 Prompt", value=prompt_text, inline=False)

            # Files section
            if show_all or (show and "files" in show.lower()):
                files = db.get_files(tribute_id)
                if files:
                    files_str = "\n".join(
                        [
                            f"[{f['file_type']}] {f['file_path'].split('/')[-1]}"
                            for f in files
                        ]
                    )
                    embed.add_field(
                        name=f"📁 Files ({len(files)})", value=files_str, inline=False
                    )

            # Set face claim as thumbnail if available
            if tribute_data.get("face_claim_url"):
                embed.set_thumbnail(url=tribute_data["face_claim_url"])

            await interaction.response.send_message(embed=embed, ephemeral=True)

        except Exception as e:
            await interaction.response.send_message(
                f"❌ Error: {str(e)}", ephemeral=True
            )

    @bot.tree.command(name="edit-tribute", description="Edit tribute information")
    @discord.app_commands.describe(
        tribute_id="Tribute ID to edit (e.g., D1F)",
        new_tribute_id="(Optional) New tribute ID",
        tribute_name="(Optional) New tribute name",
        user="(Optional) New Discord user to link",
        prompt_channel="(Optional) New channel for prompts (must be in category)",
        face_claim="(Optional) New face claim image",
        inventory_capacity="(Optional) New inventory capacity",
        equipped_capacity="(Optional) New equipped section capacity",
    )
    @discord.app_commands.autocomplete(prompt_channel=get_category_channels)
    async def edit_tribute(
        interaction: discord.Interaction,
        tribute_id: str,
        new_tribute_id: Optional[str] = None,
        tribute_name: Optional[str] = None,
        user: Optional[discord.User] = None,
        prompt_channel: Optional[str] = None,
        face_claim: Optional[discord.Attachment] = None,
        inventory_capacity: Optional[int] = None,
        equipped_capacity: Optional[int] = None,
    ):
        """Edit tribute information including name, user mention, channel, image, capacity, or ID."""

        # Check Gamemaker role
        if not any(role.name == "Gamemaker" for role in interaction.user.roles):
            await interaction.response.send_message(
                "❌ Permission Denied: You must have the Gamemaker role.",
                ephemeral=True,
            )
            return

        tribute_id = tribute_id.strip().upper()

        try:
            # Get current tribute
            tribute = db.get_tribute(tribute_id)
            if not tribute:
                await interaction.response.send_message(
                    f"❌ Tribute not found: `{tribute_id}`", ephemeral=True
                )
                return

            # Prepare updates
            updates = {}

            # Update name if provided
            if tribute_name:
                updates["tribute_name"] = tribute_name.strip()

            # Update user mention if provided
            if user:
                updates["user_mention"] = f"<@{user.id}>"

            # Update prompt channel if provided
            if prompt_channel:
                try:
                    prompt_channel_id = int(prompt_channel)
                    channel = interaction.guild.get_channel(prompt_channel_id)

                    if not channel:
                        await interaction.response.send_message(
                            "❌ Channel not found.", ephemeral=True
                        )
                        return

                    if not isinstance(channel, discord.TextChannel):
                        await interaction.response.send_message(
                            "❌ Prompt channel must be a text channel.", ephemeral=True
                        )
                        return

                    # Validate channel is in configured category
                    guild_id = str(interaction.guild.id)
                    if guild_id in bot.config and bot.config[guild_id].get(
                        "category_id"
                    ):
                        category = interaction.guild.get_channel(
                            bot.config[guild_id]["category_id"]
                        )
                        if category and channel.category_id != category.id:
                            await interaction.response.send_message(
                                f"❌ Prompt channel must be in the configured category.",
                                ephemeral=True,
                            )
                            return

                    updates["prompt_channel_id"] = prompt_channel_id
                except (ValueError, AttributeError):
                    await interaction.response.send_message(
                        "❌ Invalid channel specified.", ephemeral=True
                    )
                    return

            # Update face claim if provided
            if face_claim:
                updates["face_claim_url"] = face_claim.url

            # Update inventory capacity if provided
            capacity_changed = False
            new_inv_capacity = inventory_capacity
            new_eq_capacity = equipped_capacity
            if inventory_capacity is not None or equipped_capacity is not None:
                capacity_changed = True
                old_inv = bot.storage.get_inventory(tribute_id)
                if old_inv:
                    if inventory_capacity is None:
                        new_inv_capacity = old_inv.get("capacity", 10)
                    if equipped_capacity is None:
                        new_eq_capacity = old_inv.get("equipped_capacity", 5)

            # Handle tribute ID change
            if new_tribute_id:
                new_tribute_id = new_tribute_id.strip().upper()

                # Validate new ID format
                if len(new_tribute_id) > 5 or not new_tribute_id[1].isdigit():
                    await interaction.response.send_message(
                        f"❌ Invalid tribute ID format: `{new_tribute_id}`. Format should be like D1F, D1M, etc.",
                        ephemeral=True,
                    )
                    return

                # Check if new ID already exists
                if new_tribute_id != tribute_id:
                    existing = db.get_tribute(new_tribute_id)
                    if existing:
                        await interaction.response.send_message(
                            f"❌ Tribute ID `{new_tribute_id}` already exists.",
                            ephemeral=True,
                        )
                        return

                    # Create new tribute record with new ID, copy data
                    try:
                        # Copy inventory with updated capacity if changed
                        old_inv = bot.storage.get_inventory(tribute_id)
                        if old_inv:
                            final_inv_capacity = (
                                new_inv_capacity
                                if new_inv_capacity
                                else old_inv.get("capacity", 10)
                            )
                            final_eq_capacity = (
                                new_eq_capacity
                                if new_eq_capacity
                                else old_inv.get("equipped_capacity", 5)
                            )
                            bot.storage.create_inventory(
                                new_tribute_id,
                                capacity=final_inv_capacity,
                                equipped_capacity=final_eq_capacity,
                            )
                            bot.inventory.create_tribute_inventory(
                                new_tribute_id,
                                capacity=final_inv_capacity,
                                equipped_capacity=final_eq_capacity,
                            )
                            if old_inv.get("items"):
                                for item_num, item_name in old_inv["items"].items():
                                    bot.storage.add_inventory_item(
                                        new_tribute_id, item_name
                                    )
                                    bot.inventory.add_to_inventory(
                                        new_tribute_id, item_name
                                    )

                        # Create new tribute with updated fields
                        new_tribute = db.create_tribute(
                            tribute_id=new_tribute_id,
                            tribute_name=updates.get(
                                "tribute_name", tribute["tribute_name"]
                            ),
                            user_id=tribute["user_id"],
                            user_mention=updates.get(
                                "user_mention", tribute["user_mention"]
                            ),
                            guild_id=tribute["guild_id"],
                            face_claim_url=updates.get(
                                "face_claim_url", tribute.get("face_claim_url")
                            ),
                            prompt_channel_id=updates.get(
                                "prompt_channel_id", tribute.get("prompt_channel_id")
                            ),
                        )

                        # Delete old tribute
                        db.delete_tribute(tribute_id)
                        bot.storage.delete_inventory(tribute_id)
                        bot.inventory.delete_tribute_inventory(tribute_id)

                        tribute = new_tribute
                    except Exception as e:
                        await interaction.response.send_message(
                            f"❌ Error changing tribute ID: {str(e)}", ephemeral=True
                        )
                        return
                else:
                    # Same ID, just apply other updates
                    tribute = db.update_tribute(tribute_id, **updates)
            else:
                # No ID change, just apply updates
                if updates:
                    tribute = db.update_tribute(tribute_id, **updates)

            # Update inventory capacity if changed
            if capacity_changed:
                old_inv = bot.storage.get_inventory(tribute_id)
                if old_inv:
                    bot.storage.create_inventory(
                        tribute_id,
                        capacity=new_inv_capacity,
                        equipped_capacity=new_eq_capacity,
                    )
                    bot.inventory.create_tribute_inventory(
                        tribute_id,
                        capacity=new_inv_capacity,
                        equipped_capacity=new_eq_capacity,
                    )

            # Build response embed
            embed = discord.Embed(
                title="✅ Tribute Updated", color=discord.Color.blue()
            )
            embed.add_field(name="Tribute ID", value=tribute["tribute_id"], inline=True)
            embed.add_field(
                name="Tribute Name", value=tribute["tribute_name"], inline=True
            )
            embed.add_field(
                name="Discord User", value=tribute["user_mention"], inline=True
            )

            if tribute.get("face_claim_url"):
                embed.set_thumbnail(url=tribute["face_claim_url"])
                embed.add_field(name="Face Claim", value="✅ Updated", inline=False)

            if tribute.get("prompt_channel_id"):
                embed.add_field(
                    name="Prompt Channel",
                    value=f"<#{tribute['prompt_channel_id']}>",
                    inline=True,
                )

            if capacity_changed:
                embed.add_field(
                    name="Inventory Capacity",
                    value=f"{new_inv_capacity} slots",
                    inline=True,
                )
                embed.add_field(
                    name="Equipped Capacity",
                    value=f"{new_eq_capacity} slots",
                    inline=True,
                )

            embed.set_footer(text=f"Edited by {interaction.user.name}")

            await interaction.response.send_message(embed=embed, ephemeral=True)

            # Log the command execution
            await log_to_channel(
                interaction,
                "📝 Tribute Edited",
                f"**{tribute['tribute_id']}** - {tribute['tribute_name']}\nTribute information updated.",
                discord.Color.blue(),
            )

        except Exception as e:
            await interaction.response.send_message(
                f"❌ Error: {str(e)}", ephemeral=True
            )

    @bot.tree.command(name="view-tributes", description="View all tributes")
    async def view_tributes(interaction: discord.Interaction):
        """Display all tributes in the server."""

        try:
            guild_id = interaction.guild.id if interaction.guild else None
            tributes = db.get_all_tributes(guild_id=guild_id)

            if not tributes:
                await interaction.response.send_message(
                    "No tributes found.", ephemeral=True
                )
                return

            embed = discord.Embed(
                title="📋 All Tributes",
                color=discord.Color.blue(),
                description=f"Total: {len(tributes)} tribute(s)",
            )

            for tribute in tributes:
                created_str = (
                    f"<t:{tribute['created_at']}>"
                    if tribute["created_at"]
                    else "Unknown"
                )
                value = f"{tribute['user_mention']}\nCreated: {created_str}"
                embed.add_field(
                    name=f"{tribute['tribute_id']} - {tribute['tribute_name']}",
                    value=value,
                    inline=False,
                )

            await interaction.response.send_message(embed=embed, ephemeral=True)

        except Exception as e:
            await interaction.response.send_message(
                f"❌ Error: {str(e)}", ephemeral=True
            )

    @bot.tree.command(
        name="delete-tribute", description="Delete a tribute and all associated data"
    )
    @discord.app_commands.describe(tribute_id="Tribute ID to delete (e.g., D1F)")
    async def delete_tribute(interaction: discord.Interaction, tribute_id: str):
        """Delete a tribute and cascade-delete all related data."""

        # Check Gamemaker role
        if not any(role.name == "Gamemaker" for role in interaction.user.roles):
            await interaction.response.send_message(
                "❌ Permission Denied: You must have the Gamemaker role.",
                ephemeral=True,
            )
            return

        tribute_id = tribute_id.strip().upper()

        try:
            tribute = db.get_tribute(tribute_id)

            if not tribute:
                await interaction.response.send_message(
                    f"❌ Tribute not found: `{tribute_id}`", ephemeral=True
                )
                return

            # Show confirmation dialog
            embed = discord.Embed(
                title="⚠️ Confirm Tribute Deletion",
                description=f"Are you sure you want to delete **{tribute['tribute_id']}** ({tribute['tribute_name']})?\n\n"
                f"This will permanently delete:\n"
                f"• Tribute record\n"
                f"• All inventory items\n"
                f"• Associated prompts\n"
                f"• All attached files",
                color=discord.Color.orange(),
            )
            embed.set_footer(text="This action cannot be undone!")

            view = ConfirmationView()
            await interaction.response.send_message(
                embed=embed, view=view, ephemeral=True
            )

            # Wait for confirmation
            await view.wait()

            if not view.confirmed:
                return  # User cancelled

            # Delete the tribute (cascades to inventory, prompts, files)
            db.delete_tribute(tribute_id)

            # Also delete from both storage layers
            try:
                bot.storage.delete_inventory(tribute_id)
                bot.inventory.delete_tribute_inventory(tribute_id)
            except:
                pass  # Storage cleanup non-critical

            embed = discord.Embed(title="✅ Tribute Deleted", color=discord.Color.red())
            embed.add_field(
                name="Deleted Tribute",
                value=f"{tribute['tribute_id']} - {tribute['tribute_name']}",
            )
            embed.description = (
                "⚠️ All associated data (inventory, prompts, files) has been deleted."
            )
            embed.set_footer(text=f"Deleted by {interaction.user.name}")

            await interaction.followup.send(embed=embed, ephemeral=True)

            # Log the command execution
            await log_to_channel(
                interaction,
                "🗑️ Tribute Deleted",
                f"**{tribute['tribute_id']}** - {tribute['tribute_name']}\nAll associated data removed.",
                discord.Color.red(),
            )

        except Exception as e:
            await interaction.followup.send(f"❌ Error: {str(e)}", ephemeral=True)

    @bot.tree.command(name="save-prompt", description="Save a prompt to a tribute")
    @discord.app_commands.describe(
        tribute_id="Tribute ID to attach the prompt to",
        file1="(Optional) First file attachment",
        file2="(Optional) Second file attachment",
        file3="(Optional) Third file attachment",
    )
    async def save_prompt(
        interaction: discord.Interaction,
        tribute_id: str,
        file1: Optional[discord.Attachment] = None,
        file2: Optional[discord.Attachment] = None,
        file3: Optional[discord.Attachment] = None,
    ):
        """Save a prompt message to a specific tribute using a modal."""

        # Check Gamemaker role
        if not any(role.name == "Gamemaker" for role in interaction.user.roles):
            await interaction.response.send_message(
                "❌ Permission Denied: You must have the Gamemaker role.",
                ephemeral=True,
            )
            return

        tribute_id = tribute_id.strip().upper()

        try:
            # Check if tribute exists
            tribute = db.get_tribute(tribute_id)
            if not tribute:
                await interaction.response.send_message(
                    f"❌ Tribute not found: `{tribute_id}`", ephemeral=True
                )
                return

            # Store files for use in modal
            files = [f for f in [file1, file2, file3] if f is not None]

            # Show modal for prompt message
            class PromptMessageModal(discord.ui.Modal, title="Prompt Message"):
                message = discord.ui.TextInput(
                    label="Prompt Message",
                    placeholder="Enter the prompt message for this tribute",
                    style=discord.TextStyle.long,
                    min_length=1,
                    max_length=4000,
                )

                async def on_submit(
                    self, modal_interaction: discord.Interaction
                ) -> None:
                    try:
                        # Use the tribute's assigned prompt channel
                        channel_id = tribute.get("prompt_channel_id")

                        # Create prompt in database
                        prompt = db.create_prompt(
                            tribute_id, str(self.message), channel_id
                        )

                        # Save files if provided
                        if files:
                            guild_id = str(interaction.guild.id)
                            file_dir = os.path.join(bot.prompt_image_dir, guild_id)
                            os.makedirs(file_dir, exist_ok=True)

                            for file_attachment in files:
                                # Validate file type
                                valid_extensions = (
                                    ".png",
                                    ".jpg",
                                    ".jpeg",
                                    ".webp",
                                    ".webm",
                                    ".mp3",
                                )
                                if not any(
                                    file_attachment.filename.endswith(ext)
                                    for ext in valid_extensions
                                ):
                                    continue

                                file_extension = os.path.splitext(
                                    file_attachment.filename
                                )[1]
                                new_filename = (
                                    f"{tribute_id}_{int(time.time())}{file_extension}"
                                )
                                file_path = os.path.join(file_dir, new_filename)
                                await file_attachment.save(file_path)

                        # Confirmation embed
                        embed = discord.Embed(
                            title="✅ Prompt Saved", color=discord.Color.green()
                        )
                        embed.add_field(
                            name="Tribute",
                            value=f"{tribute['tribute_id']} - {tribute['tribute_name']}",
                            inline=False,
                        )
                        embed.add_field(
                            name="Message",
                            value=f"```\n{str(self.message)[:200]}\n```",
                            inline=False,
                        )
                        if channel_id:
                            embed.add_field(
                                name="Will be sent to",
                                value=f"<#{channel_id}>",
                                inline=False,
                            )
                        if files:
                            embed.add_field(
                                name="Files",
                                value=f"{len(files)} file(s) attached",
                                inline=False,
                            )
                        embed.set_footer(text=f"Saved by {modal_interaction.user.name}")

                        await modal_interaction.response.send_message(
                            embed=embed, ephemeral=True
                        )

                        # Log the command execution
                        await log_to_channel(
                            modal_interaction,
                            "💬 Prompt Saved",
                            f"**{tribute['tribute_id']}** - {tribute['tribute_name']}\nMessage saved and ready to send.",
                            discord.Color.blue(),
                        )
                    except Exception as e:
                        await modal_interaction.response.send_message(
                            f"❌ Error saving prompt: {str(e)}", ephemeral=True
                        )

            # Show the modal
            await interaction.response.send_modal(PromptMessageModal())

        except Exception as e:
            await interaction.response.send_message(
                f"❌ Error: {str(e)}", ephemeral=True
            )
