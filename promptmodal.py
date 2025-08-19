from utils import split_message
import discord
from promptview import PromptView
import datetime
import os

try:
    datadir = os.environ['SNAP_DATA']
except:
    print('SNAP_DATA must be set')

prompt_image_dir = os.path.join(datadir, 'prompt_images')

class PromptModal(discord.ui.Modal):
    def __init__(self, interaction: discord.Interaction, bot = None, file_name: str = None) -> None:
        super().__init__(title="Prompt Submission")
        self.interaction = interaction
        self.bot = bot
        self.guild_id = str(interaction.guild.id)
        self.channels = [channel for channel in interaction.guild.channels 
                         if isinstance(channel, discord.TextChannel) and channel.category_id == self.bot.config[self.guild_id]['category_id']]
        self.add_item(discord.ui.TextInput(label="Prompt ID", placeholder="Enter the prompt id", custom_id="prompt_id"))
        self.add_item(discord.ui.TextInput(label="Prompt", placeholder="Enter your prompt", custom_id="prompt", style=discord.TextStyle.paragraph))
        self.file_name = file_name

    async def callback(self, interaction: discord.Interaction):
        prompt_id = self.get_item("prompt_id").value
        prompt = self.get_item("prompt").value

        if not prompt_id or not prompt:
            await interaction.response.send_message("Please fill out all fields", ephemeral=True)
            return

    async def on_submit(self, interaction: discord.Interaction):
        try:
            prompt_id = self.children[0].value.upper().strip()
            prompt = self.children[1].value
            self.bot.prompt_info[prompt_id] = {}
            if self.file_name:
                self.bot.prompt_info[prompt_id]['image'] = self.file_name
            
            view = PromptView(self.channels, self.bot)
            msg = await interaction.response.send_message("Select a channel:", view=view, ephemeral=True)
            await view.wait()
            channel_id = view.channel_select.channel_id

            self.bot.prompt_info[prompt_id]['message'] = prompt
            self.bot.prompt_info[prompt_id]['channel'] = channel_id
            log_channel = self.bot.get_channel(self.bot.config[self.guild_id]['log_channel_id'])
            log_embed = discord.Embed(
                    title=f"{prompt_id} prompt saved.",
                    color=discord.Color.blue())
            log_embed.set_author(name=f"{interaction.user.name}", icon_url=f"{interaction.user.avatar}")
            log_embed.set_thumbnail(url=f"{interaction.user.avatar}")
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
            await interaction.followup.send(f"Prompt saved with ID {prompt_id}", ephemeral=True)
        except Exception as e:
            await interaction.followup.send("An error occurred. Please try again.", ephemeral=True)
            print(f"Error: {e}")
        # Saves prompts to json
        self.bot.save()
