from utils import split_message
import discord
import datetime

class AddToPromptModal(discord.ui.Modal):
    def __init__(self, interaction: discord.Interaction, bot = None, file_name: str = None) -> None:
        super().__init__(title="Prompt Addendum")
        self.interaction = interaction
        self.bot = bot
        self.channels = [channel for channel in interaction.guild.channels 
                         if isinstance(channel, discord.TextChannel) and channel.category_id == 1395987021712986133]
        self.add_item(discord.ui.TextInput(label="Prompt ID", placeholder="Enter the prompt id", custom_id="prompt_id"))
        self.add_item(discord.ui.TextInput(label="Prompt Addendum", placeholder="Enter your prompt addition", custom_id="prompt_addendum", style=discord.TextStyle.paragraph))
        self.file_name = file_name

    async def on_submit(self, interaction: discord.Interaction):
        try:
            prompt_id = self.children[0].value.upper().strip()
            prompt = self.children[1].value
            if prompt_id not in self.bot.prompt_info.keys():
                self.bot.prompt_info[prompt_id] = {}
            if self.file_name:
                self.bot.prompt_info[prompt_id]['image'] = self.file_name
            
            self.bot.prompt_info[prompt_id]['message'] += prompt
            log_channel = self.bot.get_channel(self.bot.log_channel_id)
            log_embed = discord.Embed(
                    title=f"{prompt_id} prompt has been added to.",
                    color=discord.Color.green())
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
            await interaction.response.send_message(f"{prompt_id} Prompt edited successfully.", ephemeral=True)
        except Exception as e:
            await interaction.followup.send("An error occurred. Please try again.", ephemeral=True)
            print(f"Error: {e}")
        # Saves prompts to json
        self.bot.save()
        

