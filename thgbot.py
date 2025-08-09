import discord
from discord import app_commands
from discord.ext import commands
from promptview import PromptView
from promptmodal import PromptModal
from addtopromptmodal import AddToPromptModal
from confirmationview import ConfirmationView
import os
import sys
from typing import Optional
import datetime
import json

try:
    datadir = os.environ['SNAP_DATA']
except:
    print('SNAP_DATA must be set')

try:
    token = os.environ['TOKEN']
except:
    print('TOKEN must be set')
    sys.exit(1)

prompt_image_dir = os.path.join(datadir, 'prompt_images')
prompt_dir = os.path.join(datadir, 'prompts')

class MyBot(commands.Bot):
    def __init__(self, *, intents: discord.Intents):
        super().__init__(command_prefix='!', intents=intents)
        self.prompt_info = {} 
        self.load()
        self.guild = None
        self.log_channel_id = 1396701637925408908

    def save(self):
        if not os.path.exists(prompt_dir):
            os.makedirs(prompt_dir)
        with open(os.path.join(prompt_dir, 'prompt_info.json'), 'w') as f:
            json.dump(self.prompt_info, f)

    def load(self):
        if os.path.exists(os.path.join(prompt_dir, "prompt_info.json")):
            with open(os.path.join(prompt_dir, 'prompt_info.json'), 'r') as f:
                self.prompt_info = json.load(f)
        else:
            self.prompt_info = {}

    async def on_ready(self):
        self.guild = self.get_guild(793600464570548254)
        await bot.tree.sync()
        print(f"Logged in as {self.user}")

intents = discord.Intents.default()
intents.message_content = True

bot = MyBot(intents=intents)

async def prompt_ids_list(interaction: discord.Interaction):
    if bot.prompt_info:
        prompt_ids = list(bot.prompt_info.keys())
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

@bot.tree.command(name="save-prompt", description="Stores prompt info using a modal UI")
async def save_prompt(interaction: discord.Interaction, file: Optional[discord.Attachment]):
    role_id =  1396889274615599134
    role = interaction.guild.get_role(role_id)
    if role in interaction.user.roles:
        try:
            if not os.path.exists(prompt_image_dir):
                os.makedirs(prompt_image_dir)
            if not file:
                print('before')
                modal = PromptModal(interaction, bot)
                await interaction.response.send_modal(modal)
                print('after')
            elif file.filename.endswith(".png") or file.filename.endswith(".jpg"):
                file_path = os.path.join(prompt_image_dir, file.filename)
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
            if not os.path.exists(prompt_image_dir):
                os.makedirs(prompt_image_dir)
            if not file:
                modal = AddToPromptModal(interaction)
                await interaction.response.send_modal(modal)
            elif file.filename.endswith(".png") or file.filename.endswith(".jpg"):
                file_path = os.path.join(prompt_image_dir, file.filename)
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
    if prompt_id in bot.prompt_info:
        channel = interaction.guild.get_channel(int(bot.prompt_info[prompt_id]['channel']))
        log_channel = bot.get_channel(bot.log_channel_id)
        log_embed = discord.Embed(
                title=f"{prompt_id} prompt sent to {channel.mention}",
                color=discord.Color.green())
        log_embed.set_author(name=f"{interaction.user.name}", icon_url=f"{interaction.user.avatar}")
        log_embed.set_thumbnail(url=f"{interaction.user.avatar}")
        log_embed.timestamp = datetime.datetime.now()
        if channel:
            message = bot.prompt_info[prompt_id]['message']
            messages = split_message(message)
            first_message = True
            for msg in messages:
                message = await channel.send(msg)
                if first_message:
                    await message.pin()
                    first_message = False
            if 'image' in bot.prompt_info[prompt_id].keys():
                file_name = bot.prompt_info[prompt_id]['image']
                file_path = os.path.join(prompt_image_dir, file_name)
                await channel.send(file=discord.File(file_path))
            await interaction.response.send_message(f"Prompt {prompt_id} sent in channel {channel}")
            await log_channel.send(embed=log_embed)
    else:
        await interaction.response.send_message("Prompt not found")

@bot.tree.command(name="send-all-prompts", description="Send all prompts")
@commands.has_role("Admin")
async def sendAllPrompts(interaction: discord.Interaction):
    # Sends all the prompts

    confirmSend = ConfirmationView()
    print(len(bot.prompt_info.keys()))
    await interaction.response.send_message(f"There are {len(bot.prompt_info.keys())} prompts saved. Are you sure you want to send all prompts?", ephemeral=True, view=confirmSend)
    await confirmSend.wait()
    prompt_keys = list(bot.prompt_info.keys())
    prompt_mentions = [f"<#{bot.prompt_info[prompt_id]['channel']}>" for prompt_id in bot.prompt_info.keys() if bot.prompt_info[prompt_id]['channel']]
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
        for prompt_id in bot.prompt_info.keys():
            channel_id = bot.prompt_info[prompt_id]['channel']
            channel = interaction.guild.get_channel(int(channel_id))
            if channel:
                try:
                    message = bot.prompt_info[prompt_id]['message']
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
            if 'image' in bot.prompt_info[prompt_id].keys():
                try:
                    file_name = bot.prompt_info[prompt_id]['image']
                    file_path = os.path.join(prompt_image_dir, file_name)
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
        await interaction.response.send_message(f"There are {len(bot.prompt_info.keys())} prompts saved. Are you sure you want to delete all prompts?", ephemeral=True, view=confirmSend)
        await confirmSend.wait()
        if confirmSend.confirmed:
            bot.prompt_info = {}
            bot.save()
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
    if prompt_id in bot.prompt_info.keys():
        message = bot.prompt_info[prompt_id]['message']
        messages = split_message(message)
        if messages:
            await interaction.response.send_message(messages[0], ephemeral=True)
            for msg in messages[1:]:
                await interaction.followup.send(msg, ephemeral=True)
        else:
            await interaction.response.send_message("Prompt is empty", ephemeral=True)
    else:
        await interaction.response.send_message("Prompt not found", ephemeral=True)

bot.run(token)
