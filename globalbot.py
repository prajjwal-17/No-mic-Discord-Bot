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

# Set up intents
intents = discord.Intents.default()
intents.message_content = True
intents.guilds = True
intents.voice_states = True

# Create the bot
class MyBot(commands.Bot):
    def __init__(self):
        super().__init__(command_prefix="!", intents=intents)
        self.last_active = {}

    async def setup_hook(self):
        await self.tree.sync()
        print("Global slash commands synced.")

bot = MyBot()

@bot.event
async def on_ready():
    print(f"{bot.user} is ready and connected to:")
    for g in bot.guilds:
        print(f"- {g.name} ({g.id})")
    check_inactive.start()

# Mix TTS with music
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

# Inactivity auto-disconnect
@tasks.loop(seconds=60)
async def check_inactive():
    for guild in bot.guilds:
        vc = guild.voice_client
        if vc and not vc.is_playing():
            last_time = bot.last_active.get(guild.id)
            if last_time and datetime.utcnow() - last_time > timedelta(minutes=5):
                await vc.disconnect()
                print(f"Disconnected from {guild.name} due to inactivity.")

# Handle messages in the "no-mic" channel
@bot.event
async def on_message(message):
    if message.author.bot or message.channel.name != "no-mic":
        return

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

# Slash command for joining and greeting
@bot.tree.command(name="connect", description="No-Mic Bot will join and speak.")
async def connect(interaction: discord.Interaction):
    if not interaction.user.voice or not interaction.user.voice.channel:
        await interaction.response.send_message("You must be in a voice channel.", ephemeral=True)
        return

    vc_channel = interaction.user.voice.channel

    if not interaction.guild.voice_client:
        await vc_channel.connect()

    await interaction.response.send_message("No-Mic Bot has joined. Speak freely. 🔊")

    text = "No-Mic Bot is here. Speak freely."
    tts = edge_tts.Communicate(text, voice="en-IN-PrabhatNeural", rate="+10%")
    await tts.save("voice.mp3")

    mix_with_tune("voice.mp3", "tune.mp3", "combined.mp3")

    vc = interaction.guild.voice_client
    if not vc.is_playing():
        update_last_active(interaction.guild.id)
        vc.play(FFmpegPCMAudio("combined.mp3"))

# Manual disconnect command
@bot.command()
async def leave(ctx):
    if ctx.voice_client:
        await ctx.voice_client.disconnect()
        await ctx.send("Disconnected from voice channel.")

bot.run(TOKEN)
