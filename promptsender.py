import discord
import asyncio
import os
from utils import split_message


async def send_inventory_for_tribute(channel, storage, tribute_id):
    """
    Send the inventory associated with a tribute to the channel.
    
    Args:
        channel: Discord channel to send to
        storage: Storage manager with access to inventory data
        tribute_id: The tribute ID to fetch inventory for
    """
    try:
        inventory_data = storage.get_inventory(tribute_id)
        if inventory_data:
            items = inventory_data.get("items", {})
            if items:
                embed = discord.Embed(
                    title=f"{tribute_id} Inventory",
                    description="Associated inventory with this prompt",
                    color=discord.Color.gold()
                )
                items_text = "\n".join([f"**{num}.** {item}" for num, item in items.items()])
                embed.add_field(name="Items", value=items_text, inline=False)
                await channel.send(embed=embed)
    except Exception as e:
        print(f"Failed to send inventory for {tribute_id}: {e}")


async def send_single_prompt(bot, interaction, prompt_id, guild_id, prompt_image_dir, storage=None, tribute_id=None):
    """
    Sends a single prompt to its designated channel.

    Args:
        bot: The bot instance
        interaction: The discord interaction
        prompt_id: The ID of the prompt to send
        guild_id: The guild ID as a string
        prompt_image_dir: Directory where prompt images are stored
        storage: Optional storage manager to send inventory with prompt
        tribute_id: Optional tribute ID to send inventory for

    Returns:
        prompt_id if successful, None otherwise
    """
    if not interaction.guild.get_channel(int(bot.prompt_info[prompt_id]["channel"])):
        return None

    channel_id = bot.prompt_info[prompt_id]["channel"]
    channel = interaction.guild.get_channel(int(channel_id))
    if not channel:
        await interaction.followup.send(
            f"Channel {channel} does not exist", ephemeral=True
        )
        print(f"Channel {channel} does not exist")
        return None

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

        # Handle image attachments
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
                        "File is missing, please reattach the file.",
                        ephemeral=True,
                    )

        # Send associated inventory if provided
        if storage and tribute_id:
            await send_inventory_for_tribute(channel, storage, tribute_id)

        return prompt_id  # Return the prompt_id if successful

    except discord.Forbidden:
        await interaction.followup.send(
            f"The bot doesn't have permission to send files in {channel.name}",
            ephemeral=True,
        )
        print(f"Forbidden to send messages to {channel.name}")
        return None
    except discord.HTTPException as e:
        print(f"HTTP exception while sending message to {channel.name}: {e}")
        return None


async def send_all_prompts_concurrent(bot, interaction, guild_id, prompt_image_dir, storage=None):
    """
    Sends all prompts concurrently using asyncio.gather().

    Args:
        bot: The bot instance
        interaction: The discord interaction
        guild_id: The guild ID as a string
        prompt_image_dir: Directory where prompt images are stored
        storage: Optional storage manager to send inventory with prompts

    Returns:
        List of successfully sent prompt IDs
    """
    # Create tasks for all prompts
    tasks = []
    for prompt_id in bot.prompt_info.keys():
        if interaction.guild.get_channel(int(bot.prompt_info[prompt_id]["channel"])):
            # Try to get tribute_id if storage is available
            tribute_id = None
            if storage:
                # In the new schema, prompt_id may be a tribute_id
                try:
                    tribute_id = prompt_id
                except:
                    pass
            
            tasks.append(
                send_single_prompt(
                    bot, interaction, prompt_id, guild_id, prompt_image_dir, storage, tribute_id
                )
            )

    # Execute all tasks concurrently
    results = await asyncio.gather(*tasks, return_exceptions=True)

    # Collect successfully sent prompts
    prompts_to_del = []
    for result in results:
        if result and not isinstance(result, Exception):
            prompts_to_del.append(result)

    return prompts_to_del
