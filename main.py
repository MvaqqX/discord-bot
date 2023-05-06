import nextcord
from nextcord.ext import commands
import random
import os
from dotenv import load_dotenv
import aiohttp
import json
import discord
from PIL import Image, ImageDraw, ImageFont
from pymongo.mongo_client import MongoClient
import aiosqlite
import asyncio
from easy_pil import *

client = discord.Client()

servers = []
snipped_message = None


import discord

cluster = MongoClient(f"mongodb+srv://Staff:root@verification.69qjkpx.mongodb.net/?retryWrites=true&w=majority")
db = cluster["Users"]
collection = db["Verification"]

load_dotenv()

TOKEN = os.getenv("DISCORD_TOKEN")

intents = nextcord.Intents.default()
intents = nextcord.Intents().all()


def RandomNumb():
    val = random.randint(1000,9999)
    return str(val)

class AddUser(nextcord.ui.Modal):
    def __init__(self, channel):
        super().__init__(
            "Add User to Ticket",
            timeout=300,
        )
        
        self.channel = channel

        self.user = nextcord.ui.TextInput(
            label="User Id",
            min_length=2,
            max_length=30,
            required=True,
            placeholder="User ID (Must be INT)"
        )
        self.add_item(self.user)

    async def callback(self, interaction: nextcord.Interaction) -> None:
        user = interaction.guild.get_member(int(self.user.value))
        if user is None:
            return await interaction.send(f"Invalid User ID")
        overwrite = nextcord.PermissionOverwrite()
        overwrite.read_messages = True
        await self.channel.set_permissions(user, overwrite=overwrite)
        await interaction.send(f"{user.mention} has been added to this ticket")

class RemoveUser(nextcord.ui.Modal):
    def __init__(self, channel):
        super().__init__(
            "Remove User to Ticket",
            timeout=300,
        )
        
        self.channel = channel

        self.user = nextcord.ui.TextInput(
            label="User Id",
            min_length=2,
            max_length=30,
            required=True,
            placeholder="User ID (Must be INT)"
        )
        self.add_item(self.user)

    async def callback(self, interaction: nextcord.Interaction) -> None:
        user = interaction.guild.get_member(int(self.user.value))
        if user is None:
            return await interaction.send(f"Invalid User ID")
        overwrite = nextcord.PermissionOverwrite()
        overwrite.read_messages = False
        await self.channel.set_permissions(user, overwrite=overwrite)
        await interaction.send(f"{user.mention} has been Removed to this ticket")


class CreateTicket(nextcord.ui.View):
    def __init__(self, bot):
        super().__init__(timeout=None)
        self.bot = bot

    @nextcord.ui.button(
        label="Create Ticket",
        style=discord.ButtonStyle.blurple,
        custom_id="create_ticket:blurple"
    )
    async def create_ticket(self, button: nextcord.ui.Button, interaction: nextcord.Interaction):
        msg = await interaction.response.send_message("A Ticket is Being Created", ephemeral=True)

        async with self.bot.db.cursor() as cursor:
            await cursor.execute("SELECT role FROM roles WHERE guild = ?", (interaction.guild.id,))
            role = await cursor.fetchone()
            if role:
                overwrites = {
                    interaction.guild.default_role: nextcord.PermissionOverwrite(read_messages=False),
                    interaction.guild.me: nextcord.PermissionOverwrite(read_messages = True),
                    interaction.guild.get_role(role[0]): nextcord.PermissionOverwrite(read_messages=True)
                }
            else:
                overwrites = {
                    interaction.guild.default_role: nextcord.PermissionOverwrite(read_messages=False),
                    interaction.guild.me: nextcord.PermissionOverwrite(read_messages = True),
                }

        channel = await interaction.guild.create_text_channel(f"{interaction.user.name}-ticket", overwrites=overwrites)
        await msg.edit(f"Channel Created Sucessfully {channel.mention}")
        embed = nextcord.Embed(title=f"Ticket Created", description=f"{interaction.user.mention} created a ticket, click the buttons below to chnage the settings.")
        await channel.send(embed=embed, view=TicketSettings())

class TicketSettings(nextcord.ui.View):
    def __init__(self):
        super().__init__(timeout=None)

    @nextcord.ui.button(
        label="Add User",
        style=discord.ButtonStyle.green,
        custom_id="ticket_settings:green"
    )

    async def add_user(self, button: nextcord.ui.button, interaction: nextcord.Interaction):
        await interaction.response.send_modal(AddUser(interaction.channel))

    @nextcord.ui.button(
    label="Remove User",
    style=discord.ButtonStyle.gray,
    custom_id="ticket_settings:gray"
    )

    async def remove_user(self, button: nextcord.ui.button, interaction: nextcord.Interaction):
        await interaction.response.send_modal(RemoveUser(interaction.channel))

    @nextcord.ui.button(
        label="Close Ticket",
        style=discord.ButtonStyle.red,
        custom_id="ticket_settings:red"
    )

    async def close_ticket(self, button: nextcord.ui.button, interaction: nextcord.Interaction):
        messages = await interaction.channel.history(limit=None, oldest_first=True).flatten()
        contents = [message.content for message in messages]
        final = ''
        for msg in contents:
            msg = msg + "\n"
            final = final + msg
        with open("transcript.txt", 'w') as f:
            f.write(final)
        await interaction.response.send_message("Ticket is being Closed", ephemeral=True)
        await interaction.channel.delete()
        await interaction.user.send(f"Ticket closed Sucessfully", file=nextcord.File(r'transcript.txt'))
        os.remove("transcript.txt")

        

class Bot(commands.Bot):
    def __init__(self, *args, **kwargs):
        super().__init__(*args, **kwargs)
        self.persistent_views_added = False
        setattr(self, 'db2', aiosqlite.connect('database.db'))

    async def on_ready(self):
        if not self.persistent_views_added:
            self.add_view(TicketSettings())
            self.add_view(CreateTicket(self))
            self.persistent_views_added = True
            self.db = await aiosqlite.connect('database.db')
            async with self.db.cursor() as cursor:
                await cursor.execute(f"CREATE TABLE IF NOT EXISTS roles (role INTEGER, guild INTERGER)")
                await cursor.execute(f"CREATE TABLE IF NOT EXISTS levels (level INTEGER, xp INTERGER, user INTERGER, guild INTERGER)")
                print("Database Ready")
        print(f"{self.user} is ready")
        print(f"Running | Logged in as {self.user}")

bot = Bot(intents=intents)

@bot.event
async def on_message(message):
    if message.author.bot:
        return
    author = message.author
    guild = message.guild
    async with bot.db.cursor() as cursor:
        await(cursor.execute("SELECT xp FROM levels WHERE user = ? AND guild = ?", (author.id, guild.id,)))
        xp = await cursor.fetchone()
        await(cursor.execute("SELECT level FROM levels WHERE user = ? AND guild = ?", (author.id, guild.id,)))
        level = await cursor.fetchone()

        if not xp or not level:
            await cursor.execute("INSERT INTO levels (level, xp, user, guild) VALUES (?, ?, ?, ?)", (0, 0, author.id, guild.id))
            await bot.db.commit()

        try:
            xp = xp[0]
            level = level[0]
        except TypeError:
            xp = 0
            level =0

        if level < 5:
            xp += random.randint(1, 3)
            await cursor.execute("UPDATE levels SET xp = ? WHERE user = ? AND guild = ?", (xp, author.id, guild.id))
        else:
            rand = random.randint(1, (level//4))
            if rand == 1:
                xp += random.randint(1, 3)
                await cursor.execute("UPDATE levels SET xp = ? WHERE user = ? AND guild = ?", (xp, author.id, guild.id))
        if xp >= 100:
            level += 1
            await cursor.execute("UPDATE levels SET level = ? WHERE user = ? AND guild = ?", (level, author.id, guild.id))
            await cursor.execute("UPDATE levels SET xp = ? WHERE user = ? AND guild = ?", (0, author.id, guild.id))
            await message.channel.send(f"{author.mention} has leveled up to level {level}!")
    await bot.db.commit()

@bot.slash_command()
async def level(ctx: discord.Interaction, member: discord.Member = None):
    if member is None:
        member = ctx.user

    async with bot.db.cursor() as cursor:
        await(cursor.execute("SELECT xp FROM levels WHERE user = ? AND guild = ?", (member.id, ctx.guild.id,)))
        xp = await cursor.fetchone()
        await(cursor.execute("SELECT level FROM levels WHERE user = ? AND guild = ?", (member.id, ctx.guild.id,)))
        level = await cursor.fetchone()

        if not xp or not level:
            await cursor.execute("INSERT INTO levels (level, xp, user, guild) VALUES (?, ?, ?, ?)", (0, 0, member.id, ctx.guild.id))
            await bot.db.commit()

        try:
            xp = xp[0]
            level = level[0]
        except TypeError:
            xp = 0
            level =0

        user_data = {
            'name': f'{member.name}#{member.discriminator}',
            'xp': xp,
            'level': level,
            'next_level': 100,
            'percentage': xp,
        }

        background = Editor(Canvas((900, 300), color='#141414'))
        profile_pic = load_image(member.avatar.url)
        profile = Editor(profile_pic).resize((150, 150)).circle_image()

        poppins = Font.poppins(size=40)
        poppins_small = Font.poppins(size=30)

        card_right_shape = [(600, 0), (750, 300), (900, 300), (900, 0)]

        background.polygon(card_right_shape, '#FFFFFF')
        background.paste(profile, (30, 30))

        background.rectangle((30, 220), width=650, height=40, color='#FFFFFF')
        background.bar((30, 220), max_width=650, height=40, percentage=user_data['percentage'], color='#FF0000')
        background.text((200, 40), user_data['name'], font=poppins, color='#FFFFFF')

        background.rectangle((200, 100), width=350, height=2, fill="#FFFFFF")

        background.text((200, 130), f"Level - {user_data['level']} | XP - {user_data['xp']}", font=poppins_small, color='#FFFFFF')

        file = discord.File(fp=background.image_bytes, filename='levelcard.png')
        await ctx.response.send_message(file=file)
            
@bot.slash_command()
@commands.has_permissions(manage_guild=True)
async def create_ticket(ctx):
    embed = nextcord.Embed(title="Create a ticket", description="Creates a ticket, The staff will get back to you shortly")
    await ctx.send(embed=embed, view=CreateTicket(bot))
    
@bot.slash_command()
@commands.has_permissions(manage_guild=True)
async def setup_role(ctx : nextcord.Interaction, role : nextcord.Role):
    async with bot.db.cursor() as cursor:
        await cursor.execute("SELECT role FROM roles WHERE guild = ?", (ctx.guild.id,))
        role2 = await cursor.fetchone()
        if role2: 
            await cursor.execute("UPDATE roles SET role = ? WHERE guild = ?", (role.id, ctx.guild.id,))
            await ctx.send(f"Tickets Auto Assign Roles Updated")
        else:
            await cursor.execute("INSERT INTO roles (role, guild) VALUES (?, ?)", (role.id, ctx.guild.id,))
            await ctx.send(f"Tickets Auto Assign Roles Added")
    await bot.db.commit()

@bot.event
async def on_member_join(member):
    code = RandomNumb()
    mydict = {"_id": f"{member.id}", "Code": f"{code}", "Status": "Not Verified"}
    x = collection.insert_one(mydict)

    width = 130
    height = 100
    message = code
    font = ImageFont.truetype("arial.ttf", size=50)

    img = Image.new("RGB", (width,height), color='blue')

    imageDraw = ImageDraw.Draw(img)
    imageDraw.text((10, 10), message, fill='white', font=font)

    img.save(f"captchas/{code}.png")

    role =nextcord.utils.get(member.guild.roles, name="・Visitor")

    await member.add_roles(role)

    await member.send(f"Welcome to the server, Verify by typing your given code in the <#1101953883699417118> channel ||{code}||", file=nextcord.File(f'captchas/{code}.png'))


    os.remove(f'./captchas/{code}.png')

@bot.event
async def on_member_remove(member):
    collection.delete_one({"_id": f"{member.id}"})

@bot.event
async def on_message_delete(message):
    global snipped_message
    global snipped_author

    snipped_message = f"Message: {message.content}"
    snipped_author = f"Author <@{message.author.id}>"

@bot.slash_command(guild_ids=servers, name="snipe", description="Gets a Deleted Message")
async def snipe(ctx):
    await ctx.response.defer()
    if snipped_message is None:
        await ctx.followup.send("No message to snipe")
    else:
        await ctx.followup.send(f"{snipped_message}\n{snipped_author}")

new = None

@bot.event
async def on_message_edit(before, after):
    global old
    global new
    global author
    old = before.content
    new = after.content
    author = after.author.id

@bot.slash_command(guild_ids= servers, name="edit", description="Returns an edited Message")
async def edit(ctx):
    await ctx.response.defer()
    if new is None:
        await ctx.followup.send("There is no edited message to return")
    else:
        await ctx.followup.send(f"Previous {old}\nCurrent: {new}\nAuthor: <@{author}>")


@bot.slash_command(description="Verify your Account")
async def verify(interaction: nextcord.Interaction, code: str):
    myquery = {"_id": f"{interaction.user.id}"}
    mydoc = collection.find(myquery)
    role = nextcord.utils.get(interaction.guild.roles, name="Verified")
    await interaction.response.defer(ephemeral=True)

    if role is not None and role in interaction.user.roles:
        await interaction.followup.send("Already Verified", ephemeral=True)
    else:
        for x in mydoc:
            if code == x["Code"]:
                await interaction.followup.send("Sucessfully Verified", ephemeral=True)
                collection.update_one(myquery, {"$set": {"Status": "Verified"}})
                role = nextcord.utils.get(interaction.guild.roles, name="・Verified")
                await interaction.user.add_roles(role)
            else:
                await interaction.followup.send("Wrong Code", ephemeral=True)


@bot.slash_command(description="Sends an image of a cat")
async def cat(interaction: nextcord.Interaction):
    await interaction.response.defer()
    async with aiohttp.ClientSession() as session:
        async with session.get("https://api.thecatapi.com/v1/images/search") as response:
            raw = await response.text()
            cat = json.loads(raw)[0]
            embed = discord.Embed(title="Returned Cat", color=discord.Colour.green())
            embed.set_image(url=cat['url'])
            await interaction.followup.send(embed= embed)


async def getColor(interaction, color):
    colorList = ("・Blue", "・Green", "・Red", "・Purple", "・White", "・Black", "・Pink")
    await interaction.response.defer(ephemeral=True)
    role = nextcord.utils.get(interaction.guild.roles, name=f"{color}")
    roles = []  # Initialize the list outside of the loop

    for i in range(len(colorList)):
        role2 = nextcord.utils.get(interaction.guild.roles, name=f"{colorList[i]}")
        roles.append(role2)

    for i in roles:
        if i in interaction.user.roles:
            await interaction.user.remove_roles(i)

    await interaction.user.add_roles(role)
    await interaction.followup.send("Sucessfully Changed Color")



@bot.slash_command(description="Change your color")
async def color(interaction: nextcord.Interaction, color : str):
    match color.lower():
        case'blue':
          await getColor(interaction, "・Blue")
        case'green':
            await getColor(interaction, "・Green")
        case'red':
            await getColor(interaction, "・Red")
        case'purple':
            await getColor(interaction, "・Purple")
        case'white':
            await getColor(interaction, "・White")
        case'black':
            await getColor(interaction, "・Black")
        case'pink':
            await getColor(interaction, '・Pink')
        case _:
            await interaction.response.defer(ephemeral=True)
            await interaction.followup.send("Invalid Color")


@bot.slash_command()
async def say(interaction: nextcord.Interaction, message : str):
    await interaction.response.defer()
    await interaction.followup.send(message)

bot.run(TOKEN)