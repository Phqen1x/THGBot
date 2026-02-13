from utils import split_message
import discord
import datetime
import os
from typing import Optional

try:
    datadir = os.environ["SNAP_DATA"]
except:
    print("SNAP_DATA must be set")

prompt_image_dir = os.path.join(datadir, "prompt_images")


class AddToPromptModal(discord.ui.Modal):
    def __init__(self, interaction: discord.Interaction, bot=None):
        super().__init__(title="Add to Prompt")
        self.interaction = interaction
        self.bot = bot
        self.guild_id = str(interaction.guild.id)
        self.add_item(
            discord.ui.TextInput(
                label="Tribute ID",
                placeholder="Enter the tribute ID (e.g., D1F)",
                custom_id="tribute_id",
            )
        )
        self.add_item(
            discord.ui.TextInput(
                label="Prompt Addition",
                placeholder="Enter your prompt addition",
                custom_id="prompt_addendum",
                style=discord.TextStyle.paragraph,
            )
        )

    async def on_submit(self, interaction: discord.Interaction):
        try:
            tribute_id = self.children[0].value.upper().strip()
            prompt_addendum = self.children[1].value
            
            # Get existing prompt
            prompt_data = self.bot.storage.get_prompt(tribute_id)
            if not prompt_data:
                await interaction.response.send_message(
                    f"No prompt found for tribute {tribute_id}", ephemeral=True
                )
                return
            
            # Update prompt message
            current_message = prompt_data.get('message', '')
            updated_message = f"{current_message}\n\n{prompt_addendum}"
            channel_id = prompt_data.get('channel_id') or prompt_data.get('channel')
            
            self.bot.storage.update_prompt(tribute_id, message=updated_message, channel_id=channel_id)
            self.bot.db.update_prompt(tribute_id, message=updated_message)
            
            log_channel = self.bot.get_channel(
                self.bot.config[self.guild_id]["log_channel_id"]
            )
            log_embed = discord.Embed(
                title=f"{tribute_id} prompt has been added to.",
                color=discord.Color.green(),
            )
            log_embed.set_author(
                name=f"{interaction.user.name}", icon_url=f"{interaction.user.avatar}"
            )
            log_embed.set_thumbnail(url=f"{interaction.user.avatar}")
            log_embed.timestamp = datetime.datetime.now()
            
            if log_channel:
                await log_channel.send(embed=log_embed)
                messages = split_message(prompt_addendum)
                for message in messages:
                    await log_channel.send(message)
            
            await interaction.response.send_message(
                f"{tribute_id} prompt added to successfully.", ephemeral=True
            )
        except Exception as e:
            await interaction.response.send_message(
                "An error occurred. Please try again.", ephemeral=True
            )
            print(f"Error: {e}")
