import os
import subprocess
import discord
from discord.ext import commands, tasks
from discord import app_commands, FFmpegPCMAudio
from dotenv import load_dotenv
import edge_tts
import asyncio
from datetime import datetime, timedelta

# Load environment variables
load_dotenv()
TOKEN = os.getenv("DISCORD_TOKEN")
GUILD_ID = int(os.getenv("GUILD_ID"))
NO_MIC_CHANNEL_ID = int(os.getenv("NO_MIC_CHANNEL_ID"))

# Set up intents
intents = discord.Intents.default()
intents.message_content = True
intents.guilds = True
intents.voice_states = True

# Create the bot
class MyBot(commands.Bot):
    def __init__(self):
        super().__init__(command_prefix="!", intents=intents)
        self.last_active = {}  # track last played time per guild

    async def setup_hook(self):
        guild = discord.Object(id=GUILD_ID)
        self.tree.copy_global_to(guild=guild)
        await self.tree.sync(guild=guild)
        print("Slash commands synced.")

bot = MyBot()

@bot.event
async def on_ready():
    print(f"{bot.user} is ready!")
    check_inactive.start()

# Generate and stretch voice to 6 seconds
async def generate_stretched_voice(text, filename="nadeem.mp3", duration=6):
    tts = edge_tts.Communicate(text, voice="en-IN-PrabhatNeural", rate="+10%")
    await tts.save(filename)

    # Stretch using FFmpeg
    stretched = "nadeem_stretched.mp3"
    subprocess.run([
        "ffmpeg", "-y", "-i", filename,
        "-filter_complex", f"apad,atrim=duration={duration}",
        stretched
    ])
    return stretched

# Mix voice + tune
def mix_with_tune(voice_file, tune_file="tune.mp3", output="combined.mp3"):
    subprocess.run([
        "ffmpeg", "-y",
        "-i", tune_file,
        "-i", voice_file,
        "-filter_complex",
        "[0:0]volume=0.3[a0];[1:0]volume=1.0[a1];[a0][a1]amix=inputs=2:duration=first",
        output
    ])

# Update last activity
def update_last_active(guild_id):
    bot.last_active[guild_id] = datetime.utcnow()

# Inactivity checker (runs every 60s)
@tasks.loop(seconds=60)
async def check_inactive():
    for guild in bot.guilds:
        vc = guild.voice_client
        if vc and not vc.is_playing():
            last_time = bot.last_active.get(guild.id)
            if last_time and datetime.utcnow() - last_time > timedelta(minutes=5):
                await vc.disconnect()
                print(f"Disconnected from {guild.name} due to 5 minutes of inactivity.")

# Text channel message trigger (no music)
@bot.event
async def on_message(message):
    if message.channel.id != NO_MIC_CHANNEL_ID or message.author.bot:
        return

    print(f"Received message from {message.author}: {message.content}")

    if not message.author.voice or not message.author.voice.channel:
        await message.channel.send("Join a voice channel first.")
        return

    vc_channel = message.author.voice.channel

    if not message.guild.voice_client:
        await vc_channel.connect()

    tts = edge_tts.Communicate(message.content, voice="en-IN-PrabhatNeural", rate="+10%")
    await tts.save("voice.mp3")

    voice_client = message.guild.voice_client
    if not voice_client.is_playing():
        update_last_active(message.guild.id)
        voice_client.play(FFmpegPCMAudio("voice.mp3"))

    await bot.process_commands(message)

# Slash command with synced music + TTS
@bot.tree.command(name="connect", description="Nadeem Man will join and speak.")
async def connect(interaction: discord.Interaction):
    if not interaction.user.voice or not interaction.user.voice.channel:
        await interaction.response.send_message("You must be in a voice channel to use this.", ephemeral=True)
        return

    vc_channel = interaction.user.voice.channel

    if not interaction.guild.voice_client:
        await vc_channel.connect()

    await interaction.response.send_message("I am Nadeem Man , at your service. Speak your heart out. 🔊")

    text = "I am Nadeem Man ,  at your service. Speak your heart out."
    stretched_file = await generate_stretched_voice(text)
    mix_with_tune(stretched_file, "tune.mp3", "combined.mp3")

    vc = interaction.guild.voice_client
    if not vc.is_playing():
        update_last_active(interaction.guild.id)
        vc.play(FFmpegPCMAudio("combined.mp3"))

# Command to manually disconnect
@bot.command()
async def leave(ctx):
    if ctx.voice_client:
        await ctx.voice_client.disconnect()
        await ctx.send("Disconnected from voice channel.")

bot.run(TOKEN)
