import discord
from discord import app_commands
from discord.ext import commands
from promptview import PromptView
from promptmodal import PromptModal
from addtopromptmodal import AddToPromptModal
from confirmationview import ConfirmationView
from utils import split_message
from promptsender import send_all_prompts_concurrent
from inventory import Inventory
from inventory_commands import register_inventory_commands, _format_inventory_embed
from database import SQLDatabase
from storage import StorageManager
from tributecommands import register_tribute_commands
import os
import sys
from typing import Optional
import datetime
import json
import asyncio
import re
import logging
import time

logger = logging.getLogger(__name__)

try:
    datadir = os.environ["SNAP_DATA"].replace(os.environ["SNAP_REVISION"], "current")
except:
    print("SNAP_DATA must be set")

try:
    token = os.environ["TOKEN"]
except:
    print("TOKEN must be set")
    sys.exit(1)

prompt_image_dir = os.path.join(datadir, "prompt_images")
prompt_dir = os.path.join(datadir, "prompts")
config_dir = os.path.join(datadir, "config")


class THGBot(commands.Bot):
    def __init__(self, *, intents: discord.Intents):
        super().__init__(command_prefix="!", intents=intents)
        self.prompt_info = {}
        self.config = {}
        self.datadir = datadir
        self.prompt_image_dir = prompt_image_dir
        self.inventory = Inventory(datadir)
        self.db = SQLDatabase(os.path.join(datadir, "thgbot.db"))
        self.storage = StorageManager(self.db)
        self.load()

    def save(self):
        # Check for prompt_dir and save data to json
        if not os.path.exists(prompt_dir):
            os.makedirs(prompt_dir)
        with open(os.path.join(prompt_dir, "prompt_info.json"), "w") as f:
            json.dump(self.prompt_info, f)

        # Check for config_dir and save data to json
        if not os.path.exists(config_dir):
            os.makedirs(config_dir)
        with open(os.path.join(config_dir, "config.json"), "w") as f:
            json.dump(self.config, f)
        print(self.config)

    def load(self):
        # Check for prompt_dir and load json
        if os.path.exists(os.path.join(prompt_dir, "prompt_info.json")):
            with open(os.path.join(prompt_dir, "prompt_info.json"), "r") as f:
                self.prompt_info = json.load(f)
        else:
            self.prompt_info = {}

        # Check for config_dir and load json
        if os.path.exists(os.path.join(config_dir, "config.json")):
            with open(os.path.join(config_dir, "config.json"), "r") as f:
                self.config = json.load(f)
        else:
            self.config = {}
            pass

    async def on_ready(self):
        await bot.tree.sync()
        self.save()
        print(f"Logged in as {self.user}")


intents = discord.Intents.default()
intents.message_content = True

bot = THGBot(intents=intents)

# Register inventory commands
register_inventory_commands(bot, bot.inventory)

# Register tribute commands
register_tribute_commands(bot, bot.db)


async def on_guild_join(guild):
    guild_id = str(guild.id)
    guild_prompts_dir = os.path.join(datadir, "prompt", str(guild_id))
    bot.config[guild_id] = {"log_channel_id": None, "category_id": None}
    bot.save()


@bot.tree.command(
    name="set-log-channel", description="Sets the channel for logs to be sent to"
)
async def set_log_channel(
    interaction: discord.Interaction,
    channel_id: Optional[str],
    channel_name: Optional[str],
):
    guild_id = str(interaction.guild.id)
    # Allows setting of log channel by channel id
    if channel_id:
        channel_id = channel_id.strip()
        if any(channel.id == int(channel_id) for channel in interaction.guild.channels):
            bot.config[guild_id]["log_channel_id"] = int(channel_id)
            log_channel = bot.get_channel(bot.config[guild_id]["log_channel_id"])
            bot.save()
            try:
                await interaction.response.send_message(
                    f'Log channel set to <#{bot.config[guild_id]["log_channel_id"]}>',
                    ephemeral=True,
                )
                log_embed = discord.Embed(
                    title=f'**Log channel set to <#{bot.config[guild_id]["log_channel_id"]}>**\n',
                    color=discord.Color.green(),
                )
                log_embed.set_author(
                    name=f"{interaction.user.name}",
                    icon_url=f"{interaction.user.avatar}",
                )
                if interaction.guild.icon != None:
                    log_embed.set_thumbnail(url=f"{interaction.guild.icon.url}")
                log_embed.timestamp = datetime.datetime.now()
                await log_channel.send(embed=log_embed)
            except Exception as e:
                await interaction.response.send_message(
                    "An error occured. Please try again."
                )
                print(f"Exception: {e}")
        else:
            try:
                await interaction.response.send_message(
                    "Channel not found", ephemeral=True
                )
            except Exception as e:
                await interaction.response.send_message(
                    "An error occured. Please try again."
                )
                print(f"Exception: {e}")
    # Allows setting of log channel by channel name
    elif channel_name:
        channel_name = channel_name.strip()
        for channel in interaction.guild.channels:
            if channel_name.lower() == channel.name.lower():
                bot.config[guild_id]["log_channel_id"] = channel.id
                log_channel = bot.get_channel(bot.config[guild_id]["log_channel_id"])
                try:
                    await interaction.response.send_message(
                        f'Log channel set to <#{bot.config[guild_id]["log_channel_id"]}>',
                        ephemeral=True,
                    )
                except Exception as e:
                    await interaction.response.send_message(
                        "An error occured. Please try again."
                    )
                    print(f"Exception: {e}")
                bot.save()
                sent = True
                break
        log_embed = discord.Embed(
            title=f'**Log channel set to <#{bot.config[guild_id]["log_channel_id"]}>**\n',
            color=discord.Color.green(),
        )
        log_embed.set_author(
            name=f"{interaction.user.name}", icon_url=f"{interaction.user.avatar}"
        )
        if interaction.guild.icon != None:
            log_embed.set_thumbnail(url=f"{interaction.guild.icon.url}")
        log_embed.timestamp = datetime.datetime.now()
        if not sent:
            try:
                await interaction.response.send_message(
                    "Channel not found", ephemeral=True
                )
            except Exception as e:
                await interaction.response.send_message(
                    "An error occured. Please try again."
                )
                print(f"Exception: {e}")
        else:
            await log_channel.send(embed=log_embed)
    else:
        try:
            await interaction.response.send_message(
                "Provide an argument", ephemeral=True
            )
        except Exception as e:
            await interaction.response.send_message(
                "An error occured. Please try again."
            )
            print(f"Exception: {e}")


@bot.tree.command(
    name="set-category", description="Sets the category for prompts to be sent to"
)
async def set_category(
    interaction: discord.Interaction,
    category_id: Optional[str],
    category_name: Optional[str],
):
    guild_id = str(interaction.guild.id)
    sent = False
    # Allows setting of category by category id
    if category_id:
        category_id = category_id.strip()
        if any(
            category.id == int(category_id) for category in interaction.guild.categories
        ):
            bot.config[guild_id]["category_id"] = int(category_id)
            log_channel = bot.get_channel(bot.config[guild_id]["log_channel_id"])
            bot.save()
            try:
                await interaction.response.send_message(
                    f'Prompt category set to <#{bot.config[guild_id]["category_id"]}>',
                    ephemeral=True,
                )
            except Exception as e:
                await interaction.response.send_message(
                    "An error occured. Please try again."
                )
                print(f"Exception: {e}")
            if bot.config[guild_id]["log_channel_id"]:
                log_embed = discord.Embed(
                    title=f"**Prompt category set to <#{bot.config[guild_id]['category_id']}>**\n",
                    color=discord.Color.green(),
                )
                log_embed.set_author(
                    name=f"{interaction.user.name}",
                    icon_url=f"{interaction.user.avatar}",
                )
                if interaction.guild.icon != None:
                    log_embed.set_thumbnail(url=f"{interaction.guild.icon.url}")
                log_embed.timestamp = datetime.datetime.now()
                await log_channel.send(embed=log_embed)
        else:
            try:
                await interaction.response.send_message(
                    "Category not found", ephemeral=True
                )
            except Exception as e:
                await interaction.response.send_message(
                    "An error occured. Please try again."
                )
                print(f"Exception: {e}")
    # Allows setting of category by category name
    elif category_name:
        category_name = category_name.strip()
        for category in interaction.guild.categories:
            if category_name.lower() == category.name.lower():
                bot.config[guild_id]["category_id"] = category.id
                log_channel = bot.get_channel(bot.config[guild_id]["log_channel_id"])
                bot.save()
                try:
                    await interaction.response.send_message(
                        f'Prompt category set to <#{bot.config[guild_id]["category_id"]}>',
                        ephemeral=True,
                    )
                except Exception as e:
                    await interaction.response.send_message(
                        "An error occured. Please try again."
                    )
                    print(f"Exception: {e}")
                sent = True
                break
        log_embed = discord.Embed(
            title=f"**Prompt category set to <#{bot.config[guild_id]['category_id']}>**\n",
            color=discord.Color.green(),
        )
        log_embed.set_author(
            name=f"{interaction.user.name}", icon_url=f"{interaction.user.avatar}"
        )
        if interaction.guild.icon != None:
            log_embed.set_thumbnail(url=f"{interaction.guild.icon.url}")
        log_embed.timestamp = datetime.datetime.now()
        if not sent:
            try:
                await interaction.response.send_message(
                    "Category not found", ephemeral=True
                )
            except Exception as e:
                await interaction.response.send_message(
                    "An error occured. Please try again."
                )
                print(f"Exception: {e}")
        else:
            await log_channel.send(embed=log_embed)


async def prompt_ids_list(
    interaction: discord.Interaction, embed_title: str, send_to: Optional[int]
):
    if bot.prompt_info:
        guild_id = str(interaction.guild.id)
        prompt_keys = []
        prompt_mentions = []
        channels = []
        for prompt_id in bot.prompt_info.keys():
            if interaction.guild.get_channel(
                int(bot.prompt_info[prompt_id]["channel"])
            ):
                prompt_keys.append(prompt_id)
                prompt_mentions.append(bot.prompt_info[prompt_id]["channel"])
                channels.append(
                    interaction.guild.get_channel(
                        int(bot.prompt_info[prompt_id]["channel"])
                    )
                )
        id_list_embed = discord.Embed(
            title=f"**{embed_title}**\n", color=discord.Color.green()
        )
        # Sorts channels in the view to be more readable
        prompt_keys = sorted(
            prompt_keys,
            key=lambda x: (
                (int(re.search(r"\d+", x).group()), x[-1])
                if re.search(r"\d+", x)
                else (float("inf"), x)
            ),
        )
        channels = sorted(channels, key=lambda ch: ch.position)
        if len(prompt_keys) > 0:
            id_list_embed.add_field(
                name="**Prompt IDs**",
                value=f"**{"\n".join(prompt_keys)}**",
                inline=True,
            )
            id_list_embed.add_field(
                name="**Prompt channels**",
                value=f"{'\n'.join(ch.mention for ch in channels)}",
                inline=True,
            )
            id_list_embed.set_author(
                name=f"{interaction.user.name}", icon_url=f"{interaction.user.avatar}"
            )
            id_list_embed.set_thumbnail(url=f"{interaction.user.avatar}")
            id_list_embed.timestamp = datetime.datetime.now()
            if send_to == bot.config[guild_id]["log_channel_id"]:
                if interaction.response.is_done():
                    await interaction.guild.get_channel(send_to).send(
                        embed=id_list_embed
                    )
                else:
                    await interaction.guild.get_channel(send_to).send(
                        embed=id_list_embed
                    )
            else:
                if interaction.response.is_done():
                    await interaction.followup.send(embed=id_list_embed, ephemeral=True)
                else:
                    await interaction.response.send_message(
                        embed=id_list_embed, ephemeral=True
                    )
        else:
            await interaction.response.send_message(
                "No prompts found in guild.", ephemeral=True
            )
    else:
        await interaction.response.send_message("No prompts found", ephemeral=True)


@bot.tree.command(name="view-prompt-ids", description="Lists all tributes with prompts")
async def view_prompt_ids(interaction: discord.Interaction):
    await interaction.response.defer(ephemeral=True)
    guild_id = interaction.guild.id if interaction.guild else None
    tributes = bot.db.get_all_tributes(guild_id=guild_id)

    tribute_ids = []
    for tribute in tributes:
        tribute_id = tribute.get("tribute_id")
        prompt_data = bot.storage.get_prompt(tribute_id)
        if prompt_data:
            channel_id = prompt_data.get("channel_id") or prompt_data.get("channel")
            if channel_id and interaction.guild.get_channel(int(channel_id)):
                tribute_ids.append(f"{tribute_id} - <#{channel_id}>")

    if not tribute_ids:
        await interaction.followup.send("No prompts found.", ephemeral=True)
        return

    embed = discord.Embed(
        title="Tributes with Prompts",
        description="\n".join(tribute_ids),
        color=discord.Color.blue(),
    )
    await interaction.followup.send(embed=embed, ephemeral=True)


@bot.tree.command(name="view-prompt", description="View a tribute's prompt")
async def viewPrompt(interaction: discord.Interaction, tribute_id: str):
    tribute_id = tribute_id.strip().upper()
    guild_id = str(interaction.guild.id)

    prompt_data = bot.storage.get_prompt(tribute_id)
    if not prompt_data:
        await interaction.response.send_message(
            f"No prompt found for {tribute_id}", ephemeral=True
        )
        return

    channel_id = prompt_data.get("channel_id") or prompt_data.get("channel")
    if not channel_id or not interaction.guild.get_channel(int(channel_id)):
        await interaction.response.send_message(
            "Channel not found for this prompt", ephemeral=True
        )
        return

    message = prompt_data.get("message", "")
    messages = split_message(message)
    if messages:
        await interaction.response.send_message(messages[0], ephemeral=True)
        for msg in messages[1:]:
            await interaction.followup.send(msg, ephemeral=True)
    else:
        await interaction.response.send_message("Prompt is empty", ephemeral=True)


"""
Old save-prompt command - replaced by tributecommands.save_prompt with tribute_id
@bot.tree.command(name="save-prompt", description="Stores prompt info using a modal UI")
async def save_prompt(
    interaction: discord.Interaction, file: Optional[discord.Attachment]
):
    guild_id = str(interaction.guild.id)
    try:
        if not file:
            modal = PromptModal(interaction, bot)
            await interaction.response.send_modal(modal)
        elif (
            file.filename.lower().endswith(".png")
            or file.filename.lower().endswith(".jpg")
            or file.filename.lower().endswith(".jpeg")
            or file.filename.lower().endswith(".webp")
            or file.filename.lower().endswith(".webm")
            or file.filename.lower().endswith(".mp3")
        ):
            modal = PromptModal(interaction, bot, file)
            await interaction.response.send_modal(modal)
        else:
            await interaction.response.send_message(
                "Please upload a .png, .jpg, .jpeg, .webp, or .webm file."
            )
        return
    except Exception as e:
        await interaction.response.send_message("An error occured. Please try again.")
        print(f"Error: {e}")
"""


@bot.tree.command(
    name="add-to-prompt", description="Adds content to a prompt using a modal UI"
)
async def add_to_prompt(interaction: discord.Interaction):
    guild_id = str(interaction.guild.id)
    try:
        modal = AddToPromptModal(interaction, bot)
        await interaction.response.send_modal(modal)
    except Exception as e:
        await interaction.response.send_message("An error occured. Please try again.")
        print(f"Error: {e}")


@bot.tree.command(name="send-prompt", description="Send a prompt")
async def sendPrompt(interaction: discord.Interaction, tribute_id: str):
    # Sends the prompt for a tribute
    await interaction.response.defer(ephemeral=True)

    tribute_id = tribute_id.strip().upper()
    guild_id = str(interaction.guild.id)

    # Get prompt from storage
    prompt_data = bot.storage.get_prompt(tribute_id)
    if not prompt_data:
        await interaction.followup.send(
            f"Prompt not found for tribute {tribute_id}", ephemeral=True
        )
        return

    channel_id = prompt_data.get("channel_id") or prompt_data.get("channel")
    if not channel_id:
        await interaction.followup.send(
            f"No channel specified for prompt {tribute_id}", ephemeral=True
        )
        return

    channel = interaction.guild.get_channel(int(channel_id))
    if not channel:
        await interaction.followup.send("Channel not found", ephemeral=True)
        return

    try:
        log_channel = bot.get_channel(bot.config[guild_id]["log_channel_id"])
        log_embed = discord.Embed(
            title=f"{tribute_id} prompt sent to {channel.mention}",
            color=discord.Color.green(),
        )
        log_embed.set_author(
            name=f"{interaction.user.name}", icon_url=f"{interaction.user.avatar}"
        )
        if interaction.guild.icon:
            log_embed.set_thumbnail(url=f"{interaction.guild.icon.url}")
        log_embed.timestamp = datetime.datetime.now()

        message_text = prompt_data.get("message", "")
        if not message_text:
            await interaction.followup.send("Prompt message is empty", ephemeral=True)
            return

        messages = split_message(message_text)
        first_message = True
        for msg in messages:
            message = await channel.send(msg)
            if first_message:
                await message.pin()
                first_message = False
                async for message in channel.history(limit=3):
                    if message.type == discord.MessageType.pins_add:
                        async for entry in message.guild.audit_logs(
                            limit=1, action=discord.AuditLogAction.message_pin
                        ):
                            if entry.user.id == bot.user.id:
                                await message.delete()
                                break
                        break

        await interaction.followup.send(
            f"Prompt {tribute_id} sent in channel {channel.mention}", ephemeral=True
        )
        await log_channel.send(embed=log_embed)

        # Send inventory alongside the prompt
        try:
            # Get tribute name for display
            tribute_data = bot.db.get_tribute(tribute_id)
            tribute_name = (
                tribute_data.get("tribute_name", tribute_id)
                if tribute_data
                else tribute_id
            )

            inventory_data = bot.storage.get_inventory(tribute_id)
            if inventory_data:
                items = inventory_data.get("items", {})
                equipped = inventory_data.get("equipped", {})
                capacity = inventory_data.get("capacity", 10)
                equipped_capacity = inventory_data.get("equipped_capacity", 5)

                # Only send if there are items or equipped items
                if items or equipped:
                    inventory_embed = _format_inventory_embed(
                        tribute_id=tribute_id,
                        items=items,
                        capacity=capacity,
                        equipped=equipped,
                        equipped_capacity=equipped_capacity,
                        title="Inventory:",
                        tribute_name=tribute_name,
                    )
                    await channel.send(embed=inventory_embed)
        except Exception as e:
            print(f"Failed to send inventory for {tribute_id}: {e}")

    except Exception as e:
        await interaction.followup.send(
            f"Error sending prompt: {str(e)}", ephemeral=True
        )


@bot.tree.command(name="send-all-prompts", description="Send all prompts")
async def sendAllPrompts(interaction: discord.Interaction):
    # Sends all the prompts
    confirmSend = ConfirmationView()
    length = 0
    prompts_to_del = []
    for prompt_id in bot.prompt_info.keys():
        if interaction.guild.get_channel(int(bot.prompt_info[prompt_id]["channel"])):
            length += 1
    await interaction.response.send_message(
        f"There are {length} prompts saved. Are you sure you want to send all prompts? This will also clear them from the list.",
        ephemeral=True,
        view=confirmSend,
    )
    await confirmSend.wait()
    guild_id = str(interaction.guild.id)
    prompt_keys = []
    prompt_mentions = []
    log_channel = bot.config[guild_id]["log_channel_id"]
    for prompt_id in bot.prompt_info.keys():
        if interaction.guild.get_channel(int(bot.prompt_info[prompt_id]["channel"])):
            prompt_keys.append(prompt_id)
            prompt_mentions.append(f"<#{bot.prompt_info[prompt_id]['channel']}>")

    if confirmSend.confirmed:
        prompts_to_del = await send_all_prompts_concurrent(
            bot, interaction, guild_id, prompt_image_dir, storage=bot.storage
        )

        if len(prompt_keys) > 0:
            await prompt_ids_list(interaction, "All prompts send", log_channel)

        for prompt_id in prompts_to_del:
            del bot.prompt_info[prompt_id]

        msg = await interaction.original_response()
        await msg.edit(content="All prompts sent.")
        bot.save()
    else:
        msg = await interaction.original_response()
        await msg.edit(content="Cancelled sending all prompts.")
        """for prompt_id in bot.prompt_info.keys():
            if interaction.guild.get_channel(
                int(bot.prompt_info[prompt_id]["channel"])
            ):
                channel_id = bot.prompt_info[prompt_id]["channel"]
                channel = interaction.guild.get_channel(int(channel_id))
                if channel:
                    try:
                        message = bot.prompt_info[prompt_id]["message"]
                        messages = split_message(message)
                        first_message = True
                        for msg in messages:
                            pin_message = await channel.send(msg)
                            if first_message:
                                await pin_message.pin()
                                first_message = False
                                async for message in channel.history(limit=3):
                                    if message.type == discord.MessageType.pins_add:
                                        # Get the audit log to see who pinned
                                        async for entry in message.guild.audit_logs(
                                            limit=1,
                                            action=discord.AuditLogAction.message_pin,
                                        ):
                                            if entry.user.id == bot.user.id:
                                                await message.delete()
                                                break
                                        break
                        if "image" in bot.prompt_info[prompt_id].keys():
                            if isinstance(bot.prompt_info[prompt_id]["image"], list):
                                for image in bot.prompt_info[prompt_id]["image"]:
                                    file_name = image
                                    file_path = os.path.join(
                                        prompt_image_dir, guild_id, file_name
                                    )
                                    if os.path.exists(file_path):
                                        await channel.send(file=discord.File(file_path))
                                        try:
                                            os.unlink(file_path)
                                        except FileNotFoundError:
                                            pass
                                    else:
                                        await interaction.followup.send(
                                            "File is missing, please reattach the file.",
                                            ephemeral=True,
                                        )
                            else:
                                file_name = bot.prompt_info[prompt_id]["image"]
                                file_path = os.path.join(
                                    prompt_image_dir, guild_id, file_name
                                )
                                if os.path.exists(file_path):
                                    await channel.send(file=discord.File(file_path))
                                    try:
                                        os.unlink(file_path)
                                    except FileNotFoundError:
                                        pass
                                else:
                                    await interaction.followup.send(
                                        "File is missing, please reattach the file.",
                                        ephemeral=True,
                                    )
                    except discord.Forbidden:
                        await interaction.followup.send(
                            f"The bot doesn't have permission to send files in {channel.name}"
                        )
                        print(f"Forbidden to send messages to {channel.name}")
                    except discord.HTTPException as e:
                        print(
                            f"HTTP exception while sending message to {channel.name}: {e}"
                        )
                else:
                    await interaction.followup.send(f"Channel {channel} does not exit")
                    print(f"Channel {channel} does not exist")
                    pass
                prompts_to_del.append(prompt_id)

        if len(prompt_keys) > 0:
            await prompt_ids_list(interaction, "All prompts sent", log_channel)

        for prompt_id in prompts_to_del:
            del bot.prompt_info[prompt_id]

        msg = await interaction.original_response()
        await msg.edit(content="All prompts sent.")
        bot.save()
    else:
        msg = await interaction.original_response()
        await msg.edit(content="Cancelled sending all prompts!")"""


@bot.tree.command(name="clear-all-prompts", description="Clear all prompts")
async def clearAllPrompts(interaction: discord.Interaction):
    """Clear all prompts from all tributes in the guild."""
    await interaction.response.defer(ephemeral=True)
    
    try:
        guild_id = interaction.guild.id if interaction.guild else None
        tributes = bot.db.get_all_tributes(guild_id=guild_id)
        
        # Count valid prompts to clear
        tributes_with_prompts = []
        for tribute in tributes:
            tribute_id = tribute.get('tribute_id')
            prompt_data = bot.storage.get_prompt(tribute_id)
            if prompt_data:
                channel_id = prompt_data.get('channel_id') or prompt_data.get('channel')
                if channel_id and interaction.guild.get_channel(int(channel_id)):
                    tributes_with_prompts.append(tribute_id)
        
        if not tributes_with_prompts:
            await interaction.followup.send("No prompts found to clear.", ephemeral=True)
            return
        
        # Ask for confirmation
        confirmSend = ConfirmationView()
        await interaction.followup.send(
            f"There are {len(tributes_with_prompts)} prompts saved. Are you sure you want to delete all prompts?",
            ephemeral=True,
            view=confirmSend,
        )
        await confirmSend.wait()
        
        if confirmSend.confirmed:
            # Delete all prompts
            for tribute_id in tributes_with_prompts:
                bot.storage.delete_prompt(tribute_id)
                bot.db.delete_prompt(tribute_id)
            
            # Log the action
            guild_id_str = str(interaction.guild.id)
            if guild_id_str in bot.config and bot.config[guild_id_str].get("log_channel_id"):
                log_channel = bot.get_channel(bot.config[guild_id_str]["log_channel_id"])
                if log_channel:
                    log_embed = discord.Embed(
                        title="All prompts cleared.",
                        color=discord.Color.red()
                    )
                    log_embed.add_field(
                        name="Tribute IDs",
                        value="\n".join(tributes_with_prompts),
                        inline=False
                    )
                    log_embed.set_author(
                        name=f"{interaction.user.name}",
                        icon_url=f"{interaction.user.avatar}"
                    )
                    if interaction.guild.icon:
                        log_embed.set_thumbnail(url=f"{interaction.guild.icon.url}")
                    log_embed.timestamp = discord.utils.utcnow()
                    await log_channel.send(embed=log_embed)
            
            msg = await interaction.original_response()
            await interaction.followup.edit_message(msg.id, content="✅ All prompts cleared.", view=confirmSend)
        else:
            msg = await interaction.original_response()
            await interaction.followup.edit_message(msg.id, content="❌ Cancelled clearing all prompts.", view=confirmSend)
    except Exception as e:
        print(f"Error clearing all prompts: {e}")
        await interaction.followup.send("Error clearing prompts.", ephemeral=True)


@bot.tree.command(name="clear-prompt", description="Clear a specific prompt")
async def clear_prompt(interaction: discord.Interaction, tribute_id: str):
    """Clear prompt for a specific tribute."""
    await interaction.response.defer(ephemeral=True)
    
    tribute_id = tribute_id.strip().upper()
    
    try:
        # Check if prompt exists
        prompt_data = bot.storage.get_prompt(tribute_id)
        if not prompt_data:
            await interaction.followup.send(
                f"No prompt found for tribute `{tribute_id}`.", ephemeral=True
            )
            return
        
        # Ask for confirmation
        confirmSend = ConfirmationView()
        await interaction.followup.send(
            f"Are you sure you want to delete the {tribute_id} prompt?",
            ephemeral=True,
            view=confirmSend,
        )
        await confirmSend.wait()
        
        if confirmSend.confirmed:
            # Delete the prompt from storage and database
            bot.storage.delete_prompt(tribute_id)
            bot.db.delete_prompt(tribute_id)
            
            # Log the action
            guild_id = str(interaction.guild.id)
            if guild_id in bot.config and bot.config[guild_id].get("log_channel_id"):
                log_channel = bot.get_channel(bot.config[guild_id]["log_channel_id"])
                if log_channel:
                    log_embed = discord.Embed(
                        title=f"{tribute_id} prompt cleared.",
                        color=discord.Color.red()
                    )
                    log_embed.set_author(
                        name=f"{interaction.user.name}",
                        icon_url=f"{interaction.user.avatar}"
                    )
                    if interaction.guild.icon:
                        log_embed.set_thumbnail(url=f"{interaction.guild.icon.url}")
                    log_embed.timestamp = discord.utils.utcnow()
                    await log_channel.send(embed=log_embed)
            
            msg = await interaction.original_response()
            await interaction.followup.edit_message(msg.id, content=f"✅ Prompt for {tribute_id} cleared.", view=confirmSend)
        else:
            msg = await interaction.original_response()
            await interaction.followup.edit_message(msg.id, content=f"❌ Cancelled clearing the {tribute_id} prompt.", view=confirmSend)
    except Exception as e:
        print(f"Error clearing prompt for {tribute_id}: {e}")
        await interaction.followup.send("Error clearing prompt.", ephemeral=True)


@bot.tree.command(
    name="add-file", description="Add a file to a specific tribute's prompt."
)
async def add_file(
    interaction: discord.Interaction, tribute_id: str, file: discord.Attachment
):
    await interaction.response.defer(ephemeral=True)

    tribute_id = tribute_id.strip().upper()
    guild_id = str(interaction.guild.id)

    # Check if prompt exists
    prompt_data = bot.storage.get_prompt(tribute_id)
    if not prompt_data:
        await interaction.followup.send(
            f"Prompt not found for tribute `{tribute_id}`. Please create the prompt first.",
            ephemeral=True,
        )
        return

    # Validate file type
    if not (
        file.filename.endswith(".png")
        or file.filename.endswith(".jpg")
        or file.filename.endswith(".jpeg")
        or file.filename.endswith(".webp")
        or file.filename.endswith(".webm")
        or file.filename.endswith(".mp3")
    ):
        await interaction.followup.send(
            "Please upload a .png, .jpeg, .jpg, .webm, .webp, or .mp3 file.",
            ephemeral=True,
        )
        return

    # Prepare file directory
    file_dir = os.path.join(bot.prompt_image_dir, guild_id)
    os.makedirs(file_dir, exist_ok=True)

    # Save the file
    file_extension = os.path.splitext(file.filename)[1]
    new_filename = f"{tribute_id}_{int(time.time())}{file_extension}"
    file_path = os.path.join(file_dir, new_filename)

    try:
        await file.save(file_path)

        await interaction.followup.send(
            f"✅ File added to prompt `{tribute_id}`.", ephemeral=True
        )

        # Log the file addition
        if guild_id in bot.config and bot.config[guild_id].get("log_channel_id"):
            log_channel = bot.get_channel(bot.config[guild_id]["log_channel_id"])
            if log_channel:
                log_embed = discord.Embed(
                    title=f"File added to {tribute_id}",
                    description=f"File: {file.filename}",
                    color=discord.Color.green(),
                )
                log_embed.set_author(
                    name=f"{interaction.user.name}", icon_url=f"{interaction.user.avatar}"
                )
                log_embed.timestamp = discord.utils.utcnow()
                await log_channel.send(embed=log_embed)
    except Exception as e:
        await interaction.followup.send(
            f"Error uploading file: {str(e)}", ephemeral=True
        )
        print(f"Error uploading file: {e}")


bot.run(token)
