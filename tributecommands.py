"""
Tribute management commands for THGBot.
Allows Gamemakers to create and manage tribute records.
"""

import discord
from database import SQLDatabase

def register_tribute_commands(bot, db: SQLDatabase):
    """Register all tribute commands with the bot."""
    
    @bot.tree.command(name="create-tribute", description="Create a new tribute")
    @discord.app_commands.describe(
        tribute_id="Tribute ID (e.g., D1F, D1M)",
        tribute_name="Tribute name (e.g., John Doe)",
        user="Discord user to link to this tribute"
    )
    async def create_tribute(
        interaction: discord.Interaction,
        tribute_id: str,
        tribute_name: str,
        user: discord.User
    ):
        """Create a new tribute with ID, name, and Discord user link."""
        
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
            tribute = db.create_tribute(
                tribute_id=tribute_id,
                tribute_name=tribute_name,
                user_id=user.id,
                user_mention=user_mention,
                guild_id=guild_id
            )
            
            embed = discord.Embed(
                title="✅ Tribute Created",
                color=discord.Color.green()
            )
            embed.add_field(name="Tribute ID", value=tribute['tribute_id'], inline=True)
            embed.add_field(name="Tribute Name", value=tribute['tribute_name'], inline=True)
            embed.add_field(name="Discord User", value=tribute['user_mention'], inline=True)
            embed.add_field(name="User ID", value=f"`{tribute['user_id']}`", inline=False)
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
                value = f"{tribute['user_mention']} (ID: {tribute['user_id']})"
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
    
    @bot.tree.command(name="view-tribute", description="View details of a specific tribute")
    @discord.app_commands.describe(tribute_id="Tribute ID (e.g., D1F)")
    async def view_tribute(interaction: discord.Interaction, tribute_id: str):
        """Display details of a specific tribute."""
        
        tribute_id = tribute_id.strip().upper()
        
        try:
            tribute = db.get_tribute(tribute_id)
            
            if not tribute:
                await interaction.response.send_message(
                    f"❌ Tribute not found: `{tribute_id}`",
                    ephemeral=True
                )
                return
            
            embed = discord.Embed(
                title=f"👤 {tribute['tribute_name']}",
                color=discord.Color.blue()
            )
            embed.add_field(name="Tribute ID", value=tribute['tribute_id'], inline=True)
            embed.add_field(name="Discord User", value=tribute['user_mention'], inline=True)
            embed.add_field(name="User ID", value=f"`{tribute['user_id']}`", inline=False)
            embed.add_field(name="Created", value=tribute['created_at'], inline=False)
            
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
