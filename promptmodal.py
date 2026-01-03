from utils import split_message
import discord
from promptview import PromptView
import datetime
import os
import asyncio
from typing import Optional

try:
    datadir = os.environ['SNAP_DATA']
except:
    print('SNAP_DATA must be set')

prompt_image_dir = os.path.join(datadir, 'prompt_images')

class PromptModal(discord.ui.Modal):
    def __init__(self, interaction: discord.Interaction, bot = None, file: Optional[discord.Attachment] = None) -> None:
        super().__init__(title="Prompt Submission")
        self.interaction = interaction
        self.bot = bot
        self.guild_id = str(interaction.guild.id)
        self.channels = [channel for channel in interaction.guild.channels 
                         if isinstance(channel, discord.TextChannel) and channel.category_id == self.bot.config[self.guild_id]['category_id'] and "district-" in channel.name]
        self.add_item(discord.ui.TextInput(label="Prompt ID", placeholder="Enter the prompt id", custom_id="prompt_id"))
        self.add_item(discord.ui.TextInput(label="Prompt", placeholder="Enter your prompt", custom_id="prompt", style=discord.TextStyle.paragraph))
        self.file = file
        print(f"Found {len(self.channels)} channels in category {self.bot.config[self.guild_id]['category_id']}")

    async def callback(self, interaction: discord.Interaction):
        prompt_id = self.get_item("prompt_id").value
        prompt = self.get_item("prompt").value

        if not prompt_id or not prompt:
            await interaction.response.send_message("Please fill out all fields", ephemeral=True)
            return

    async def on_submit(self, interaction: discord.Interaction):
        #try:
        if not self.channels:
            await interaction.response.send_message("No valid channels found in the configured category. Please contact Phoenix.", ephemeral=True)
            return

        if True:
            view = PromptView(self.channels, self.bot)
            msg = await interaction.response.send_message("Select a channel:", view=view, ephemeral=True)
            self.interaction = interaction
            prompt_id = self.children[0].value.upper().strip()
            prompt = self.children[1].value
            async def process_prompt(self, interaction: discord.Interaction):
                for count in range(0, 30):
                    if not view.is_finished():
                        print("sleeping...")
                        await asyncio.sleep(1)
                    else:
                        break

                if view.is_finished():
                    print("is finished")
                    self.bot.prompt_info[prompt_id] = {}

                    channel_id = view.channel_select.channel_id

                    if self.file and channel_id:
                        if self.file.filename.endswith(".png") or self.file.filename.endswith(".jpg"):
                            file_dir = os.path.join(prompt_image_dir, self.guild_id)
                            file_path = os.path.join(file_dir, prompt_id + os.path.splitext(self.file.filename)[1])
                            os.makedirs(file_dir, exist_ok=True)
                            await self.file.save(file_path)
                            self.bot.prompt_info[prompt_id]['image'] = file_path
                        else:
                            await interaction.response.send_message("Please upload a .png or .jpg file.")

                    self.bot.prompt_info[prompt_id]['message'] = prompt
                    self.bot.prompt_info[prompt_id]['channel'] = channel_id
                    log_channel = self.bot.get_channel(self.bot.config[self.guild_id]['log_channel_id'])
                    log_embed = discord.Embed(
                        title=f"{prompt_id} prompt saved.",
                        color=discord.Color.blue())
                    log_embed.set_author(name=f"{interaction.user.name}", icon_url=f"{interaction.user.avatar}")
                    if interaction.guild.icon != None:
                        log_embed.set_thumbnail(url=f"{interaction.guild.icon.url}")
                    log_embed.timestamp = datetime.datetime.now()
                    if any(channel.id == self.bot.config[self.guild_id]['log_channel_id'] for channel in self.interaction.guild.channels):
                        await log_channel.send(embed=log_embed)
                        messages = split_message(prompt)
                        for message in messages:
                            await log_channel.send(message)
                        if 'image' in self.bot.prompt_info[prompt_id].keys():
                            file_name = self.bot.prompt_info[prompt_id]['image']
                            file_path = os.path.join(prompt_image_dir, self.guild_id, file_name)
                            await log_channel.send(file=discord.File(file_path))
                    else:
                        print(f"Log channel not found: {self.bot.config[self.guild_id]['log_channel_id']}")
                    view.remove_item(view.channel_select)
                    msg = await interaction.original_response()
                    await interaction.followup.edit_message(msg.id, content=f"Prompt saved with ID {prompt_id}", view=view)
                else:
                    print("Not finished")
                    view.remove_item(view.channel_select)
                    msg = await interaction.original_response()
                    await interaction.followup.edit_message(msg.id, content="Timed out.", view=view)
            await process_prompt(self, interaction)
        #except Exception as e:
        #    await interaction.followup.send("An error occurred. Please try again.", ephemeral=True)
        #    print(f"Error: {e}")
        # Saves prompts to json
        self.bot.save()
