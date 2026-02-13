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


async def send_single_prompt(bot, interaction, tribute_id, guild_id, prompt_image_dir, storage=None):
    """
    Sends a single prompt to its designated channel.

    Args:
        bot: The bot instance
        interaction: The discord interaction
        tribute_id: The tribute ID whose prompt to send
        guild_id: The guild ID as a string
        prompt_image_dir: Directory where prompt images are stored
        storage: Storage manager to get prompt data

    Returns:
        tribute_id if successful, None otherwise
    """
    if not storage:
        return None
    
    # Get prompt from storage using tribute_id
    prompt_data = storage.get_prompt(tribute_id)
    if not prompt_data:
        print(f"No prompt found for {tribute_id}")
        return None
    
    channel_id = prompt_data.get('channel_id') or prompt_data.get('channel')
    if not channel_id:
        print(f"No channel specified for prompt {tribute_id}")
        return None
    
    channel = interaction.guild.get_channel(int(channel_id))
    if not channel:
        await interaction.followup.send(
            f"Channel {channel_id} does not exist", ephemeral=True
        )
        print(f"Channel {channel_id} does not exist")
        return None

    try:
        message = prompt_data.get('message', '')
        if not message:
            print(f"No message found for prompt {tribute_id}")
            return None
            
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

        # Send associated inventory if provided
        if storage and tribute_id:
            await send_inventory_for_tribute(channel, storage, tribute_id)

        return tribute_id  # Return the tribute_id if successful

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
        storage: Storage manager to get prompts

    Returns:
        List of successfully sent tribute IDs
    """
    if not storage:
        return []
    
    # Get all tributes and their prompts
    tasks = []
    tributes = bot.db.get_all_tributes(guild_id=interaction.guild.id)
    
    for tribute in tributes:
        tribute_id = tribute.get('tribute_id')
        prompt_data = storage.get_prompt(tribute_id)
        
        if prompt_data:
            channel_id = prompt_data.get('channel_id') or prompt_data.get('channel')
            if channel_id and interaction.guild.get_channel(int(channel_id)):
                tasks.append(
                    send_single_prompt(
                        bot, interaction, tribute_id, guild_id, prompt_image_dir, storage
                    )
                )

    # Execute all tasks concurrently
    results = await asyncio.gather(*tasks, return_exceptions=True)

    # Collect successfully sent tributes
    prompts_to_del = []
    for result in results:
        if result and not isinstance(result, Exception):
            prompts_to_del.append(result)

    return prompts_to_del
