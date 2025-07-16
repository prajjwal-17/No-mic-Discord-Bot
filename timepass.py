import os
import subprocess
import discord
from discord.ext import commands
from discord import app_commands, FFmpegPCMAudio
from dotenv import load_dotenv
import edge_tts
import asyncio

# Load environment variables
load_dotenv()

TOKEN = os.getenv("DISCORD_TOKEN")
GUILD_ID = int(os.getenv("GUILD_ID"))
NO_MIC_CHANNEL_ID = int(os.getenv("NO_MIC_CHANNEL_ID"))
VC_CHANNEL_ID = int(os.getenv("VC_CHANNEL_ID"))

# Set up intents
intents = discord.Intents.default()
intents.message_content = True
intents.guilds = True
intents.voice_states = True

# Create the bot
class MyBot(commands.Bot):
    def __init__(self):
        super().__init__(command_prefix="!", intents=intents)

    async def setup_hook(self):
        guild = discord.Object(id=GUILD_ID)
        self.tree.copy_global_to(guild=guild)
        await self.tree.sync(guild=guild)
        print("Slash commands synced.")

bot = MyBot()

@bot.event
async def on_ready():
    print(f"{bot.user} is ready!")

# Generate TTS and stretch it to 6 seconds
async def generate_stretched_voice(text, filename="nadeem.mp3", duration=6):
    # Step 1: Generate TTS
    tts = edge_tts.Communicate(text, voice="en-IN-PrabhatNeural", rate="+10%")
    await tts.save(filename)

    # Step 2: Stretch to 6s using FFmpeg
    stretched = "nadeem_stretched.mp3"
    subprocess.run([
        "ffmpeg", "-y", "-i", filename,
        "-filter_complex", f"apad,atrim=duration={duration}",
        stretched
    ])
    return stretched

# Mix voice + tune into final file
def mix_with_tune(voice_file, tune_file="tune.mp3", output="combined.mp3"):
    subprocess.run([
        "ffmpeg", "-y",
        "-i", tune_file,
        "-i", voice_file,
        "-filter_complex",
        "[0:0]volume=0.3[a0];[1:0]volume=1.0[a1];[a0][a1]amix=inputs=2:duration=first",
        output
    ])

# TEXT CHANNEL TTS (unchanged, no music)
@bot.event
async def on_message(message):
    if message.channel.id != NO_MIC_CHANNEL_ID or message.author.bot:
        return

    print(f"Received message from {message.author}: {message.content}")
    vc_channel = message.guild.get_channel(VC_CHANNEL_ID)

    if not message.guild.voice_client:
        await vc_channel.connect()

    tts = edge_tts.Communicate(message.content, voice="en-IN-PrabhatNeural", rate="+10%")
    await tts.save("voice.mp3")

    voice_client = message.guild.voice_client
    if not voice_client.is_playing():
        audio = FFmpegPCMAudio("voice.mp3")
        voice_client.play(audio)

    await bot.process_commands(message)

# SLASH COMMAND with tune + synced voice
@bot.tree.command(name="connect", description="Nadeem Man will join and speak.")
async def connect(interaction: discord.Interaction):
    vc_channel = interaction.guild.get_channel(VC_CHANNEL_ID)

    if vc_channel is None:
        await interaction.response.send_message("Voice channel not found.", ephemeral=True)
        return

    if not interaction.guild.voice_client:
        await vc_channel.connect()

    await interaction.response.send_message("I am Nadeem Man at your service. 🔊")

    # Generate 6-second stretched voice
    text = "I am Nadeem Man at your service"
    stretched_file = await generate_stretched_voice(text)

    # Mix it with your 6-sec tune.mp3
    mix_with_tune(stretched_file, "tune.mp3", "combined.mp3")

    # Play it
    vc = interaction.guild.voice_client
    if not vc.is_playing():
        audio = FFmpegPCMAudio("combined.mp3")
        vc.play(audio)

# DISCONNECT command
@bot.command()
async def leave(ctx):
    if ctx.voice_client:
        await ctx.voice_client.disconnect()
        await ctx.send("Disconnected from voice channel.")

# Run the bot
bot.run(TOKEN)
