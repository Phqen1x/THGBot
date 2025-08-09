import discord

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
        print('Confirm')

    async def send_callback(self, interaction: discord.Interaction):
        await interaction.response.defer()
        self.confirmed = True
        self.stop()

    async def cancel_callback(self, interaction: discord.Interaction):
        await interaction.response.defer()
        self.confirmed = False
        self.stop()
