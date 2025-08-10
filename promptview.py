import discord
from tributechannelselector import TributeChannelSelector

class PromptView(discord.ui.View):
    def __init__(self, channels, bot = None):
        super().__init__()
        self.channel_select = TributeChannelSelector(channels)
        self.add_item(self.channel_select)

    @property
    def channel_id(self):
        return int(self.channel_select.values[0])

