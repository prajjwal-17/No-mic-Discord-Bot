import discord
from discord.ext import commands
import asyncio
import os
from gtts import gTTS
from discord import FFmpegPCMAudio
from dotenv import load_dotenv

load_dotenv()

TOKEN = os.getenv("DISCORD_TOKEN")
GUILD_ID = int(os.getenv("GUILD_ID"))
NO_MIC_CHANNEL_ID = int(os.getenv("NO_MIC_CHANNEL_ID"))
VC_CHANNEL_ID = int(os.getenv("VC_CHANNEL_ID"))



intents = discord.Intents.default()
intents.message_content = True
intents.voice_states = True
intents.guilds = True

bot = commands.Bot(command_prefix="!", intents=intents)

@bot.event
async def on_ready():
    print(f"{bot.user} is ready!")

@bot.event
async def on_message(message):
    if message.channel.id != NO_MIC_CHANNEL_ID or message.author.bot:
        return

    vc = discord.utils.get(message.guild.voice_channels, id=VC_CHANNEL_ID)

    if not message.guild.voice_client:
        await vc.connect()

    text = message.content
    tts = gTTS(text)
    tts.save("voice.mp3")

    voice_client = message.guild.voice_client
    if not voice_client.is_playing():
        audio = FFmpegPCMAudio("voice.mp3")
        voice_client.play(audio)

    await bot.process_commands(message)

@bot.command()
async def leave(ctx):
    if ctx.voice_client:
        await ctx.voice_client.disconnect()

bot.run(TOKEN)
