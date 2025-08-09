from utils import split_message
import discord
from promptview import PromptView

class PromptModal(discord.ui.Modal):
    def __init__(self, interaction: discord.Interaction, bot = None, file_name: str = None) -> None:
        super().__init__(title="Prompt Submission")
        self.log_channel_id = 1396701637925408908
        self.interaction = interaction
        self.channels = [channel for channel in interaction.guild.channels 
                         if isinstance(channel, discord.TextChannel) and channel.category_id == 1395987021712986133]
        self.add_item(discord.ui.TextInput(label="Prompt ID", placeholder="Enter the prompt id", custom_id="prompt_id"))
        self.add_item(discord.ui.TextInput(label="Prompt", placeholder="Enter your prompt", custom_id="prompt", style=discord.TextStyle.paragraph))
        self.file_name = file_name
        print("PromptModal")

    async def on_submit(self, interaction: discord.Interaction):
        try:
            prompt_id = self.children[0].value.upper().strip()
            prompt = self.children[1].value
            bot.prompt_info[prompt_id] = {}
            if self.file_name:
                bot.prompt_info[prompt_id]['image'] = self.file_name
            
            view = PromptView(self.channels, bot)
            msg = await interaction.response.send_message("Select a channel:", view=view, ephemeral=True)
            await view.wait()
            channel_id = view.channel_select.channel_id

            bot.prompt_info[prompt_id]['message'] = prompt
            bot.prompt_info[prompt_id]['channel'] = channel_id
            log_channel = bot.get_channel(bot.log_channel_id)
            log_embed = discord.Embed(
                    title=f"{prompt_id} prompt saved.",
                    color=discord.Color.blue())
            log_embed.set_author(name=f"{interaction.user.name}", icon_url=f"{interaction.user.avatar}")
            log_embed.set_thumbnail(url=f"{interaction.user.avatar}")
            log_embed.timestamp = datetime.datetime.now()
            if log_channel:
                await log_channel.send(embed=log_embed)
                messages = split_message(prompt)
                for message in messages:
                    await log_channel.send(message)
            else:
                print(f"Log channel not found: {log_channel_id}")
            await interaction.followup.send(f"Prompt save with ID {prompt_id}", ephemeral=True)
        except Exception as e:
            await interaction.followup.send("An error occurred. Please try again.", ephemeral=True)
            print(f"Error: {e}")
        # Saves prompts to json
        bot.save()
