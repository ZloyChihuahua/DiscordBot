import os
import requests
import discord
import sqlite3
import logging
import asyncio
from discord.ext import commands
from discord.utils import get

logger = logging.getLogger('discord')
logger.setLevel(logging.DEBUG)
handler = logging.StreamHandler()
handler.setFormatter(logging.Formatter('%(asctime)s:%(levelname)s:%(name)s: %(message)s'))
logger.addHandler(handler)

intents = discord.Intents.default()
intents.members = True
intents.message_content = True

bot = commands.Bot(command_prefix='!', intents=intents)
TOKEN = "TOKEN"

conn = sqlite3.connect('user_banks.db')
c = conn.cursor()

c.execute('''CREATE TABLE IF NOT EXISTS banks
             (user_id INTEGER PRIMARY KEY, money INTEGER)''')
conn.commit()


def get_money(user_id):
    c.execute("SELECT money FROM banks WHERE user_id=?", (user_id,))
    row = c.fetchone()
    if row:
        return row[0]
    else:
        return 0


def update_money(user_id, money):
    c.execute("INSERT OR REPLACE INTO banks (user_id, money) VALUES (?, ?)", (user_id, money))
    conn.commit()


async def add_money_for_message(message):
    if message.author.bot:
        return

    user_id = message.author.id
    money = get_money(user_id)

    if not hasattr(bot, 'message_counts'):
        bot.message_counts = {}
    if not hasattr(bot, 'spam_counts'):
        bot.spam_counts = {}

    bot.message_counts[user_id] = bot.message_counts.get(user_id, 0) + 1

    if bot.message_counts[user_id] > 5:
        bot.spam_counts[user_id] = bot.spam_counts.get(user_id, 0) + 1
        if bot.spam_counts[user_id] >= 3:
            await message.channel.send(f"{message.author.mention}, без спама, брат. Я за спам не даю денег!")
            bot.message_counts[user_id] = 0
            return

    update_money(user_id, money + 1)


async def reset_message_counts():
    await bot.wait_until_ready()
    while not bot.is_closed():
        bot.message_counts = {}
        await asyncio.sleep(4)


@bot.command()
async def kitten(ctx):
    response = requests.get('https://api.thecatapi.com/v1/images/search?mime_types=jpg,png')
    data = response.json()
    if data:
        image_url = data[0]['url']
        await ctx.send(image_url)
    else:
        await ctx.send("Failed to fetch a kitten image.")


shop_items = {
    "VIP": 100,
    "Элита": 250,
    "Король": 500,
    "Админ": 2500
}


@bot.command()
async def shop(ctx):
    shop_info = "```"
    for item, price in shop_items.items():
        shop_info += f"{item}: {price} Тубриков\n"
    shop_info += "```"
    await ctx.send("Вот что у нас есть:\n" + shop_info)


@bot.command()
async def buy(ctx, *, role_name):
    user_id = ctx.author.id
    money = get_money(user_id)
    role_name = role_name.capitalize()
    found_role = False
    for shop_role in shop_items.keys():
        if role_name.lower() == shop_role.lower():
            found_role = True
            break
    if found_role:
        price = shop_items[shop_role]
        if money >= price:
            role = discord.utils.get(ctx.guild.roles, name=shop_role)
            if role:
                if role in ctx.author.roles:
                    await ctx.send("У вас уже есть эта роль.")
                else:
                    await ctx.author.add_roles(role, reason="Покупка")
                    update_money(user_id, money - price)
                    await ctx.send(f"Поздравляю! Теперь вы {shop_role}.")
            else:
                await ctx.send("Такой роли нет, обратитесь к Гл. Админу.")
        else:
            await ctx.send("Извини, в долг не даю.")
    else:
        await ctx.send("Такого у нас нет.")


@bot.command()
async def money(ctx):
    user_id = ctx.author.id
    money = get_money(user_id)
    await ctx.send(f"У вас {money} Тубриков.")


@bot.event
async def on_ready():
    logger.info(f'{bot.user} Присоединён к Дискорду!')
    for guild in bot.guilds:
        logger.info(
            f'{bot.user} присоединён к серверу:\n'
            f'{guild.name}(id: {guild.id})')

    c.execute("SELECT COUNT(*) FROM banks")
    count = c.fetchone()[0]
    if count == 0:
        for guild in bot.guilds:
            for member in guild.members:
                update_money(member.id, 0)

    await bot.loop.create_task(reset_message_counts())


@bot.event
async def on_member_join(member):
    update_money(member.id, 0)
    await member.create_dm()
    await member.dm_channel.send(
        f'Добро пожаловать, {member.name}!'
    )


@bot.event
async def on_message(message):
    if message.author == bot.user:
        return

    if message.content[0] != "!":
        await add_money_for_message(message)
    await bot.process_commands(message)


bot.run(TOKEN)
