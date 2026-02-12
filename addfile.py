import discord
from discord import app_commands
import os
from typing import Optional


# Assuming this is in your main bot file or cog
class PromptCommands(app_commands.Group):
    def __init__(self, bot):
        super().__init__(name="prompt", description="Prompt management commands")
        self.bot = bot
        try:
            self.datadir = os.environ["SNAP_DATA"]
        except:
            print("SNAP_DATA must be set")
        self.prompt_image_dir = os.path.join(self.datadir, "prompt_images")

    @app_commands.command(
        name="add_file", description="Add a file to an existing prompt"
    )
    @app_commands.describe(
        prompt_id="The ID of the prompt to add a file to",
        file="The image file to add (.png or .jpg)",
    )
    async def add_file(
        self, interaction: discord.Interaction, prompt_id: str, file: discord.Attachment
    ):
        """Add a file to an existing prompt without overwriting"""

        await interaction.response.defer(ephemeral=True)

        guild_id = str(interaction.guild.id)
        prompt_id = prompt_id.upper().strip()

        # Check if prompt exists
        if prompt_id not in self.bot.prompt_info:
            await interaction.followup.send(
                f"Prompt ID `{prompt_id}` not found. Please create the prompt first.",
                ephemeral=True,
            )
            return

        # Validate file type
        if not (
            file.filename.endswith(".png")
            or file.filename.endswith(".jpg")
            or file.filename.endswith(".jpeg")
            or file.filename.endswith(".webm")
            or file.filename.endswith(".webp")
            or file.filename.endswith(".mp3")
        ):
            await interaction.followup.send(
                "Please upload a .png, .jpg, .jpeg, .webm, .webp, or .mp3 file.",
                ephemeral=True,
            )
            return

        # Prepare file directory
        file_dir = os.path.join(self.prompt_image_dir, guild_id)
        os.makedirs(file_dir, exist_ok=True)

        # Handle multiple files by using a list or numbering system
        if "image" in self.bot.prompt_info[prompt_id]:
            # If there's already an image, convert to list format
            existing_image = self.bot.prompt_info[prompt_id]["image"]

            # Check if it's already a list
            if isinstance(existing_image, list):
                images = existing_image
            else:
                # Convert single image to list
                images = [existing_image]

            # Generate unique filename
            file_extension = os.path.splitext(file.filename)[1]
            file_number = len(images) + 1
            new_filename = f"{prompt_id}_{file_number}{file_extension}"
            file_path = os.path.join(file_dir, new_filename)

            # Save the file
            await file.save(file_path)

            # Add to list
            images.append(new_filename)
            self.bot.prompt_info[prompt_id]["image"] = images
        else:
            # First image for this prompt
            file_extension = os.path.splitext(file.filename)[1]
            new_filename = f"{prompt_id}{file_extension}"
            file_path = os.path.join(file_dir, new_filename)

            # Save the file
            await file.save(file_path)
            self.bot.prompt_info[prompt_id]["image"] = new_filename

        # Save to persistent storage
        self.bot.save()

        # Log to log channel
        if "log_channel_id" in self.bot.config[guild_id]:
            log_channel = self.bot.get_channel(
                self.bot.config[guild_id]["log_channel_id"]
            )
            if log_channel:
                log_embed = discord.Embed(
                    title=f"File added to {prompt_id}",
                    description=f"Added: `{new_filename if 'new_filename' in locals() else file.filename}`",
                    color=discord.Color.green(),
                )
                log_embed.set_author(
                    name=interaction.user.name,
                    icon_url=(
                        interaction.user.avatar.url if interaction.user.avatar else None
                    ),
                )
                log_embed.timestamp = discord.utils.utcnow()
                await log_channel.send(embed=log_embed)
                await log_channel.send(file=await file.to_file())

        # Confirm to user
        image_count = (
            len(self.bot.prompt_info[prompt_id]["image"])
            if isinstance(self.bot.prompt_info[prompt_id].get("image"), list)
            else 1
        )
        await interaction.followup.send(
            f"✅ File added to prompt `{prompt_id}`. This prompt now has {image_count} image(s).",
            ephemeral=True,
        )
