import discord
from discord.ext import commands

class help_cog(commands.Cog):
    def __init__(self, bot):
        self.bot = bot
        self.embedOrange = 0xeab148
    
    @commands.Cog.listener()
    async def on_ready(self):
        sendToChannels = []
        for guild in self.bot.guilds:
            channel = guild.text_channels[0]
            sendToChannels.append(channel)
        helloEmbed = discord.Embed(
            title = "Hello there!",
            description = """
            Hi, the name's **Sirius**!\n\n I am just a humble music bot. Type a command after **`.`**, well, basically a dot, for me to be at your service. Ring the **`.help`** command so I can do rundown of what I can do.""",
            colour=self.embedOrange
        )
        for channel in sendToChannels:
            await channel.send(embed=helloEmbed)

    @commands.command(
        name="help",
        aliases=["h"],
        help="Provides a description of all specified commands"
    )
    async def help(self, ctx):
        helpCog = self.bot.get_cog('help_cog')
        musicCog = self.bot.get_cog('music_cog')
        commands = helpCog.get_commands() + musicCog.get_commands()
        commandDescription = ""

        for c in commands:
            commandDescription += f"**`.{c.name}`** \n {c.help}\n"

        commandsEmbed = discord.Embed(
            title="COMMANDS LIST",
            description=commandDescription,
            colour=self.embedOrange
        )

        await ctx.send(embed=commandsEmbed)