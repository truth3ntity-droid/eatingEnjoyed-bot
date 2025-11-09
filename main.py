import discord
from discord.ext import commands, tasks
import random
import os
from collections import defaultdict
from flask import Flask
from threading import Thread

# === CONFIG ===
from config import (
    TARGET_CHANNEL_ID,
    IGNORE_USER_IDS,
    EAT_INTERVAL_HOURS,
    LEADERBOARD_INTERVAL_HOURS
)

# === FUNNY REPLACEMENT WORDS ===
FUNNY_WORDS = [
    "STEAKED!",
    "BEEF BLAST!",
    "BURGER BOMB!",
    "TACO TORNADO!",
    "PIZZA PANIC!",
    "CHICKEN CHAOS!",
    "CROISSANT CRASH!",
    "DONUT DOOM!",
    "CHOCO COLLAPSE!",
    "FRY FIASCO!",
    "CAKE CATASTROPHE!",
    "SANDWICH SAGA!",
    "NOODLE NIGHTMARE!",
    "HOTDOG HORROR!",
    "ICE CREAM INVASION!",
    "PANCAKE POUNCE!",
    "POPCORN PANDEMONIUM!",
    "SALAD STORM!",
    "WATERMELON WHAM!",
    "BANANA BLOWOUT!"
]

# === BOT SETUP ===
intents = discord.Intents.default()
intents.message_content = True
intents.messages = True
bot = commands.Bot(command_prefix="!", intents=intents)

# === DATA STORAGE ===
eaten_count = defaultdict(int)
last_eaten_message = None
DATA_FILE = "eaten_data.txt"

def load_data():
    try:
        with open(DATA_FILE, "r") as f:
            for line in f:
                if ":" in line:
                    uid, cnt = line.strip().split(":", 1)
                    eaten_count[int(uid)] = int(cnt)
    except FileNotFoundError:
        pass

def save_data():
    with open(DATA_FILE, "w") as f:
        for uid, cnt in eaten_count.items():
            f.write(f"{uid}:{cnt}\n")

# === EAT & DELETE FUNCTION (FIXED!) ===
async def eat_and_replace():
    global last_eaten_message
    channel = bot.get_channel(TARGET_CHANNEL_ID)
    if not channel:
        print("Channel not found!")
        return

    try:
        msgs = [m async for m in channel.history(limit=100)]
        candidates = [
            m for m in msgs
            if not m.author.bot
            and (m.content or m.stickers or m.attachments)
            and (last_eaten_message is None or m.id != last_eaten_message.id)
            and m.author.id not in IGNORE_USER_IDS
        ]

        if not candidates:
            return

        msg = random.choice(candidates)

        # DELETE THE MESSAGE
        try:
            await msg.delete()
            print(f"Deleted message from {msg.author.name}")
        except Exception as e:
            print(f"Failed to delete: {e}")

        # SEND FUNNY REPLACEMENT
        funny = random.choice(FUNNY_WORDS)
        await channel.send(funny)

        # COUNT IT
        eaten_count[msg.author.id] += 1
        last_eaten_message = msg
        save_data()
        print(f"Eaten & replaced: {funny}")

    except Exception as e:
        print(f"Error: {e}")

# === LEADERBOARD ===
async def post_leaderboard():
    channel = bot.get_channel(TARGET_CHANNEL_ID)
    if not channel or not eaten_count:
        return

    top = sorted(eaten_count.items(), key=lambda x: x[1], reverse=True)[:5]
    embed = discord.Embed(title="EATEN LEADERBOARD", color=0xff6b6b)
    medals = ["1st", "2nd", "3rd", "4th", "5th"]
    for i, (uid, cnt) in enumerate(top, 1):
        user = bot.get_user(uid)
        name = user.display_name if user else f"User {uid}"
        embed.add_field(
            name=f"{medals[i-1]} - {name}",
            value=f"`{cnt}` times eaten",
            inline=False
        )
    embed.set_footer(text="eatingEnjoyed.1984")
    await channel.send(embed=embed)

# === TASKS ===
@tasks.loop(hours=EAT_INTERVAL_HOURS)
async def eat_task():
    await bot.wait_until_ready()
    await eat_and_replace()

@tasks.loop(hours=LEADERBOARD_INTERVAL_HOURS)
async def leaderboard_task():
    await bot.wait_until_ready()
    await post_leaderboard()

# === BOT EVENTS & COMMANDS ===
@bot.event
async def on_ready():
    print(f"{bot.user} is HUNGRY and ready!")
    print(f"Monitoring channel: {TARGET_CHANNEL_ID}")
    load_data()
    eat_task.start()
    leaderboard_task.start()

@bot.command()
@commands.is_owner()
async def eatnow(ctx):
    if ctx.channel.id != TARGET_CHANNEL_ID:
        await ctx.send("Only in target channel!")
        return
    await eat_and_replace()
    await ctx.send("NOM! (Forced eat)")

@bot.command()
@commands.is_owner()
async def leaderboard(ctx):
    if ctx.channel.id != TARGET_CHANNEL_ID:
        await ctx.send("Only in target channel!")
        return
    await post_leaderboard()

@bot.command()
async def mystats(ctx):
    if ctx.channel.id != TARGET_CHANNEL_ID:
        await ctx.send("Only in target channel!")
        return
    count = eaten_count.get(ctx.author.id, 0)
    await ctx.send(f"Your messages have been **EATEN {count} times**!")

# === KEEP-ALIVE (RENDER) ===
app = Flask('')

@app.route('/')
def home():
    return "Bot is alive! NOM NOM"

def run_flask():
    port = int(os.environ.get('PORT', 10000))
    app.run(host='0.0.0.0', port=port)

flask_thread = Thread(target=run_flask)
flask_thread.daemon = True
flask_thread.start()
print(f"Flask running on port {os.environ.get('PORT', 10000)}")

# === START BOT ===
TOKEN = os.getenv("BOT_TOKEN")
if TOKEN:
    bot.run(TOKEN)
else:
    print("ERROR: Add BOT_TOKEN in Render Environment Variables!")
