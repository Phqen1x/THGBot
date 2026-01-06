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
    def __init__(
        self,
        interaction: discord.Interaction,
        bot=None,
        file: Optional[discord.Attachment] = None,
    ) -> None:
        super().__init__(title="Prompt Addendum")
        self.interaction = interaction
        self.bot = bot
        self.guild_id = str(interaction.guild.id)
        self.channels = [
            channel
            for channel in interaction.guild.channels
            if isinstance(channel, discord.TextChannel)
            and channel.category_id == self.bot.config[self.guild_id]["category_id"]
        ]
        self.add_item(
            discord.ui.TextInput(
                label="Prompt ID",
                placeholder="Enter the prompt id",
                custom_id="prompt_id",
            )
        )
        self.add_item(
            discord.ui.TextInput(
                label="Prompt Addendum",
                placeholder="Enter your prompt addition",
                custom_id="prompt_addendum",
                style=discord.TextStyle.paragraph,
            )
        )
        self.file = file

    async def on_submit(self, interaction: discord.Interaction):
        try:
            prompt_id = self.children[0].value.upper().strip().replace(" ", "_")
            prompt = self.children[1].value
            if prompt_id not in self.bot.prompt_info.keys():
                self.bot.prompt_info[prompt_id] = {"message": ""}
            self.bot.prompt_info[prompt_id]["message"] += prompt
            log_channel = self.bot.get_channel(
                self.bot.config[self.guild_id]["log_channel_id"]
            )
            log_embed = discord.Embed(
                title=f"{prompt_id} prompt has been added to.",
                color=discord.Color.green(),
            )
            log_embed.set_author(
                name=f"{interaction.user.name}", icon_url=f"{interaction.user.avatar}"
            )
            log_embed.set_thumbnail(url=f"{interaction.user.avatar}")
            log_embed.timestamp = datetime.datetime.now()
            if any(
                channel.id == self.bot.config[self.guild_id]["log_channel_id"]
                for channel in self.interaction.guild.channels
            ):
                await log_channel.send(embed=log_embed)
                messages = split_message(prompt)
                for message in messages:
                    await log_channel.send(message)
                channel_id = self.bot.prompt_info[prompt_id]["channel"]
                if self.file and channel_id:
                    if self.file.filename.endswith(
                        ".png"
                    ) or self.file.filename.endswith(".jpg"):
                        file_dir = os.path.join(prompt_image_dir, self.guild_id)
                        file_path = os.path.join(
                            file_dir,
                            prompt_id + os.path.splitext(self.file.filename)[1],
                        )
                        os.makedirs(file_dir, exist_ok=True)
                        await self.file.save(file_path)
                        self.bot.prompt_info[prompt_id]["image"] = file_path
                        await log_channel.send(file=discord.File(file_path))
                    else:
                        await interaction.response.send_message(
                            "Please upload a .png or .jpg file."
                        )
            else:
                print(f"Log channel not found: {log_channel_id}")
            await interaction.response.send_message(
                f"{prompt_id} Prompt added to successfully.", ephemeral=True
            )
        except Exception as e:
            await interaction.response.send_message(
                "An error occurred. Please try again.", ephemeral=True
            )
            print(f"Error: {e}")
        # Saves prompts to json
        self.bot.save()
