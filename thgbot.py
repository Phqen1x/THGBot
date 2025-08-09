import discord
from discord import app_commands
from discord.ext import commands
import os
from typing import Optional
import datetime

class MyBot(commands.Bot):
    def __init__(self, *, intents: discord.Intents):
        super().__init__(command_prefix='!', intents=intents)
        self.prompts = {}
        self.channels = {}
        self.prompt_images = {}
        self.guild = None
        self.log_channel_id = 1396701637925408908

    async def on_ready(self):
        self.guild = self.get_guild(793600464570548254)
        await bot.tree.sync()
        print(f"Logged in as {self.user}")

intents = discord.Intents.default()
intents.message_content = True

bot = MyBot(intents=intents)

async def prompt_ids_list(interaction: discord.Interaction):
    if bot.prompts:
        prompt_ids = list(bot.prompts.keys())
        embed = discord.Embed(
            title='**Prompt IDs:**\n',
            description=f'**{"\n".join(prompt_ids)}**',
            color=0x00ff00 # Green
        )
        await interaction.response.send_message(embed=embed, ephemeral=True)
    else:
        await interaction.response.send_message("No prompts found", ephemeral=True)

@bot.tree.command(name="view-prompt-ids", description="Lists all prompt_ids")
async def view_prompt_ids(interaction: discord.Interaction):
    await prompt_ids_list(interaction)

class TributeChannelSelector(discord.ui.Select):
    def __init__(self, channels):
        options = [
            discord.SelectOption(label=channel.name, description=channel.name, value=str(channel.id))
            for channel in channels
        ]
        super().__init__(placeholder='Select a channel', max_values=1, min_values=1, options=options)

    async def callback(self, interaction: discord.Interaction):
        await interaction.response.defer()
        self.channel_id = (self.values[0])
        self.view.stop()

class PromptView(discord.ui.View):
    def __init__(self, channels):
        super().__init__()
        self.channel_select = TributeChannelSelector(channels)
        self.add_item(self.channel_select)

    @property
    def channel_id(self):
        return int(self.channel_select.values[0])

class PromptModal(discord.ui.Modal):
    def __init__(self, interaction: discord.Interaction, file_name: str = None) -> None:
        super().__init__(title="Prompt Submission")
        self.interaction = interaction
        self.channels = [channel for channel in interaction.guild.channels 
                         if isinstance(channel, discord.TextChannel) and channel.category_id == 1395987021712986133]
        self.add_item(discord.ui.TextInput(label="Prompt ID", placeholder="Enter the prompt id", custom_id="prompt_id"))
        self.add_item(discord.ui.TextInput(label="Prompt", placeholder="Enter your prompt", custom_id="prompt", style=discord.TextStyle.paragraph))
        self.file_name = file_name

    async def on_submit(self, interaction: discord.Interaction):
        try:
            prompt_id = self.children[0].value.upper().strip()
            prompt = self.children[1].value
            bot.prompt_images[prompt_id] = self.file_name
            
            view = PromptView(self.channels)
            msg = await interaction.response.send_message("Select a channel:", view=view, ephemeral=True)
            await view.wait()
            channel_id = view.channel_select.channel_id

            bot.prompts[prompt_id] = prompt
            bot.channels[prompt_id] = channel_id
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


class AddToPromptModal(discord.ui.Modal):
    def __init__(self, interaction: discord.Interaction, file_name: str = None) -> None:
        super().__init__(title="Prompt Addendum")
        self.interaction = interaction
        self.channels = [channel for channel in interaction.guild.channels 
                         if isinstance(channel, discord.TextChannel) and channel.category_id == 1395987021712986133]
        self.add_item(discord.ui.TextInput(label="Prompt ID", placeholder="Enter the prompt id", custom_id="prompt_id"))
        self.add_item(discord.ui.TextInput(label="Prompt Addendum", placeholder="Enter your prompt addition", custom_id="prompt_addendum", style=discord.TextStyle.paragraph))
        self.file_name = file_name

    async def on_submit(self, interaction: discord.Interaction):
        try:
            prompt_id = self.children[0].value.upper().strip()
            prompt = self.children[1].value
            bot.prompt_images[prompt_id] = self.file_name
            
            bot.prompts[prompt_id] += prompt
            log_channel = bot.get_channel(bot.log_channel_id)
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
        

@bot.tree.command(name="save-prompt", description="Stores prompt info using a modal UI")
async def save_prompt(interaction: discord.Interaction, file: Optional[discord.Attachment]):
    role_id =  1396889274615599134
    role = interaction.guild.get_role(role_id)
    if role in interaction.user.roles:
        try:
            if not os.path.exists('prompt_images'):
                os.makedirs('prompt_images')
            if not file:
                modal = PromptModal(interaction)
                await interaction.response.send_modal(modal)
            elif file.filename.endswith(".png") or file.filename.endswith(".jpg"):
                file_path = f"prompt_images/{file.filename}"
                await file.save(file_path)
                modal = PromptModal(interaction, file.filename)
                await interaction.response.send_modal(modal)
            else:
                await interaction.response.send_message("Please upload a .png or .jpg file.")
        except Exception as e:
            await interaction.response.send_message("An error occured. Please try again.")
            print(f"Error: {e}")
    else:
        await interaction.response.send_message("You do not have the necessary role to run this command!")


@bot.tree.command(name="add-to-prompt", description="Adds content to a prompt using a modal UI")
async def add_to_prompt(interaction: discord.Interaction, file: Optional[discord.Attachment]):
    role_id = 1396889274615599134
    role = interaction.guild.get_role(role_id)
    if role in interaction.user.roles:
        try:
            if not os.path.exists('prompt_images'):
                os.makedirs('prompt_images')
            if not file:
                modal = AddToPromptModal(interaction)
                await interaction.response.send_modal(modal)
            elif file.filename.endswith(".png") or file.filename.endswith(".jpg"):
                file_path = f"prompt_images/{file.filename}"
                await file.save(file_path)
                modal = AddToPromptModal(interaction, file.filename)
                await interaction.response.send_modal(modal)
            else:
                await interaction.response.send_message("Please upload a .png or .jpg file.")
        except Exception as e:
            await interaction.response.send_message("An error occured. Please try again.")
            print(f"Error: {e}")
    else:
        await interaction.response.send_message("You do not have the necessary role to run this command!")


@bot.tree.command(name="send-prompt", description="Send a prompt")
async def sendPrompt(interaction: discord.Interaction, prompt_id: str):
    # Sends the prompt
    prompt_id = prompt_id.strip().upper()
    if prompt_id in bot.prompts:
        if prompt_id in bot.channels:
            channel = interaction.guild.get_channel(int(bot.channels.get(prompt_id)))
            log_channel = bot.get_channel(bot.log_channel_id)
            log_embed = discord.Embed(
                    title=f"{prompt_id} prompt sent to {channel.mention}",
                    color=discord.Color.green())
            log_embed.set_author(name=f"{interaction.user.name}", icon_url=f"{interaction.user.avatar}")
            log_embed.set_thumbnail(url=f"{interaction.user.avatar}")
            log_embed.timestamp = datetime.datetime.now()
            if channel:
                message = bot.prompts[prompt_id]
                messages = split_message(message)
                first_message = True
                for msg in messages:
                    message = await channel.send(msg)
                    if first_message:
                        await message.pin()
                        first_message = False
                if bot.prompt_images[prompt_id]:
                    file_name = bot.prompt_images[prompt_id]
                    file_path = f"prompt_images/{file_name}"
                    await channel.send(file=discord.File(file_path))
                await interaction.response.send_message(f"Prompt {prompt_id} sent in channel {channel}")
                await log_channel.send(embed=log_embed)
        else:
            await interaction.response.send_message("Channel not found")
    else:
        await interaction.response.send_message("Prompt not found")

class ConfirmationView(discord.ui.View):
    def __init__(self):
        super().__init__()
        self.confirmed = False

        self.send_button = discord.ui.Button(label="Send", style=discord.ButtonStyle.green)
        self.send_button.callback = self.send_callback
        self.add_item(self.send_button)

        self.cancel_button = discord.ui.Button(label="Cancel", style=discord.ButtonStyle.red)
        self.cancel_button.callback = self.cancel_callback
        self.add_item(self.cancel_button)

    async def send_callback(self, interaction: discord.Interaction):
        await interaction.response.defer()
        self.confirmed = True
        self.stop()

    async def cancel_callback(self, interaction: discord.Interaction):
        await interaction.response.defer()
        self.confirmed = False
        self.stop()

@bot.tree.command(name="send-all-prompts", description="Send all prompts")
@commands.has_role("Admin")
async def sendAllPrompts(interaction: discord.Interaction):
    # Sends all the prompts

    confirmSend = ConfirmationView()
    print(len(bot.prompts))
    await interaction.response.send_message(f"There are {len(bot.prompts)} prompts saved. Are you sure you want to send all prompts?", ephemeral=True, view=confirmSend)
    await confirmSend.wait()
    prompt_keys = list(bot.prompts.keys())
    prompt_mentions = [f"<#{channel}>" for channel in bot.channels.values() if channel]
    log_channel = bot.get_channel(bot.log_channel_id)
    log_embed = discord.Embed(
            title=f"All prompts sent.",
            color=discord.Color.green())
    log_embed.add_field(name="Prompt IDs", value=f"**{"\n".join(prompt_keys)}**", inline=True)
    log_embed.add_field(name="Prompt channels", value=f"{'\n'.join(prompt_mentions)}", inline=True)
    log_embed.set_author(name=f"{interaction.user.name}", icon_url=f"{interaction.user.avatar}")
    log_embed.set_thumbnail(url=f"{interaction.user.avatar}")
    log_embed.timestamp = datetime.datetime.now()
    
    if confirmSend.confirmed:
        for prompt_id, channel in bot.channels.items():
            channel_id = bot.channels.get(prompt_id)
            if prompt_id in bot.prompts:
                channel = interaction.guild.get_channel(int(channel_id))
                if channel:
                    try:
                        message = bot.prompts[prompt_id]
                        messages = split_message(message)
                        first_message = True
                        for msg in messages:
                            pin_message = await channel.send(msg)
                            if first_message:
                                await pin_message.pin()
                                first_message = False
                        print(f"Sent prompt {prompt_id} to {channel.name}")
                    except discord.Forbidden:
                        await interaction.followup.send(f"The bot doesn't have permission to send files in {channel.name}")
                        print(f"Forbidden to send messages to {channel.name}")
                    except discord.HTTPException as e:
                        print(f"HTTP exception while sending message to {channel.name}: {e}")
                else:
                    await interaction.followup.send(f"Channel {channel} does not exit")
                    print(f"Channel {channel} does not exist")
                if bot.prompt_images[prompt_id] and prompt_id in bot.prompt_images:
                    try:
                        file_name = bot.prompt_images[prompt_id]
                        file_path = f"prompt_images/{file_name}"
                        await channel.send(file=discord.File(file_path))
                    except discord.Forbidden:
                        print(f"Forbidden to send files to {channel.name}")
                    except discord.HTTPException as e:
                        print(f"HTTP exception while sneding message to {channel.name}: {e}")
        await interaction.followup.send("All prompts have been sent")
        await log_channel.send(embed=log_embed)
    else:
        await interaction.followup.send("Cancelled sending all prompts!", ephemeral=True)

@bot.tree.command(name="clear-all-prompts", description="Clear all prompts")
@commands.has_role("Admin")
async def clearAllPrompts(interaction: discord.Interaction):
    # Clears all the prompts
    try:
        confirmSend = ConfirmationView()
        await interaction.response.send_message(f"There are {len(bot.prompts)} prompts saved. Are you sure you want to delete all prompts?", ephemeral=True, view=confirmSend)
        await confirmSend.wait()
        if confirmSend.confirmed:
            bot.prompts = {}
            bot.channels = {}
            await interaction.followup.send("Prompts cleared", ephemeral=True)
        else:
            await interaction.followup.send("Cancelled clearing all prompts!")
    except Exception as e:
        print(e)
        await interaction.response.send_message("Prompts not cleared", ephemeral=True)

@bot.tree.command(name="view-prompt", description="View a prompt")
@commands.has_role("Gamemaker")
async def viewPrompt(interaction:discord.Interaction, prompt_id: str):
    prompt_id = prompt_id.upper().strip()
    if prompt_id in bot.prompts:
        message = bot.prompts[prompt_id]
        messages = split_message(message)
        if messages:
            await interaction.response.send_message(messages[0], ephemeral=True)
            for msg in messages[1:]:
                await interaction.followup.send(msg, ephemeral=True)
        else:
            await interaction.response.send_message("Prompt is empty", ephemeral=True)
    else:
        await interaction.response.send_message("Prompt not found", ephemeral=True)

def split_message(message: str) -> list[str]:
    messages = []
    while len(message) > 2000:
        index = message[:2000].rfind('\n')
        if index == -1:
            index = 2000
        messages.append(message[:index])
        message = message[index:]
    messages.append(message)
    return messages

try:
    apikey = os.environ['TOKEN']
except:
    print('TOKEN must be set')
    sys.exit(1)
bot.run(apikey)
