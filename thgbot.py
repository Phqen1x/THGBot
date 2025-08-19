import discord
from discord import app_commands
from discord.ext import commands
from promptview import PromptView
from promptmodal import PromptModal
from addtopromptmodal import AddToPromptModal
from confirmationview import ConfirmationView
from utils import split_message
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
config_dir = os.path.join(datadir, 'config')

class THGBot(commands.Bot):
    def __init__(self, *, intents: discord.Intents):
        super().__init__(command_prefix='!', intents=intents)
        self.prompt_info = {} 
        self.config = {}
        self.load()

    def save(self):
        # Check for prompt_dir and save data to json
        if not os.path.exists(prompt_dir):
            os.makedirs(prompt_dir)
        with open(os.path.join(prompt_dir, 'prompt_info.json'), 'w') as f:
            json.dump(self.prompt_info, f)

        # Check for config_dir and save data to json
        if not os.path.exists(config_dir):
            os.makedirs(config_dir)
        with open(os.path.join(config_dir, 'config.json'), 'w') as f:
            json.dump(self.config, f)
        print(self.config)

    def load(self):
        # Check for prompt_dir and load json
        if os.path.exists(os.path.join(prompt_dir, "prompt_info.json")):
            with open(os.path.join(prompt_dir, 'prompt_info.json'), 'r') as f:
                self.prompt_info = json.load(f)
        else:
            self.prompt_info = {}

        # Check for config_dir and load json
        if os.path.exists(os.path.join(config_dir, 'config.json')):
            with open(os.path.join(config_dir, 'config.json'), 'r') as f:
                self.config = json.load(f)
        else:
            self.config = {}
            pass

    async def on_ready(self):
        await bot.tree.sync()
        print(f"Logged in as {self.user}")

intents = discord.Intents.default()
intents.message_content = True

bot = THGBot(intents=intents)
@bot.event
async def on_guild_join(guild):
    guild_id = str(guild.id)
    guild_prompts_dir = os.path.join(datadir, 'prompt', str(guild_id))
    bot.config[guild_id] = {'log_channel_id':  None, 'category_id': None}
    bot.save()

@bot.tree.command(name='set-log-channel', description='Sets the channel for logs to be sent to')
async def set_log_channel(interaction: discord.Interaction, channel_id: Optional[str], channel_name: Optional[str]):
    guild_id = str(interaction.guild.id)
    print(f'channel_id: {channel_id}')
    print(f'First: {bot.config}')
    if channel_id:
        channel_id = channel_id.strip()
        print(f'Second: {bot.config}')
        if any(channel.id == int(channel_id) for channel in interaction.guild.channels):
            print(f'Third: {bot.config}')
            bot.config[guild_id]['log_channel_id'] = int(channel_id)
            bot.save()
            try:
                await interaction.response.send_message(f'Log channel set to <#{bot.config[guild_id]["log_channel_id"]}>', ephemeral=True)
            except Exception as e:
                await interaction.response.send_message('An error occured. Please try again.')
                print(f'Exception: {e}')
        else:
            try:
                await interaction.response.send_message('Channel not found', ephemeral=True)
            except Exception as e:
                await interaction.response.send_message('An error occured. Please try again.')
                print(f'Exception: {e}')
    elif channel_name:
        channel_name = channel_name.strip()
        for channel in interaction.guild.channels:
            if channel_name.lower() == channel.name.lower():
                bot.config[guild_id]['log_channel_id'] = channel.id
                try:
                    await interaction.response.send_message(f'Log channel set to <#{bot.config[guild_id]["log_channel_id"]}>', ephemeral=True)
                except Exception as e:
                    await interaction.response.send_message('An error occured. Please try again.')
                    print(f'Exception: {e}')
                bot.save()
                sent = True
                break
        if not sent:
            try:
                await interaction.response.send_message('Channel not found', ephemeral=True)
            except Exception as e:
                await interaction.response.send_message('An error occured. Please try again.')
                print(f'Exception: {e}')
    else:
        try:
            await interaction.response.send_message('Provide an argument', ephemeral=True)
        except Exception as e:
            await interaction.response.send_message('An error occured. Please try again.')
            print(f'Exception: {e}')

@bot.tree.command(name='set-category', description='Sets the category for prompts to be sent to')
async def set_category(interaction: discord.Interaction, category_id: Optional[str], category_name: Optional[str]):
    guild_id = str(interaction.guild.id)
    sent = False
    if category_id:
        category_id = category_id.strip()
        if any(category.id == int(category_id) for category in interaction.guild.categories):
            bot.config[guild_id]['category_id'] = int(category_id)
            bot.save()
            try:
                await interaction.response.send_message(f'Prompt category set to <#{bot.config[guild_id]["category_id"]}>', ephemeral=True)
            except Exception as e:
                await interaction.response.send_message('An error occured. Please try again.')
                print(f'Exception: {e}')

        else:
            try:
                await interaction.response.send_message('Category not found', ephemeral=True)
            except Exception as e:
                await interaction.response.send_message('An error occured. Please try again.')
                print(f'Exception: {e}')
    elif category_name:
        category_name = category_name.strip()
        for category in interaction.guild.categories:
            if category_name.lower() == category.name.lower():
                bot.config[guild_id]['category_id'] = category.id
                bot.save()
                try:
                    await interaction.response.send_message(f'Prompt category set to <#{bot.config[guild_id]["category_id"]}>', ephemeral=True)
                except Exception as e:
                    await interaction.response.send_message('An error occured. Please try again.')
                    print(f'Exception: {e}')
                sent = True
                break
        if not sent:
            try:
                await interaction.response.send_message('Category not found', ephemeral=True)
            except Exception as e:
                await interaction.response.send_message('An error occured. Please try again.')
                print(f'Exception: {e}')

async def prompt_ids_list(interaction: discord.Interaction):
    if bot.prompt_info:
        prompt_keys = list(bot.prompt_info.keys())
        prompt_mentions = [f"<#{bot.prompt_info[prompt_id]['channel']}>" for prompt_id in bot.prompt_info.keys() if bot.prompt_info[prompt_id]['channel']]
        id_list_embed = discord.Embed(
                title=f"**Prompts**\n",
                color=discord.Color.green())
        id_list_embed.add_field(name="**Prompt IDs**", value=f"**{"\n".join(prompt_keys)}**", inline=True)
        id_list_embed.add_field(name="**Prompt channels**", value=f"{'\n'.join(prompt_mentions)}", inline=True)
        id_list_embed.set_author(name=f"{interaction.user.name}", icon_url=f"{interaction.user.avatar}")
        id_list_embed.set_thumbnail(url=f"{interaction.user.avatar}")
        id_list_embed.timestamp = datetime.datetime.now()
        await interaction.response.send_message(embed=id_list_embed, ephemeral=True)
    else:
        await interaction.response.send_message("No prompts found", ephemeral=True)

@bot.tree.command(name="view-prompt-ids", description="Lists all prompt_ids")
async def view_prompt_ids(interaction: discord.Interaction):
    await prompt_ids_list(interaction)

@bot.tree.command(name="view-prompt", description="View a prompt")
async def viewPrompt(interaction:discord.Interaction, prompt_id: str):
    prompt_id = prompt_id.upper().strip()
    guild_id = str(interaction.guild.id)
    if prompt_id in bot.prompt_info.keys():
        message = bot.prompt_info[prompt_id]['message']
        messages = split_message(message)
        if messages:
            await interaction.response.send_message(messages[0], ephemeral=True)
            for msg in messages[1:]:
                await interaction.followup.send(msg, ephemeral=True)
            if 'image' in bot.prompt_info[prompt_id].keys():
                file_name = bot.prompt_info[prompt_id]['image']
                os.makedirs(os.path.join(prompt_image_dir, guild_id), exist_ok=True)
                file_path = os.path.join(prompt_image_dir, guild_id, file_name)
                await interaction.followup.send(file=discord.File(file_path), ephemeral=True)
        else:
            await interaction.response.send_message("Prompt is empty", ephemeral=True)
    else:
        await interaction.response.send_message("Prompt not found", ephemeral=True)

@bot.tree.command(name="save-prompt", description="Stores prompt info using a modal UI")
async def save_prompt(interaction: discord.Interaction, file: Optional[discord.Attachment]):
    guild_id = str(interaction.guild.id)
    try:
        os.makedirs(os.path.join(prompt_image_dir, guild_id), exist_ok=True)
        if not file:
            modal = PromptModal(interaction, bot)
            await interaction.response.send_modal(modal)
        elif file.filename.endswith(".png") or file.filename.endswith(".jpg"):
            file_path = os.path.join(prompt_image_dir, guild_id, file.filename)
            await file.save(file_path)
            modal = PromptModal(interaction, bot, file.filename)
            await interaction.response.send_modal(modal)
        else:
            await interaction.response.send_message("Please upload a .png or .jpg file.")
    except Exception as e:
        await interaction.response.send_message("An error occured. Please try again.")
        print(f"Error: {e}")


@bot.tree.command(name="add-to-prompt", description="Adds content to a prompt using a modal UI")
async def add_to_prompt(interaction: discord.Interaction, file: Optional[discord.Attachment]):
    guild_id = str(interaction.guild.id)
    try:
        os.makedirs(os.path.join(prompt_image_dir, guild_id), exist_ok=True)
        if not file:
            modal = AddToPromptModal(interaction, bot)
            await interaction.response.send_modal(modal)
        elif file.filename.endswith(".png") or file.filename.endswith(".jpg"):
            file_path = os.path.join(prompt_image_dir, guild_id, file.filename)
            await file.save(file_path)
            modal = AddToPromptModal(interaction, bot, file.filename)
            await interaction.response.send_modal(modal)
        else:
            await interaction.response.send_message("Please upload a .png or .jpg file.")
    except Exception as e:
        await interaction.response.send_message("An error occured. Please try again.")
        print(f"Error: {e}")


@bot.tree.command(name="send-prompt", description="Send a prompt")
async def sendPrompt(interaction: discord.Interaction, prompt_id: str):
    # Sends the prompt
    prompt_id = prompt_id.strip().upper()
    guild_id = str(interaction.guild.id)
    if prompt_id in bot.prompt_info:
        channel = interaction.guild.get_channel(int(bot.prompt_info[prompt_id]['channel']))
        log_channel = bot.get_channel(bot.config[guild_id]['log_channel_id'])
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
                os.makedirs(os.path.join(prompt_image_dir, guild_id), exist_ok=True)
                file_name = bot.prompt_info[prompt_id]['image']
                file_path = os.path.join(prompt_image_dir, guild_id, file_name)
                await channel.send(file=discord.File(file_path))
                try:
                    os.unlink(file_path)
                except FileNotFoundError:
                    pass
            del bot.prompt_info[prompt_id]
            bot.save()
            await interaction.response.send_message(f"Prompt {prompt_id} sent in channel {channel.mention}")
            await log_channel.send(embed=log_embed)
    else:
        await interaction.response.send_message("Prompt not found")

@bot.tree.command(name="send-all-prompts", description="Send all prompts")
@commands.has_role("Admin")
async def sendAllPrompts(interaction: discord.Interaction):
    # Sends all the prompts

    confirmSend = ConfirmationView()
    print(len(bot.prompt_info.keys()))
    await interaction.response.send_message(f"There are {len(bot.prompt_info.keys())} prompts saved. Are you sure you want to send all prompts? This will also clear them from the list.", ephemeral=True, view=confirmSend)
    await confirmSend.wait()
    guild_id = str(interaction.guild.id)
    prompt_keys = list(bot.prompt_info.keys())
    prompt_mentions = [f"<#{bot.prompt_info[prompt_id]['channel']}>" for prompt_id in bot.prompt_info.keys() if bot.prompt_info[prompt_id]['channel']]
    log_channel = bot.get_channel(bot.config[guild_id]['log_channel_id'])
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
                    if 'image' in bot.prompt_info[prompt_id].keys():
                        try:
                            os.makedirs(os.path.join(prompt_image_dir, guild_id), exist_ok=True)
                            file_name = bot.prompt_info[prompt_id]['image']
                            file_path = os.path.join(prompt_image_dir, guild_id, file_name)
                            await channel.send(file=discord.File(file_path))
                            try:
                                os.unlink(file_path)
                            except FileNotFoundError:
                                pass
                        except discord.Forbidden:
                            print(f"Forbidden to send files to {channel.name}")
                        except discord.HTTPException as e:
                            print(f"HTTP exception while sending message to {channel.name}: {e}")
                    bot.prompt_info = {}
                    bot.save()
                    print(f"Sent prompt {prompt_id} to {channel.name}")
                except discord.Forbidden:
                    await interaction.followup.send(f"The bot doesn't have permission to send files in {channel.name}")
                    print(f"Forbidden to send messages to {channel.name}")
                except discord.HTTPException as e:
                    print(f"HTTP exception while sending message to {channel.name}: {e}")
            else:
                await interaction.followup.send(f"Channel {channel} does not exit")
                print(f"Channel {channel} does not exist")
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


bot.run(token)
