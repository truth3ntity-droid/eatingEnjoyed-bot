import discord
from discord.ext import commands, tasks
import random
import os
from collections import defaultdict
from config import TARGET_CHANNEL_ID, IGNORE_USER_IDS, EAT_INTERVAL_HOURS, LEADERBOARD_INTERVAL_HOURS

intents = discord.Intents.default()
intents.message_content = True
intents.messages = True

bot = commands.Bot(command_prefix="!", intents=intents)

EAT_RESPONSES = [
    "**OM NOM NOM!** Your message has been *devoured*!",
    "**CHOMP!** I just ate your message like a digital cookie!",
    "**Slurp...** Your words? *Gone.*", "**GOBBLE GOBBLE!** Into the void!",
    "**munch munch*...** Tasted like code.", "**CRONCH!** Gone in one bite!",
    "**RAWR!** Message-eating dino strikes!", "**Your message = my snack!**",
    "**gulp*...** Echo in my belly.", "**BLAST OFF!** Orbiting my stomach."
]

eaten_count = defaultdict(int)
last_eaten_message = None
DATA_FILE = "eaten_data.txt"


def load_data():
    try:
        with open(DATA_FILE, "r") as f:
            for line in f:
                uid, cnt = line.strip().split(":")
                eaten_count[int(uid)] = int(cnt)
    except FileNotFoundError:
        pass


def save_data():
    with open(DATA_FILE, "w") as f:
        for uid, cnt in eaten_count.items():
            f.write(f"{uid}:{cnt}\n")


async def do_eat_message():
    global last_eaten_message
    channel = bot.get_channel(TARGET_CHANNEL_ID)
    if not channel:
        print(f"Error: Could not find channel {TARGET_CHANNEL_ID}")
        return

    try:
        msgs = [m async for m in channel.history(limit=100)]
        candidates = [
            m for m in msgs if not m.author.bot and m.content
            and m != last_eaten_message and m.author.id not in IGNORE_USER_IDS
        ]
        if not candidates:
            print("No eligible messages to eat")
            return
        msg = random.choice(candidates)
        await msg.reply(
            f"{random.choice(EAT_RESPONSES)}\n> {msg.content[:500]}")
        eaten_count[msg.author.id] += 1
        last_eaten_message = msg
        save_data()
        print(
            f"Ate message from {msg.author.name}. Total eaten: {eaten_count[msg.author.id]}"
        )
    except Exception as e:
        print(f"Error eating message: {e}")


async def do_post_leaderboard():
    channel = bot.get_channel(TARGET_CHANNEL_ID)
    if not channel or not eaten_count:
        return
    top = sorted(eaten_count.items(), key=lambda x: x[1], reverse=True)[:5]
    embed = discord.Embed(title="🍴 EATEN LEADERBOARD 🍴", color=0xff6b6b)
    for i, (uid, cnt) in enumerate(top, 1):
        user = bot.get_user(uid)
        name = user.display_name if user else f"<@{uid}>"
        medal = ["🥇 1st", "🥈 2nd", "🥉 3rd", "4th", "5th"][i - 1]
        embed.add_field(name=f"{medal} - {name}",
                        value=f"`{cnt}` times eaten",
                        inline=False)
    embed.set_footer(text="eatingEnjoyed.1984")
    await channel.send(embed=embed)
    print("Posted leaderboard")


@bot.event
async def on_ready():
    print(f"{bot.user} is HUNGRY and ready!")
    print(f"Monitoring channel ID: {TARGET_CHANNEL_ID}")
    load_data()
    eat_messages_task.start()
    leaderboard_task.start()


@tasks.loop(hours=EAT_INTERVAL_HOURS)
async def eat_messages_task():
    await bot.wait_until_ready()
    await do_eat_message()


@tasks.loop(hours=LEADERBOARD_INTERVAL_HOURS)
async def leaderboard_task():
    await bot.wait_until_ready()
    await do_post_leaderboard()


@bot.command()
@commands.is_owner()
async def eatnow(ctx):
    if ctx.channel.id != TARGET_CHANNEL_ID:
        await ctx.send("Only in my target channel!")
        return
    await do_eat_message()
    await ctx.send("NOM!")


@bot.command()
@commands.is_owner()
async def leaderboard(ctx):
    if ctx.channel.id != TARGET_CHANNEL_ID:
        await ctx.send("Only in my target channel!")
        return
    await do_post_leaderboard()


@bot.command()
async def mystats(ctx):
    if ctx.channel.id != TARGET_CHANNEL_ID:
        await ctx.send("Only in my target channel!")
        return
    count = eaten_count.get(ctx.author.id, 0)
    await ctx.send(f"Your messages have been eaten **{count}** times!")


# === KEEP-ALIVE WEB SERVER ===
from flask import Flask
from threading import Thread

app = Flask('')


@app.route('/')
def home():
    return "Bot is alive! 🍽️ NOM NOM"


def run_flask():
    app.run(host='0.0.0.0', port=8080)


# Start Flask in background BEFORE bot starts
flask_thread = Thread(target=run_flask)
flask_thread.daemon = True
flask_thread.start()

print("Flask keep-alive server started on port 8080")

# Now start the Discord bot
TOKEN = os.getenv("BOT_TOKEN")
if TOKEN:
    print("Starting eatingEnjoyed bot...")
    bot.run(TOKEN)
else:
    print("❌ ERROR: BOT_TOKEN not found in environment variables!")
    print("Please add your Discord bot token to Replit Secrets as 'BOT_TOKEN'")
