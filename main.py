import discord
import logging
from discord.ext import commands
from discord.ui import View, Button
from bottokens import tokener
from PIL import Image, ImageDraw, ImageFont
import aiohttp
from datetime import datetime
import customutilities
from io import BytesIO

handler = logging.FileHandler(filename='discord.log', encoding='utf-8', mode='w')

intents = discord.Intents.all()
bot = commands.Bot(
  command_prefix="?", 
  intents=intents, 
  activity=discord.Activity(name="Cleaning the Hakurei Shrine", type=discord.ActivityType.streaming),
  owner_ids=[556445511066976296, 1245710245192269917, 824431868589768734]
)
myServerId = 1251195753020522639
myGeneral = 1251195753020522642

class MyHelpCommand(commands.HelpCommand):
  def __init__(self):
    super().__init__()
  
  def get_command_signature(self, command):
    if command.clean_params:
      commandParams = [f"({p})" for p in command.clean_params.keys()]
      return commandParams
    else:
      return False

  async def send_bot_help(self, mapping):
    botEmbeds = []

    for cog, commandsList in mapping.items():
      cogName =  cog.qualified_name if cog else "Uncategorized"
      commands = "\n".join(f"**{cmd.name}** {" ".join(f"{para}" for para in self.get_command_signature(cmd)) if cmd.signature else ''}\n_{cmd.help if cmd.help else 'No Description Provided'}_" for cmd in commandsList)
      botEmbeds.append(
        discord.Embed(title=cogName + " Commands", description=commands, color=discord.Color.purple(), timestamp=datetime.now())
        .set_footer(
          text=self.context.author.name,
          icon_url=self.context.author.avatar.url
          )
        )

    channel = self.get_destination()
    view = PaginatedHelpView(botEmbeds)
    await channel.send(embed=botEmbeds[0], view=view)

  async def send_command_help(self, command):
    if command.clean_params:
      commandParams = [p for p in command.clean_params.values()]
    else:
      commandParams = []

    commandEmbed = discord.Embed(
      description=f"**{command.name} {" ".join(para for para in self.get_command_signature(command))}\n**{command.help}\n\n{'Arguments:' if commandParams else ''}\n\n{'\n'.join(f"{param.name} - _{param.description}_" for param in commandParams)}",
      color=discord.Color.purple(),
      timestamp=datetime.now()
      )
    commandEmbed.set_footer(
      text=self.context.author.name,
      icon_url=self.context.author.avatar.url
    )

    channel = self.get_destination()
    cmdparams = self.get_command_signature(command)
    await channel.send(embed=commandEmbed)
  
  async def send_cog_help(self, cog):
    cogEmbed = discord.Embed(
      title=f"{cog.qualified_name} Commands",
      description=f"{cog.description}\n\n{'\n'.join(f"{command.name} {" ".join(para for para in self.get_command_signature(command))}" for command in cog.get_commands())}",
      timestamp=datetime.now(),
      color = discord.Color.purple()
    )
    cogEmbed.set_footer(
      text=self.context.author.name,
      icon_url=self.context.author.avatar.url
    )

    channel = self.get_destination()
    await channel.send(embed=cogEmbed)

class PaginatedHelpView(View):
  def __init__(self, embeds):
    super().__init__()
    self.embeds = embeds
    self.current_page = 0
    self.previousButton.disabled = True
    self.updateButtons()
  
  @discord.ui.button(label="Previous", style=discord.ButtonStyle.red)
  async def previousButton(self, interaction: discord.Interaction, button: Button):
    """Takes you to the previous page."""
    self.current_page -= 1
    await self.updatePage(interaction)

  @discord.ui.button(label="Next", style=discord.ButtonStyle.blurple)
  async def nextButton(self, interaction: discord.Interaction, button: Button):
    """Takes you to the next page."""
    self.current_page += 1
    await self.updatePage(interaction)

  async def updatePage(self, interaction):
    """Updates the Help Embed and Page."""
    self.updateButtons()
    await interaction.response.edit_message(embed=self.embeds[self.current_page], view=self)

  def updateButtons(self):
    """Enables / disables the Next / Previous buttons based on the current page count."""
    self.previousButton.disabled = self.current_page == 0
    self.nextButton.disabled = self.current_page ==  len(self.embeds) - 1


def fontSize(size: int):
  return ImageFont.truetype("./assets/Orbitron/Orbitron-Bold.ttf", size)

async def loadCogs():
  await bot.load_extension('extensions.generalcommands')
  await bot.load_extension('extensions.fumocommands')
  await bot.load_extension('extensions.devcommands')
  await bot.load_extension('extensions.nsfwcommands')

@bot.event
async def on_ready():
  print(f'Logged in as {bot.user}')
  await loadCogs()

@bot.event
async def on_member_join(member):
  if member.guild.id == myServerId:
    channel = bot.get_channel(myGeneral)

    backgroundImage = Image.open("./assets/WelcomeFumo.jpg").convert("RGBA")
    blackOverlay = Image.new("RGBA", backgroundImage.size, (0, 0, 0, 0))
    overlayDraw = ImageDraw.Draw(blackOverlay)
    userW, userH = backgroundImage.size
    pfpSize = 250
  
    texts = [
    {"text": "Welcome to Fumoland!", "fontSize": 75, "yOffset": -460, "strokeWidth": 3},
    {"text": member.name, "fontSize": 55, "yOffset": -80, "strokeWidth": 3},
    {"text": "\"Enjoy your stay here.... heheheheh...\"", "fontSize": 40, "yOffset": 350, "strokeWidth": 2}
    ]

    overlayDraw.rectangle([(0, 0), backgroundImage.size], fill=(0, 0, 0, 80))
    finalImage = Image.alpha_composite(backgroundImage, blackOverlay)
    imgDrawObject = ImageDraw.Draw(finalImage)

    for atext in texts:
      font = fontSize(atext["fontSize"])
      textLength = imgDrawObject.textlength(text=atext["text"], font=font)
      xPos = (userW - textLength) // 2
      yPos = userH/2 + atext["yOffset"]
      imgDrawObject.text(
        (xPos, yPos),
        text=atext["text"],
        font=font,
        stroke_width=atext["strokeWidth"],
        stroke_fill='black'
      )

    async with aiohttp.ClientSession() as session:
      async with session.get(member.avatar.url) as response:
        if response.status == 200:
          pfpBytes = await response.read()
          pfp = Image.open(BytesIO(pfpBytes)).resize((pfpSize, pfpSize))
          mask = Image.new("L", (pfpSize, pfpSize), 0)
          drawMask = ImageDraw.Draw(mask)
          drawMask.ellipse((0, 0, pfpSize, pfpSize), fill=255)

          outlineSize = 7  # Thickness of the outline
          outlineDiameter = pfpSize + (outlineSize * 2)
          outline = Image.new("RGBA", (outlineDiameter, outlineDiameter), (0, 0, 0, 0))
          drawOutline = ImageDraw.Draw(outline)
          outlineColor = (255, 255, 255, 255)
          drawOutline.ellipse(
            (0, 0, outlineDiameter, outlineDiameter), 
            fill=outlineColor
          )

          finalImage.paste(outline, ((userW - outlineDiameter) // 2, (userH // 3) - 178), outline)
          finalImage.paste(pfp, ((userW - pfpSize) // 2, (userH // 3) - 170), mask=mask)

          with BytesIO() as screenshotter:
            finalImage.save(screenshotter, 'PNG')
            screenshotter.seek(0)
            await channel.send(f"Welcome to my domain, {member.mention}! Enjoy your stay here!", file=discord.File(screenshotter, 'WelcomeImage.png'))

@bot.event
async def on_command_error(ctx, err):
  if isinstance(err, commands.CommandNotFound):
    return
  elif isinstance(err, commands.NotOwner):
    await ctx.reply("Sorry, this command is only reserved for Ryn!")
  elif isinstance(err, commands.BadArgument):
    await ctx.reply(err)
  elif isinstance(err, commands.MissingRequiredArgument):
    await ctx.reply(f"Missing `{err.param.name}` argument, which is required. Try to use `*help {ctx.command.name}` for the proper usage.")
  elif isinstance(err, commands.MissingPermissions):
    await ctx.reply(f"You are missing permissions to do this command!")
  elif isinstance(err, customutilities.Hierarchy):
    await ctx.reply(f"Cannot execute this command since your top role is equal/lower than the one you're trying to moderate, or I'm trying to edit you and your role is higher than mine.")
  elif isinstance(err, commands.NSFWChannelRequired):
    await ctx.reply(f"Naughty! Go to a NSFW Channel first to use this command!")
  elif isinstance(err, customutilities.NotEnoughMoney):
    await ctx.reply(f"You don't have enough money to do this... Brokie.")
  elif isinstance(err, commands.BotMissingPermissions):
    await ctx.reply(f"I don't have permissions to do this... Or your role is higher than mine!")
  elif isinstance(err, customutilities.YoureTheOwner):
    await ctx.reply(f"I can't do this since you're the server owner!")
  elif isinstance(err, commands.NoPrivateMessage):
    await ctx.reply(f"Sorry, but you can only do this in a server!")
  else:
    print(err)
    await ctx.reply(f"Err... an unexpected issue happened! The problem has been sent to Ryn... Hang on tight!")

bot.help_command = MyHelpCommand()
bot.run(tokener) 