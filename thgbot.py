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
from inventory_commands import InventoryCog
import os
import sys
from typing import Optional
import datetime
import json
import asyncio
import re

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
        self.inventory = Inventory(datadir)
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
        if not hasattr(self, '_inventory_cog_loaded'):
            await self.add_cog(InventoryCog(self, self.inventory))
            self._inventory_cog_loaded = True
        self.save()
        print(f"Logged in as {self.user}")


intents = discord.Intents.default()
intents.message_content = True

bot = THGBot(intents=intents)


@bot.event
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


@bot.tree.command(name="view-prompt-ids", description="Lists all prompt_ids")
async def view_prompt_ids(interaction: discord.Interaction):
    await prompt_ids_list(interaction, "Prompts", None)


@bot.tree.command(name="view-prompt", description="View a prompt")
async def viewPrompt(interaction: discord.Interaction, prompt_id: str):
    prompt_id = prompt_id.upper().strip().replace(" ", "_")
    guild_id = str(interaction.guild.id)
    if prompt_id in bot.prompt_info.keys() and interaction.guild.get_channel(
        int(bot.prompt_info[prompt_id]["channel"])
    ):
        message = bot.prompt_info[prompt_id]["message"]
        messages = split_message(message)
        if messages:
            await interaction.response.send_message(messages[0], ephemeral=True)
            for msg in messages[1:]:
                await interaction.followup.send(msg, ephemeral=True)
            if "image" in bot.prompt_info[prompt_id].keys():
                if isinstance(bot.prompt_info[prompt_id]["image"], list):
                    for image in bot.prompt_info[prompt_id]["image"]:
                        file_name = image
                        file_path = os.path.join(prompt_image_dir, guild_id, file_name)
                        if os.path.exists(file_path):
                            await interaction.followup.send(
                                file=discord.File(file_path), ephemeral=True
                            )
                        else:
                            await interaction.followup.send(
                                "File is missing, please reattach the file.",
                                ephemeral=True,
                            )
                else:
                    file_name = bot.prompt_info[prompt_id]["image"]
                    file_path = os.path.join(prompt_image_dir, guild_id, file_name)
                    if os.path.exists(file_path):
                        await interaction.followup.send(
                            file=discord.File(file_path), ephemeral=True
                        )
                    else:
                        await interaction.followup.send(
                            "File is missing, please reattach the file.", ephemeral=True
                        )
        else:
            await interaction.response.send_message("Prompt is empty", ephemeral=True)
    else:
        await interaction.response.send_message("Prompt not found", ephemeral=True)


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
async def sendPrompt(interaction: discord.Interaction, prompt_id: str):
    # Sends the prompt
    prompt_id = prompt_id.strip().upper()
    guild_id = str(interaction.guild.id)
    if prompt_id in bot.prompt_info and interaction.guild.get_channel(
        int(bot.prompt_info[prompt_id]["channel"])
    ):
        channel = interaction.guild.get_channel(
            int(bot.prompt_info[prompt_id]["channel"])
        )
        log_channel = bot.get_channel(bot.config[guild_id]["log_channel_id"])
        log_embed = discord.Embed(
            title=f"{prompt_id} prompt sent to {channel.mention}",
            color=discord.Color.green(),
        )
        log_embed.set_author(
            name=f"{interaction.user.name}", icon_url=f"{interaction.user.avatar}"
        )
        if interaction.guild.icon != None:
            log_embed.set_thumbnail(url=f"{interaction.guild.icon.url}")
        log_embed.timestamp = datetime.datetime.now()
        if channel:
            message = bot.prompt_info[prompt_id]["message"]
            messages = split_message(message)
            first_message = True
            for msg in messages:
                message = await channel.send(msg)
                if first_message:
                    await message.pin()
                    first_message = False
                    async for message in channel.history(limit=3):
                        if message.type == discord.MessageType.pins_add:
                            # Get the audit log to see who pinned
                            async for entry in message.guild.audit_logs(
                                limit=1, action=discord.AuditLogAction.message_pin
                            ):
                                if entry.user.id == bot.user.id:
                                    await message.delete()
                                    break
                            break

            if "image" in bot.prompt_info[prompt_id].keys():
                if isinstance(bot.prompt_info[prompt_id]["image"], list):
                    for image in bot.prompt_info[prompt_id]["image"]:
                        file_name = image
                        file_path = os.path.join(prompt_image_dir, guild_id, file_name)
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
                    file_path = os.path.join(prompt_image_dir, guild_id, file_name)
                    if os.path.exists(file_path):
                        await channel.send(file=discord.File(file_path))
                        try:
                            os.unlink(file_path)
                        except FileNotFoundError:
                            pass
                    else:
                        await interaction.followup.send(
                            "File is missing, please reattach the file.", ephemeral=True
                        )
            await interaction.response.send_message(
                f"Prompt {prompt_id} sent in channel {channel.mention}", ephemeral=True
            )
            await log_channel.send(embed=log_embed)
            del bot.prompt_info[prompt_id]
            bot.save()
    else:
        await interaction.response.send_message("Prompt not found")


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
            bot, interaction, guild_id, prompt_image_dir
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
    # Clears all the prompts
    try:
        confirmSend = ConfirmationView()
        length = 0
        for prompt_id in bot.prompt_info.keys():
            if interaction.guild.get_channel(
                int(bot.prompt_info[prompt_id]["channel"])
            ):
                length += 1
        await interaction.response.send_message(
            f"There are {length} prompts saved. Are you sure you want to delete all prompts?",
            ephemeral=True,
            view=confirmSend,
        )
        await confirmSend.wait()

        prompts_to_del = []
        guild_id = str(interaction.guild.id)
        prompt_keys = []
        prompt_mentions = []
        for prompt_id in bot.prompt_info.keys():
            if interaction.guild.get_channel(
                int(bot.prompt_info[prompt_id]["channel"])
            ):
                prompt_keys.append(prompt_id)
                prompt_mentions.append(f"<#{bot.prompt_info[prompt_id]['channel']}>")

        log_channel = bot.get_channel(bot.config[guild_id]["log_channel_id"])
        if length > 0:
            log_embed = discord.Embed(
                title=f"All prompts cleared.", color=discord.Color.red()
            )
            log_embed.add_field(
                name="Prompt IDs", value=f"**{"\n".join(prompt_keys)}**", inline=True
            )
            log_embed.add_field(
                name="Prompt channels",
                value=f"{'\n'.join(prompt_mentions)}",
                inline=True,
            )
            log_embed.set_author(
                name=f"{interaction.user.name}", icon_url=f"{interaction.user.avatar}"
            )
            if interaction.guild.icon != None:
                log_embed.set_thumbnail(url=f"{interaction.guild.icon.url}")
            log_embed.timestamp = datetime.datetime.now()

        if confirmSend.confirmed:
            for prompt_id in bot.prompt_info.keys():
                if interaction.guild.get_channel(
                    int(bot.prompt_info[prompt_id]["channel"])
                ):
                    prompts_to_del.append(prompt_id)

            for prompt_id in prompts_to_del:
                if "image" in bot.prompt_info[prompt_id].keys():
                    if isinstance(bot.prompt_info[prompt_id]["image"], list):
                        for image in bot.prompt_info[prompt_id]["image"]:
                            file_name = image
                            file_path = os.path.join(
                                prompt_image_dir, guild_id, file_name
                            )
                            try:
                                os.unlink(file_path)
                            except FileNotFoundError:
                                pass
                    else:
                        file_name = bot.prompt_info[prompt_id]["image"]
                        file_path = os.path.join(prompt_image_dir, guild_id, file_name)
                        try:
                            os.unlink(file_path)
                        except FileNotFoundError:
                            pass
                del bot.prompt_info[prompt_id]
            bot.save()
            msg = await interaction.original_response()
            await interaction.followup.edit_message(
                msg.id, content="Prompts cleared", view=confirmSend
            )
            await log_channel.send(embed=log_embed)
        else:
            await interaction.followup.send("Cancelled clearing all prompts!")
    except Exception as e:
        print(e)
        await interaction.response.send_message("Prompts not cleared", ephemeral=True)


@bot.tree.command(name="clear-prompt", description="Clear a specific prompt")
async def clear_prompt(interaction: discord.Interaction, prompt_id: str):
    # Clears a specific prompt
    prompt_id_key = prompt_id.upper().strip().replace(" ", "_")
    if prompt_id_key in bot.prompt_info.keys():
        confirmSend = ConfirmationView()
        await interaction.response.send_message(
            f"Are you sure you want to delete the {prompt_id_key} prompt?",
            ephemeral=True,
            view=confirmSend,
        )
        await confirmSend.wait()

        guild_id = str(interaction.guild.id)
        log_channel = bot.get_channel(bot.config[guild_id]["log_channel_id"])
        log_embed = discord.Embed(
            title=f"{prompt_id_key} prompt cleared.", color=discord.Color.red()
        )
        log_embed.set_author(
            name=f"{interaction.user.name}", icon_url=f"{interaction.user.avatar}"
        )
        if interaction.guild.icon != None:
            log_embed.set_thumbnail(url=f"{interaction.guild.icon.url}")
        log_embed.timestamp = datetime.datetime.now()

        if confirmSend.confirmed:
            if "image" in bot.prompt_info[prompt_id_key].keys():
                if isinstance(bot.prompt_info[prompt_id_key]["image"], list):
                    for image in bot.prompt_info[prompt_id_key]["image"]:
                        file_name = bot.prompt_info[prompt_id_key]["image"]
                        file_path = os.path.join(prompt_image_dir, guild_id, file_name)
                        try:
                            os.unlink(file_path)
                        except FileNotFoundError:
                            pass
                else:
                    file_name = bot.prompt_info[prompt_id_key]["image"]
                    file_path = os.path.join(prompt_image_dir, guild_id, file_name)
                    try:
                        os.unlink(file_path)
                    except FileNotFoundError:
                        pass
            del bot.prompt_info[prompt_id_key]
            bot.save()
            msg = await interaction.original_response()
            await interaction.followup.edit_message(
                msg.id, content=f"Prompt {prompt_id_key} cleared.", view=confirmSend
            )
            await log_channel.send(embed=log_embed)
        else:
            msg = await interaction.original_response()
            await interaction.followup.edit_message(
                msg.id,
                content=f"Cancelled clearing the {prompt_id_key} prompt!",
                view=confirmSend,
            )
    else:
        await interaction.response.send_message(
            "This prompt was not found in this server.", ephemeral=True
        )


@bot.tree.command(name="add-file", description="Add a file to a specific prompt.")
async def add_file(
    interaction: discord.Interaction, prompt_id: str, file: discord.Attachment
):
    # Add a file to an existing prompt without overwriting

    await interaction.response.defer(ephemeral=True)

    guild_id = str(interaction.guild.id)
    prompt_id = prompt_id.upper().strip()

    # Check if prompt exists
    if prompt_id not in bot.prompt_info:
        await interaction.followup.send(
            f"Prompt ID `{prompt_id}` not found. Please create the prompt first.",
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
    file_dir = os.path.join(prompt_image_dir, guild_id)
    os.makedirs(file_dir, exist_ok=True)

    # Handle multiple files by using a list or numbering system
    if "image" in bot.prompt_info[prompt_id]:
        # If there's already an image, convert to list format
        existing_image = bot.prompt_info[prompt_id]["image"]

        # Check if it's already a list
        if isinstance(existing_image, list):
            images = existing_image
        else:
            # Convert single image to list
            images = [existing_image]

        # Generate unique filename
        file_extension = os.path.splitext(file.filename)[1]
        file_number = len(images)
        new_filename = f"{prompt_id}_{file_number}{file_extension}"
        file_path = os.path.join(file_dir, new_filename)

        # Save the file
        await file.save(file_path)

        # Add to list
        images.append(new_filename)
        bot.prompt_info[prompt_id]["image"] = images
    else:
        # First image for this prompt
        file_extension = os.path.splitext(file.filename)[1]
        new_filename = f"{prompt_id}{file_extension}"
        file_path = os.path.join(file_dir, new_filename)

        # Save the file
        await file.save(file_path)
        bot.prompt_info[prompt_id]["image"] = new_filename

    # Save to persistent storage
    bot.save()

    # Log to log channel
    if "log_channel_id" in bot.config[guild_id]:
        log_channel = bot.get_channel(bot.config[guild_id]["log_channel_id"])
        if log_channel:
            log_embed = discord.Embed(
                title=f"File added to {prompt_id}",
                description=f"Added: `{new_filename if 'new_filename' in locals() else file.filename}`",
                color=discord.Color.green(),
            )
            log_embed.set_author(
                name=interaction.user.name,
                icon_url=(
                    interaction.user.avatar.url if interaction.user.avatar else None
                ),
            )
            log_embed.timestamp = discord.utils.utcnow()
            await log_channel.send(embed=log_embed)
            await log_channel.send(file=await file.to_file())

    # Confirm to user
    file_count = (
        len(bot.prompt_info[prompt_id]["image"])
        if isinstance(bot.prompt_info[prompt_id].get("image"), list)
        else 1
    )
    await interaction.followup.send(
        f"{new_filename} added to prompt `{prompt_id}`. This prompt now has {file_count} file(s).",
        ephemeral=True,
    )


bot.run(token)
