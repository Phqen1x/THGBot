"""
Tribute management commands for THGBot with unified data view.
Allows Gamemakers to create, view, and manage tribute records with all associated data.
"""

import discord
from database import SQLDatabase
from typing import Optional
import time

def register_tribute_commands(bot, db: SQLDatabase):
    """Register all tribute commands with the bot."""
    
    @bot.tree.command(name="create-tribute", description="Create a new tribute")
    @discord.app_commands.describe(
        tribute_id="Tribute ID (e.g., D1F, D1M)",
        tribute_name="Tribute name (e.g., John Doe)",
        user="Discord user to link to this tribute",
        face_claim="(Optional) Image URL for character face claim (e.g., https://example.com/image.jpg)"
    )
    async def create_tribute(
        interaction: discord.Interaction,
        tribute_id: str,
        tribute_name: str,
        user: discord.User,
        face_claim: Optional[str] = None
    ):
        """Create a new tribute with ID, name, Discord user link, and optional face claim."""
        
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
            # Handle face claim URL
            face_claim_url = None
            if face_claim:
                face_claim_url = face_claim if face_claim.startswith("http") else None
            
            tribute = db.create_tribute(
                tribute_id=tribute_id,
                tribute_name=tribute_name,
                user_id=user.id,
                user_mention=user_mention,
                guild_id=guild_id,
                face_claim_url=face_claim_url
            )
            
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
            embed.set_footer(text=f"Created by {interaction.user.name}")
            
            await interaction.response.send_message(embed=embed, ephemeral=True)
            
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
            tribute_data = db.get_tribute_full(tribute_id)
            
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
            
            # Inventory section
            if show_all or (show and "inventory" in show.lower()):
                if tribute_data.get('inventory'):
                    inv = tribute_data['inventory']
                    items_str = "\n".join([f"#{num}: {name}" for num, name in inv['items'].items()]) if inv['items'] else "Empty"
                    embed.add_field(
                        name=f"📦 Inventory (Capacity: {inv['capacity']})",
                        value=items_str,
                        inline=False
                    )
            
            # Prompt section
            if show_all or (show and "prompt" in show.lower()):
                if tribute_data.get('prompt'):
                    prompt = tribute_data['prompt']
                    prompt_text = prompt['message'][:1024] if len(prompt['message']) > 1024 else prompt['message']
                    embed.add_field(
                        name="💬 Prompt",
                        value=prompt_text,
                        inline=False
                    )
                    if prompt.get('created_at'):
                        embed.add_field(name="Prompt Created", value=f"<t:{prompt['created_at']}>", inline=False)
            
            # Files section
            if show_all or (show and "files" in show.lower()):
                if tribute_data.get('files'):
                    files_str = "\n".join([f"[{f['file_type']}] {f['file_path'].split('/')[-1]}" for f in tribute_data['files']])
                    embed.add_field(
                        name=f"📁 Files ({len(tribute_data['files'])})",
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
            
            embed = discord.Embed(
                title="✅ Tribute Deleted",
                color=discord.Color.red()
            )
            embed.add_field(name="Deleted Tribute", value=f"{tribute['tribute_id']} - {tribute['tribute_name']}")
            embed.description = "⚠️ All associated data (inventory, prompts, files) has been deleted."
            embed.set_footer(text=f"Deleted by {interaction.user.name}")
            
            await interaction.response.send_message(embed=embed, ephemeral=True)
            
        except Exception as e:
            await interaction.response.send_message(
                f"❌ Error: {str(e)}",
                ephemeral=True
            )
