import discord

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

