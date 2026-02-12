import discord
from promptview import PromptView
from utils import split_message
import datetime
import os
import asyncio

try:
    datadir = os.environ["SNAP_DATA"]
except:
    print("SNAP_DATA must be set")

prompt_image_dir = os.path.join(datadir, "prompt_images")


def segment_message(message: str, max_length: int = 4000) -> list:
    """
    Segment a message into chunks, ensuring INVENTORY section stays together.

    Args:
        message: The full message to segment
        max_length: Maximum length of each segment (default 4000)

    Returns:
        List of message segments
    """
    # Check if message has an INVENTORY section
    inventory_match = message.find("EQUIPPED")

    if inventory_match == -1:
        # No INVENTORY section, split normally
        segments = []
        for i in range(0, len(message), max_length):
            segments.append(message[i : i + max_length])
        return segments

    # INVENTORY section exists
    before_inventory = message[:inventory_match]
    inventory_section = message[inventory_match:]

    segments = []

    # Split the part before INVENTORY normally
    if before_inventory:
        for i in range(0, len(before_inventory), max_length):
            segments.append(before_inventory[i : i + max_length])

    # Keep INVENTORY section together (even if it exceeds max_length)
    if len(inventory_section) <= max_length:
        # INVENTORY fits in one segment
        # Check if we can append it to the last segment
        if segments and len(segments[-1]) + len(inventory_section) <= max_length:
            segments[-1] += inventory_section
        else:
            segments.append(inventory_section)
    else:
        # INVENTORY section is too long for one segment, but keep it as one anyway
        # This prevents splitting it mid-content
        segments.append(inventory_section)

    return segments


class EditPromptMessageModal(discord.ui.Modal):
    """Modal for editing the prompt message text"""

    def __init__(
        self,
        prompt_id: str,
        current_message: str,
        bot,
        segment_index: int = None,
        all_segments: list = None,
        parent_view=None,
    ) -> None:
        super().__init__(
            title=f"Edit {prompt_id} Message"
            + (f" - Segment {segment_index + 1}" if segment_index is not None else "")
        )
        self.prompt_id = prompt_id
        self.bot = bot
        self.segment_index = segment_index
        self.all_segments = all_segments
        self.parent_view = parent_view  # Reference to the MessageSegmentView

        # Add text input with current message as default
        self.add_item(
            discord.ui.TextInput(
                label="Prompt Message"
                + (
                    f" (Segment {segment_index + 1}/{len(all_segments)})"
                    if segment_index is not None
                    else ""
                ),
                placeholder="Enter the new prompt message",
                custom_id="prompt_message",
                style=discord.TextStyle.paragraph,
                default=current_message,
                max_length=4000,
            )
        )

    async def on_submit(self, interaction: discord.Interaction):
        new_message = self.children[0].value

        if not new_message:
            await interaction.response.send_message(
                "Prompt message cannot be empty", ephemeral=True
            )
            return

        # If this is a segment edit, reassemble the full message
        if self.segment_index is not None:
            self.all_segments[self.segment_index] = new_message
            final_message = "\n".join(self.all_segments)

            # Update the parent view's segments so subsequent edits use the updated version
            if self.parent_view:
                self.parent_view.segments = self.all_segments
        else:
            final_message = new_message

        # Update the prompt message
        self.bot.prompt_info[self.prompt_id]["message"] = final_message
        self.bot.save()

        # Log the change
        guild_id = str(interaction.guild.id)
        log_channel = self.bot.get_channel(self.bot.config[guild_id]["log_channel_id"])

        log_embed = discord.Embed(
            title=f"{self.prompt_id} message updated"
            + (
                f" (Segment {self.segment_index + 1})"
                if self.segment_index is not None
                else ""
            ),
            color=discord.Color.blue(),
        )
        log_embed.set_author(
            name=interaction.user.name,
            icon_url=interaction.user.avatar.url if interaction.user.avatar else None,
        )
        if interaction.guild.icon:
            log_embed.set_thumbnail(url=interaction.guild.icon.url)
        log_embed.timestamp = datetime.datetime.now()

        if log_channel:
            await log_channel.send(embed=log_embed)
            messages = split_message(final_message)
            for message in messages:
                await log_channel.send(message)

        if self.segment_index is not None:
            await interaction.response.send_message(
                f"✅ Segment {self.segment_index + 1} updated for prompt `{self.prompt_id}`.\n"
                f"Total message length: {len(final_message)} characters",
                ephemeral=True,
            )
        else:
            await interaction.response.send_message(
                f"✅ Message for prompt `{self.prompt_id}` has been updated.",
                ephemeral=True,
            )


class EditPromptChannelView(discord.ui.View):
    """View for editing the channel a prompt will be sent to"""

    def __init__(self, prompt_id: str, channels: list, bot):
        super().__init__(timeout=30)
        self.prompt_id = prompt_id
        self.bot = bot
        self.channels = channels
        self.channel_id = None
        self.finished = False

        # Add channel selector
        self.channel_select = discord.ui.ChannelSelect(
            placeholder="Select a channel",
            channel_types=[discord.ChannelType.text],
            custom_id="channel_select",
        )
        self.channel_select.callback = self.channel_callback
        self.add_item(self.channel_select)

    async def channel_callback(self, interaction: discord.Interaction):
        selected_channel = self.channel_select.values[0]
        self.channel_id = selected_channel.id

        # Update the prompt channel
        self.bot.prompt_info[self.prompt_id]["channel"] = self.channel_id
        self.bot.save()

        # Log the change
        guild_id = str(interaction.guild.id)
        log_channel = self.bot.get_channel(self.bot.config[guild_id]["log_channel_id"])

        log_embed = discord.Embed(
            title=f"{self.prompt_id} channel updated",
            description=f"New channel: <#{self.channel_id}>",
            color=discord.Color.blue(),
        )
        log_embed.set_author(
            name=interaction.user.name,
            icon_url=interaction.user.avatar.url if interaction.user.avatar else None,
        )
        if interaction.guild.icon:
            log_embed.set_thumbnail(url=interaction.guild.icon.url)
        log_embed.timestamp = datetime.datetime.now()

        if log_channel:
            await log_channel.send(embed=log_embed)

        self.finished = True
        self.stop()

        await interaction.response.send_message(
            f"✅ Channel for prompt `{self.prompt_id}` has been updated to <#{self.channel_id}>.",
            ephemeral=True,
        )


class EditPromptFilesView(discord.ui.View):
    """View for managing files attached to a prompt"""

    def __init__(self, prompt_id: str, bot):
        super().__init__(timeout=60)
        self.prompt_id = prompt_id
        self.bot = bot

    @discord.ui.button(label="View Current Files", style=discord.ButtonStyle.primary)
    async def view_files(
        self, interaction: discord.Interaction, button: discord.ui.Button
    ):
        """Show all files currently attached to this prompt"""
        guild_id = str(interaction.guild.id)

        if "image" not in self.bot.prompt_info[self.prompt_id]:
            await interaction.response.send_message(
                f"No files are attached to prompt `{self.prompt_id}`.", ephemeral=True
            )
            return

        images = self.bot.prompt_info[self.prompt_id]["image"]
        if isinstance(images, str):
            images = [images]

        await interaction.response.send_message(
            f"**Files attached to `{self.prompt_id}`:**\n"
            + "\n".join([f"• {img}" for img in images]),
            ephemeral=True,
        )

    @discord.ui.button(label="Remove a File", style=discord.ButtonStyle.danger)
    async def remove_file(
        self, interaction: discord.Interaction, button: discord.ui.Button
    ):
        """Remove a file from the prompt"""
        guild_id = str(interaction.guild.id)

        if "image" not in self.bot.prompt_info[self.prompt_id]:
            await interaction.response.send_message(
                f"No files are attached to prompt `{self.prompt_id}`.", ephemeral=True
            )
            return

        images = self.bot.prompt_info[self.prompt_id]["image"]
        if isinstance(images, str):
            images = [images]

        # Create a select menu for file removal
        select = discord.ui.Select(
            placeholder="Select a file to remove",
            options=[discord.SelectOption(label=img, value=img) for img in images],
        )

        async def select_callback(select_interaction: discord.Interaction):
            file_to_remove = select.values[0]

            # Remove from list
            if isinstance(self.bot.prompt_info[self.prompt_id]["image"], list):
                self.bot.prompt_info[self.prompt_id]["image"].remove(file_to_remove)

                # If only one file left, convert back to string
                if len(self.bot.prompt_info[self.prompt_id]["image"]) == 1:
                    self.bot.prompt_info[self.prompt_id]["image"] = (
                        self.bot.prompt_info[self.prompt_id]["image"][0]
                    )
                elif len(self.bot.prompt_info[self.prompt_id]["image"]) == 0:
                    del self.bot.prompt_info[self.prompt_id]["image"]
            else:
                del self.bot.prompt_info[self.prompt_id]["image"]

            # Delete the actual file
            file_path = os.path.join(prompt_image_dir, guild_id, file_to_remove)
            try:
                os.unlink(file_path)
            except FileNotFoundError:
                pass

            self.bot.save()

            # Log the change
            log_channel = self.bot.get_channel(
                self.bot.config[guild_id]["log_channel_id"]
            )

            log_embed = discord.Embed(
                title=f"File removed from {self.prompt_id}",
                description=f"Removed: `{file_to_remove}`",
                color=discord.Color.orange(),
            )
            log_embed.set_author(
                name=select_interaction.user.name,
                icon_url=(
                    select_interaction.user.avatar.url
                    if select_interaction.user.avatar
                    else None
                ),
            )
            log_embed.timestamp = datetime.datetime.now()

            if log_channel:
                await log_channel.send(embed=log_embed)

            await select_interaction.response.send_message(
                f"✅ Removed `{file_to_remove}` from prompt `{self.prompt_id}`.",
                ephemeral=True,
            )

        select.callback = select_callback
        view = discord.ui.View()
        view.add_item(select)

        await interaction.response.send_message(
            "Select a file to remove:", view=view, ephemeral=True
        )

    @discord.ui.button(label="Clear All Files", style=discord.ButtonStyle.danger)
    async def clear_files(
        self, interaction: discord.Interaction, button: discord.ui.Button
    ):
        """Remove all files from the prompt"""
        guild_id = str(interaction.guild.id)

        if "image" not in self.bot.prompt_info[self.prompt_id]:
            await interaction.response.send_message(
                f"No files are attached to prompt `{self.prompt_id}`.", ephemeral=True
            )
            return

        images = self.bot.prompt_info[self.prompt_id]["image"]
        if isinstance(images, str):
            images = [images]

        # Delete all files
        for img in images:
            file_path = os.path.join(prompt_image_dir, guild_id, img)
            try:
                os.unlink(file_path)
            except FileNotFoundError:
                pass

        del self.bot.prompt_info[self.prompt_id]["image"]
        self.bot.save()

        # Log the change
        log_channel = self.bot.get_channel(self.bot.config[guild_id]["log_channel_id"])

        log_embed = discord.Embed(
            title=f"All files removed from {self.prompt_id}",
            description=f"Removed {len(images)} file(s)",
            color=discord.Color.red(),
        )
        log_embed.set_author(
            name=interaction.user.name,
            icon_url=interaction.user.avatar.url if interaction.user.avatar else None,
        )
        log_embed.timestamp = datetime.datetime.now()

        if log_channel:
            await log_channel.send(embed=log_embed)

        await interaction.response.send_message(
            f"✅ All files removed from prompt `{self.prompt_id}`.", ephemeral=True
        )


class MessageSegmentView(discord.ui.View):
    """View for selecting which segment of a long message to edit"""

    def __init__(self, prompt_id: str, segments: list, bot):
        super().__init__(timeout=120)
        self.prompt_id = prompt_id
        self.segments = segments  # This will be updated as edits are made
        self.bot = bot

        # Create a button for each segment
        for i in range(len(segments)):
            button = discord.ui.Button(
                label=f"Edit Segment {i + 1}",
                style=discord.ButtonStyle.primary,
                custom_id=f"segment_{i}",
            )
            # Create a closure to capture the current index
            button.callback = self.create_segment_callback(i)
            self.add_item(button)

    def create_segment_callback(self, segment_index: int):
        """Create a callback function for a specific segment"""

        async def callback(interaction: discord.Interaction):
            # Use the CURRENT segments from this view (which includes any edits)
            modal = EditPromptMessageModal(
                self.prompt_id,
                self.segments[segment_index],
                self.bot,
                segment_index=segment_index,
                all_segments=self.segments,  # Pass reference, not copy
                parent_view=self,  # Pass reference to this view
            )
            await interaction.response.send_modal(modal)

        return callback


class EditPromptView(discord.ui.View):
    """Main view for selecting what to edit about a prompt"""

    def __init__(self, prompt_id: str, bot):
        super().__init__(timeout=60)
        self.prompt_id = prompt_id
        self.bot = bot

    @discord.ui.button(
        label="Edit Message", style=discord.ButtonStyle.primary, emoji="📝"
    )
    async def edit_message(
        self, interaction: discord.Interaction, button: discord.ui.Button
    ):
        """Open modal to edit the prompt message, or segment selector for long messages"""
        current_message = self.bot.prompt_info[self.prompt_id].get("message", "")

        # Check if message exceeds 4000 characters
        if len(current_message) <= 4000:
            # Message fits in one modal, edit normally
            modal = EditPromptMessageModal(self.prompt_id, current_message, self.bot)
            await interaction.response.send_modal(modal)
        else:
            # Message is too long, need to segment it intelligently
            segments = segment_message(current_message)

            # Create an embed showing previews of each segment
            embed = discord.Embed(
                title=f"Edit Message for {self.prompt_id}",
                description=f"This message is {len(current_message)} characters long and has been split into {len(segments)} segments.\n"
                f"Select which segment you want to edit:",
                color=discord.Color.orange(),
            )

            # Add preview of each segment
            for i, segment in enumerate(segments):
                # Get first and last ~100 characters of segment
                preview_start = segment[:100].replace("\n", " ")
                preview_end = segment[-100:].replace("\n", " ")

                # Check if this segment contains INVENTORY
                contains_inventory = "INVENTORY" in segment
                segment_label = f"Segment {i + 1}"
                if contains_inventory:
                    segment_label += " [INVENTORY SECTION]"

                if len(segment) <= 200:
                    # Segment is short enough to show in full
                    preview = segment.replace("\n", " ")
                    if len(preview) > 200:
                        preview = preview[:197] + "..."
                else:
                    preview = (
                        f"**Start:** {preview_start}...\n**End:** ...{preview_end}"
                    )

                embed.add_field(
                    name=f"{segment_label} ({len(segment)} chars)",
                    value=preview,
                    inline=False,
                )

            embed.set_footer(text="Click a button below to edit that segment")

            # Create view with segment selection buttons
            view = MessageSegmentView(self.prompt_id, segments, self.bot)

            await interaction.response.send_message(
                embed=embed, view=view, ephemeral=True
            )

    @discord.ui.button(
        label="Edit Channel", style=discord.ButtonStyle.primary, emoji="📺"
    )
    async def edit_channel(
        self, interaction: discord.Interaction, button: discord.ui.Button
    ):
        """Open channel selector to change the prompt's channel"""
        guild_id = str(interaction.guild.id)
        channels = [
            channel
            for channel in interaction.guild.channels
            if isinstance(channel, discord.TextChannel)
            and channel.category_id == self.bot.config[guild_id]["category_id"]
            and "district-" in channel.name
        ]
        channels.sort(key=lambda ch: ch.position)

        if not channels:
            await interaction.response.send_message(
                "No valid channels found in the configured category.", ephemeral=True
            )
            return

        view = EditPromptChannelView(self.prompt_id, channels, self.bot)
        await interaction.response.send_message(
            f"Select a new channel for prompt `{self.prompt_id}`:",
            view=view,
            ephemeral=True,
        )

    @discord.ui.button(
        label="Manage Files", style=discord.ButtonStyle.primary, emoji="📎"
    )
    async def manage_files(
        self, interaction: discord.Interaction, button: discord.ui.Button
    ):
        """Open file management view"""
        view = EditPromptFilesView(self.prompt_id, self.bot)

        # Show current file count
        file_count = 0
        if "image" in self.bot.prompt_info[self.prompt_id]:
            images = self.bot.prompt_info[self.prompt_id]["image"]
            if isinstance(images, list):
                file_count = len(images)
            else:
                file_count = 1

        await interaction.response.send_message(
            f"**Managing files for prompt `{self.prompt_id}`**\n"
            f"Current file count: {file_count}\n\n"
            f"*Note: Use `/add-file` to add new files to this prompt.*",
            view=view,
            ephemeral=True,
        )
