"""
Tribute management commands for THGBot with unified data view.
Allows Gamemakers to create, view, and manage tribute records with all associated data.
"""

import discord
from database import SQLDatabase
from inventory import Inventory
from typing import Optional
import time
import os
import logging
import datetime

logger = logging.getLogger(__name__)

def register_tribute_commands(bot, db: SQLDatabase):
    """Register all tribute commands with the bot."""
    
    async def log_to_channel(interaction: discord.Interaction, title: str, description: str, color=None):
        """Helper function to send logs to the configured log channel."""
        try:
            guild_id = str(interaction.guild.id)
            if guild_id not in bot.config or not bot.config[guild_id].get("log_channel_id"):
                return
            
            log_channel = bot.get_channel(bot.config[guild_id]["log_channel_id"])
            if not log_channel:
                return
            
            log_embed = discord.Embed(
                title=title,
                description=description,
                color=color or discord.Color.blue()
            )
            log_embed.set_author(
                name=f"{interaction.user.name}",
                icon_url=f"{interaction.user.avatar}"
            )
            if interaction.guild.icon:
                log_embed.set_thumbnail(url=interaction.guild.icon.url)
            log_embed.timestamp = datetime.datetime.now()
            await log_channel.send(embed=log_embed)
        except Exception as e:
            logger.error(f"Failed to log to channel: {e}")
    
    @bot.tree.command(name="create-tribute", description="Create a new tribute")
    @discord.app_commands.describe(
        tribute_id="Tribute ID (e.g., D1F, D1M)",
        tribute_name="Tribute name (e.g., John Doe)",
        user="Discord user to link to this tribute",
        prompt_channel="Channel where prompts will be sent",
        inventory_capacity="Number of inventory slots (default: 10)",
        face_claim="(Optional) Image file or URL for character face claim"
    )
    async def create_tribute(
        interaction: discord.Interaction,
        tribute_id: str,
        tribute_name: str,
        user: discord.User,
        prompt_channel: discord.TextChannel,
        inventory_capacity: int = 10,
        face_claim: Optional[discord.Attachment] = None
    ):
        """Create a new tribute with ID, name, Discord user link, channel, and optional face claim."""
        
        # Check Gamemaker role
        if not any(role.name == "Gamemaker" for role in interaction.user.roles):
            await interaction.response.send_message(
                "❌ Permission Denied: You must have the Gamemaker role.",
                ephemeral=True
            )
            return
        
        # Validate tribute_id format
        tribute_id = tribute_id.strip().upper()
        if len(tribute_id) > 5 or not tribute_id[1].isdigit():
            await interaction.response.send_message(
                f"❌ Invalid tribute ID format: `{tribute_id}`. Format should be like D1F, D1M, etc.",
                ephemeral=True
            )
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
                prompt_channel_id=prompt_channel.id
            )
            
            # Auto-create empty inventory for this tribute with specified capacity
            try:
                bot.storage.create_inventory(tribute_id, capacity=inventory_capacity)
                logger.info(f"Created inventory for tribute {tribute_id} with capacity {inventory_capacity}")
            except Exception as inv_err:
                # Log but don't fail - tribute still created
                logger.warning(f"Could not create inventory for {tribute_id}: {inv_err}")
            
            embed = discord.Embed(
                title="✅ Tribute Created",
                color=discord.Color.green()
            )
            embed.add_field(name="Tribute ID", value=tribute['tribute_id'], inline=True)
            embed.add_field(name="Tribute Name", value=tribute['tribute_name'], inline=True)
            embed.add_field(name="Discord User", value=tribute['user_mention'], inline=True)
            embed.add_field(name="User ID", value=f"`{tribute['user_id']}`", inline=False)
            if face_claim_url:
                embed.set_thumbnail(url=face_claim_url)
                embed.add_field(name="Face Claim", value="✅ Attached", inline=False)
            if tribute['created_at']:
                embed.add_field(name="Created", value=f"<t:{tribute['created_at']}>", inline=False)
            embed.add_field(name="Prompt Channel", value=f"<#{prompt_channel.id}>", inline=True)
            embed.add_field(name="Inventory Capacity", value=f"{inventory_capacity} slots", inline=True)
            embed.add_field(name="Inventory", value="✅ Empty inventory created", inline=False)
            embed.set_footer(text=f"Created by {interaction.user.name}")
            
            await interaction.response.send_message(embed=embed, ephemeral=True)
            
            # Log the command execution
            await log_to_channel(
                interaction,
                "📋 Tribute Created",
                f"**{tribute['tribute_id']}** - {tribute['tribute_name']} ({tribute['user_mention']})\nCapacity: {inventory_capacity}",
                discord.Color.green()
            )
            
        except Exception as e:
            if "UNIQUE constraint failed" in str(e):
                await interaction.response.send_message(
                    f"❌ Error: Tribute ID `{tribute_id}` already exists.",
                    ephemeral=True
                )
            else:
                await interaction.response.send_message(
                    f"❌ Error: Failed to create tribute. {str(e)}",
                    ephemeral=True
                )
    
    @bot.tree.command(name="view-tribute", description="View tribute details with all associated data")
    @discord.app_commands.describe(
        tribute_id="Tribute ID (e.g., D1F)",
        show="What to show: files, prompt, inventory, or leave empty for all"
    )
    async def view_tribute(
        interaction: discord.Interaction,
        tribute_id: str,
        show: Optional[str] = None
    ):
        """Display complete tribute data including inventory, prompt, and files."""
        
        tribute_id = tribute_id.strip().upper()
        
        try:
            tribute_data = db.get_tribute(tribute_id)
            
            if not tribute_data:
                await interaction.response.send_message(
                    f"❌ Tribute not found: `{tribute_id}`",
                    ephemeral=True
                )
                return
            
            # Create main embed
            embed = discord.Embed(
                title=f"👤 {tribute_data['tribute_name']}",
                color=discord.Color.blue()
            )
            
            # Tribute info
            embed.add_field(name="Tribute ID", value=tribute_data['tribute_id'], inline=True)
            embed.add_field(name="Discord User", value=tribute_data['user_mention'], inline=True)
            if tribute_data['created_at']:
                embed.add_field(name="Created", value=f"<t:{tribute_data['created_at']}>", inline=True)
            
            # Show selected sections or all
            show_all = show is None or show.lower() == "all"
            
            # Inventory section - get from storage manager
            if show_all or (show and "inventory" in show.lower()):
                inv_data = bot.storage.get_inventory(tribute_id)
                if inv_data:
                    items = inv_data.get('items', {})
                    capacity = inv_data.get('capacity', 10)
                    items_str = "\n".join([f"#{num}: {name}" for num, name in items.items()]) if items else "Empty"
                    embed.add_field(
                        name=f"📦 Inventory ({len(items)}/{capacity} items)",
                        value=items_str,
                        inline=False
                    )
            
            # Prompt section
            if show_all or (show and "prompt" in show.lower()):
                prompt_data = bot.storage.get_prompt(tribute_id)
                if prompt_data:
                    prompt_text = prompt_data.get('message', '')
                    prompt_text = prompt_text[:1024] if len(prompt_text) > 1024 else prompt_text
                    embed.add_field(
                        name="💬 Prompt",
                        value=prompt_text,
                        inline=False
                    )
            
            # Files section  
            if show_all or (show and "files" in show.lower()):
                files = db.get_files(tribute_id)
                if files:
                    files_str = "\n".join([f"[{f['file_type']}] {f['file_path'].split('/')[-1]}" for f in files])
                    embed.add_field(
                        name=f"📁 Files ({len(files)})",
                        value=files_str,
                        inline=False
                    )
            
            # Set face claim as thumbnail if available
            if tribute_data.get('face_claim_url'):
                embed.set_thumbnail(url=tribute_data['face_claim_url'])
            
            await interaction.response.send_message(embed=embed, ephemeral=True)
            
        except Exception as e:
            await interaction.response.send_message(
                f"❌ Error: {str(e)}",
                ephemeral=True
            )
    
    @bot.tree.command(name="view-tributes", description="View all tributes")
    async def view_tributes(interaction: discord.Interaction):
        """Display all tributes in the server."""
        
        try:
            guild_id = interaction.guild.id if interaction.guild else None
            tributes = db.get_all_tributes(guild_id=guild_id)
            
            if not tributes:
                await interaction.response.send_message(
                    "No tributes found.",
                    ephemeral=True
                )
                return
            
            embed = discord.Embed(
                title="📋 All Tributes",
                color=discord.Color.blue(),
                description=f"Total: {len(tributes)} tribute(s)"
            )
            
            for tribute in tributes:
                created_str = f"<t:{tribute['created_at']}>" if tribute['created_at'] else "Unknown"
                value = f"{tribute['user_mention']}\nCreated: {created_str}"
                embed.add_field(
                    name=f"{tribute['tribute_id']} - {tribute['tribute_name']}",
                    value=value,
                    inline=False
                )
            
            await interaction.response.send_message(embed=embed, ephemeral=True)
            
        except Exception as e:
            await interaction.response.send_message(
                f"❌ Error: {str(e)}",
                ephemeral=True
            )
    
    @bot.tree.command(name="delete-tribute", description="Delete a tribute and all associated data")
    @discord.app_commands.describe(tribute_id="Tribute ID to delete (e.g., D1F)")
    async def delete_tribute(interaction: discord.Interaction, tribute_id: str):
        """Delete a tribute and cascade-delete all related data."""
        
        # Check Gamemaker role
        if not any(role.name == "Gamemaker" for role in interaction.user.roles):
            await interaction.response.send_message(
                "❌ Permission Denied: You must have the Gamemaker role.",
                ephemeral=True
            )
            return
        
        tribute_id = tribute_id.strip().upper()
        
        try:
            tribute = db.get_tribute(tribute_id)
            
            if not tribute:
                await interaction.response.send_message(
                    f"❌ Tribute not found: `{tribute_id}`",
                    ephemeral=True
                )
                return
            
            # Delete the tribute (cascades to inventory, prompts, files)
            db.delete_tribute(tribute_id)
            
            # Also delete from storage/JSON inventory
            try:
                bot.storage.clear_inventory(tribute_id)
            except:
                pass  # Storage cleanup non-critical
            
            embed = discord.Embed(
                title="✅ Tribute Deleted",
                color=discord.Color.red()
            )
            embed.add_field(name="Deleted Tribute", value=f"{tribute['tribute_id']} - {tribute['tribute_name']}")
            embed.description = "⚠️ All associated data (inventory, prompts, files) has been deleted."
            embed.set_footer(text=f"Deleted by {interaction.user.name}")
             
            await interaction.response.send_message(embed=embed, ephemeral=True)
            
            # Log the command execution
            await log_to_channel(
                interaction,
                "🗑️ Tribute Deleted",
                f"**{tribute['tribute_id']}** - {tribute['tribute_name']}\nAll associated data removed.",
                discord.Color.red()
            )
             
        except Exception as e:
            await interaction.response.send_message(
                f"❌ Error: {str(e)}",
                ephemeral=True
            )
    
    @bot.tree.command(name="save-prompt", description="Save a prompt to a tribute")
    @discord.app_commands.describe(
        tribute_id="Tribute ID to attach the prompt to"
    )
    async def save_prompt(
        interaction: discord.Interaction,
        tribute_id: str
    ):
        """Save a prompt message to a specific tribute using a modal."""
        
        # Check Gamemaker role
        if not any(role.name == "Gamemaker" for role in interaction.user.roles):
            await interaction.response.send_message(
                "❌ Permission Denied: You must have the Gamemaker role.",
                ephemeral=True
            )
            return
        
        tribute_id = tribute_id.strip().upper()
        
        try:
            # Check if tribute exists
            tribute = db.get_tribute(tribute_id)
            if not tribute:
                await interaction.response.send_message(
                    f"❌ Tribute not found: `{tribute_id}`",
                    ephemeral=True
                )
                return
            
            # Show modal for prompt message
            class PromptMessageModal(discord.ui.Modal, title="Prompt Message"):
                message = discord.ui.TextInput(
                    label="Prompt Message",
                    placeholder="Enter the prompt message for this tribute",
                    style=discord.TextStyle.long,
                    min_length=1,
                    max_length=2000
                )
                
                async def on_submit(self, modal_interaction: discord.Interaction) -> None:
                    try:
                        # Use the tribute's assigned prompt channel
                        channel_id = tribute.get('prompt_channel_id')
                        
                        # Create prompt in database
                        prompt = db.create_prompt(tribute_id, str(self.message), channel_id)
                        
                        # Confirmation embed
                        embed = discord.Embed(
                            title="✅ Prompt Saved",
                            color=discord.Color.green()
                        )
                        embed.add_field(name="Tribute", value=f"{tribute['tribute_id']} - {tribute['tribute_name']}", inline=False)
                        embed.add_field(name="Message", value=f"```\n{str(self.message)[:200]}\n```", inline=False)
                        if channel_id:
                            embed.add_field(name="Will be sent to", value=f"<#{channel_id}>", inline=False)
                        embed.set_footer(text=f"Saved by {modal_interaction.user.name}")
                        
                        await modal_interaction.response.send_message(embed=embed, ephemeral=True)
                        
                        # Log the command execution
                        await log_to_channel(
                            modal_interaction,
                            "💬 Prompt Saved",
                            f"**{tribute['tribute_id']}** - {tribute['tribute_name']}\nMessage saved and ready to send.",
                            discord.Color.blue()
                        )
                    except Exception as e:
                        await modal_interaction.response.send_message(
                            f"❌ Error saving prompt: {str(e)}",
                            ephemeral=True
                        )
            
            # Show the modal
            await interaction.response.send_modal(PromptMessageModal())
            
        except Exception as e:
            await interaction.response.send_message(
                f"❌ Error: {str(e)}",
                ephemeral=True
            )
