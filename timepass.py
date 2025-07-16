import os
import discord
from discord.ext import commands
from discord import app_commands
from gtts import gTTS
from discord import FFmpegPCMAudio
from dotenv import load_dotenv

load_dotenv()

# Load env variables
TOKEN = os.getenv("DISCORD_TOKEN")
GUILD_ID = int(os.getenv("GUILD_ID"))
NO_MIC_CHANNEL_ID = int(os.getenv("NO_MIC_CHANNEL_ID"))
VC_CHANNEL_ID = int(os.getenv("VC_CHANNEL_ID"))

# Set intents
intents = discord.Intents.default()
intents.message_content = True
intents.guilds = True
intents.voice_states = True

# Create bot instance
class MyBot(commands.Bot):
    def __init__(self):
        super().__init__(command_prefix="!", intents=intents)

    async def setup_hook(self):
        # Sync slash commands to a specific guild for instant updates
        guild = discord.Object(id=GUILD_ID)
        self.tree.copy_global_to(guild=guild)
        await self.tree.sync(guild=guild)
        print("Slash commands synced!")

bot = MyBot()

# When bot is ready
@bot.event
async def on_ready():
    print(f"{bot.user} is ready!")

# TEXT-BASED TRIGGER from #no-mic
@bot.event
async def on_message(message):
    if message.channel.id != NO_MIC_CHANNEL_ID or message.author.bot:
        return

    print(f"Received message from {message.author}: {message.content}")
    vc_channel = message.guild.get_channel(VC_CHANNEL_ID)

    if not message.guild.voice_client:
        await vc_channel.connect()

    # Generate speech
    tts = gTTS(message.content)
    tts.save("voice.mp3")

    voice_client = message.guild.voice_client
    if not voice_client.is_playing():
        audio = FFmpegPCMAudio("voice.mp3")
        voice_client.play(audio)

    await bot.process_commands(message)

# SLASH COMMAND: /connect
@bot.tree.command(name="connect", description="Nadeem Man will join and speak.")
async def connect(interaction: discord.Interaction):
    vc_channel = interaction.guild.get_channel(VC_CHANNEL_ID)

    if vc_channel is None:
        await interaction.response.send_message("Voice channel not found.", ephemeral=True)
        return

    if not interaction.guild.voice_client:
        await vc_channel.connect()

    await interaction.response.send_message("I am Nadeem Man at your service. 🔊")

    text = "I am Nadeem Man at your service"
    tts = gTTS(text, lang="en", tld="co.in")  # male-sounding Indian voice
    tts.save("nadeem.mp3")

    voice_client = interaction.guild.voice_client
    if not voice_client.is_playing():
        audio = FFmpegPCMAudio("nadeem.mp3")
        voice_client.play(audio)

# COMMAND: !leave to disconnect
@bot.command()
async def leave(ctx):
    if ctx.voice_client:
        await ctx.voice_client.disconnect()
        await ctx.send("Disconnected from voice channel.")

# Start the bot
bot.run(TOKEN)
