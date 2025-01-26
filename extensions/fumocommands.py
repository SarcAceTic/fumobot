import discord
from discord.ui import View, Button
from io import BytesIO
from discord.ext import commands
import aiohttp
import customutilities
import typing
import asyncio
import asqlite
from datetime import timedelta, datetime
import random
import pydealer as pd

async def fumoDbCheck():
  async with asqlite.connect("fumo.db") as db:
    async with db.cursor() as cursor:
      await cursor.execute("""
      CREATE TABLE IF NOT EXISTS players (
      id INTEGER PRIMARY KEY,
      username TEXT,
      balance INTEGER DEFAULT 100                     
      )
      """)
      await db.commit()

class BlackjackView(View):
  def __init__(self, ctx, hand, dealerHand, embed, deck, bet, pscore, timeout = 20):
    super().__init__(timeout=timeout)
    self.ctx = ctx
    self.hand = hand
    self.dealerHand = dealerHand
    self.embed = embed
    self.deck = deck
    self.bet = bet
    self.pscore = pscore

    self.winnings = bet
    self.gameRover = False

  async def interaction_check(self, interaction):
    if interaction.user.id != self.ctx.user.id:
      await interaction.response.send_message("This button is not for you!!", ephemeral=True)
      return False
    else:
      return True

  async def on_timeout(self):
    if not self.gameRover:
      for item in self.children:
        item.disabled= True

      await self.message.edit(view=self)
      await self.ctx.reply("You didn't respond in time! The whole game is cancelled, and fortunately, the dealer was kind enough to give you your money back.")
  
  @discord.ui.button(label="Hit!", style=discord.ButtonStyle.green)
  async def hitButton(self, interaction: discord.Interaction, button: Button):
    self.hand.add(self.deck.deal(1))
    self.pscore = customutilities.handValue(self.hand)

    self.embed = discord.Embed(
      description=f"{f"Oh no! You busted! You lost {self.bet}...\n" if self.pscore > 21 else ""}**Your Hand**: {" ".join(f"| {card.value} of {card.suit} " for card in self.hand)}\nScore: {self.pscore}\n\n**Dealer's Hand**: Hidden | {" ".join(f"{card.value} of {card.suit} | " for card in self.dealerHand[1:])}",
      timestamp=datetime.now(),
      color=discord.Color.purple()
    )
    self.embed.set_footer(
      text=self.ctx.author.name,
      icon_url=self.ctx.author.avatar.url
    )

    if self.pscore > 21:
      await customutilities.updateBalance(self.ctx.author.id, self.bet * -1)
      self.gameOver()
      self.gameRover = True

    await interaction.response.edit_message(embed=self.embed, view=self)
  
  @discord.ui.button(label="Stand!", style=discord.ButtonStyle.red)
  async def standButton(self, interaction: discord.Interaction, button: Button):
    dealerScore = customutilities.handValue(self.dealerHand)

    while customutilities.handValue(self.dealerHand) < 17:
      self.dealerHand.add(self.deck.deal(1))
      dealerScore = customutilities.handValue(self.dealerHand)
    
    print(self.pscore)
    if dealerScore > self.pscore and (dealerScore < 21):
      await customutilities.updateBalance(self.ctx.author.id, self.bet * -1)
      self.gameOver()
      self.gameRover = True
    elif dealerScore == self.pscore:
      self.gameOver()
      self.gameRover = True
    else:
      await customutilities.updateBalance(self.ctx.author.id, self.winnings)
      self.gameOver()
      self.gameRover = True
    
    self.embed = discord.Embed(
      description=f"{f"Ahh! You lost! You gave away {self.bet} to the dealer!" if dealerScore > self.pscore and (dealerScore < 21) else f"You drew with the dealer! You didn't win anything..." if dealerScore == self.pscore else f"Yay! The dealer {"busted" if dealerScore > 21 else "lost"}! You won {self.winnings}"}\n\n**Your Hand**: {" ".join(f"| {card.value} of {card.suit} " for card in self.hand)}\nScore: {self.pscore}\n\n**Dealer's Hand**: {" ".join(f"| {card.value} of {card.suit}" for card in self.dealerHand)}\nScore:{customutilities.handValue(self.dealerHand)}",
      timestamp=datetime.now(),
      color=discord.Color.purple()
    )
    self.embed.set_footer(
      text=self.ctx.author.name,
      icon_url=self.ctx.author.avatar.url
    )

    await interaction.response.edit_message(embed=self.embed, view=self)
  
  def gameOver(self):
    self.standButton.disabled = True
    self.hitButton.disabled = True

class FumoCommands(commands.Cog, name="Fumo"):
  """Take care of your Fumos here in this simple pet economy game!"""
  def __init__(self, bot):
    self.bot = bot
  
  async def cog_before_invoke(self, ctx):
    async with asqlite.connect("fumo.db") as db:
      async with db.cursor() as cursor:
        await cursor.execute(
          """
          INSERT INTO players (id, username)
          VALUES (?, ?)
          ON CONFLICT (id)
          DO UPDATE SET 
            username = excluded.username
          """, (ctx.author.id, ctx.author.name)
        )
  
  @commands.command(name="collection")
  async def collection(self, ctx, user: discord.User = commands.parameter(default=None, description="The user to be inputted.")):
    """Find out a user's / your Fumo collection!"""
    user = user or ctx.author
  
  @commands.command(name="balance", aliases=["bal", "points"])
  async def balance(self, ctx, user: discord.User = commands.parameter(default=None, description="The user to be inputted.")):
    """Check a user's balance / power."""
    user = user or ctx.author
    row = await customutilities.checkBalance(user.id)

    if row is None:
      await ctx.reply(embed=discord.Embed(
        description=f"**Balance**:\n<:power_item:1329068042650386518> 0",
        timestamp=datetime.now(),
        color=discord.Color.purple(),
      ).set_footer(
        text=ctx.author.name,
        icon_url=ctx.author.avatar.url
      ).set_author(
        name=user.name, 
        icon_url=user.avatar.url
      ))
      return
          
    balanceEmbed = discord.Embed(
      description=f"**Balance**:\n<:power_item:1329068042650386518> {row[0]}",
      timestamp=datetime.now(),
      color=discord.Color.purple(),
    )
    balanceEmbed.set_footer(
      text=ctx.author.name,
      icon_url=ctx.author.avatar.url
    )
    balanceEmbed.set_author(name=user.name, icon_url=user.avatar.url)

    await ctx.reply(embed=balanceEmbed)
  
  @commands.command(name="dice")
  async def dice(self, ctx, power: int = commands.parameter(description="The amount of power to be put on bet.")):
    """Gambles your power away. You win everytime you don't roll a 6. Pays out 0.2x of your original bet."""
    await customutilities.lowBalance(ctx, power=power)
    if power <= 2:
      raise commands.BadArgument("You cannot bet less than <:power_item:1329068042650386518> 2!")

    diceEmojis = [
      "<:dice1:1329654498540519454>",
      "<:dice2:1329654509340721173>",
      "<:dice3:1329654500625219584>",
      "<:dice4:1329654502604673045>",
      "<:dice5:1329654504710344805>",
      "<:dice6:1329654507302555689>"
      ]
    rollingEmbed = discord.Embed(
      description=f"<a:diceroll:1329655140415967293> | Rolling a dice for <:power_item:1329068042650386518> {power}...",
      timestamp=datetime.now(),
      color=discord.Color.purple()
    )
    rollingEmbed.set_footer(
      text=ctx.author.name,
      icon_url=ctx.author.avatar.url
    )
    rolled = await ctx.reply(embed=rollingEmbed)
    roll = random.randint(1, 6)
    winnings = round(power * 0.2) if roll != 6 else power * -1
    rolledEmbed = discord.Embed(
      description=f"{diceEmojis[roll - 1]} | {"Good job!" if roll != 6 else "Oh no..."} You rolled a {roll}! You {"won" if roll != 6 else "lost"} <:power_item:1329068042650386518> {winnings if roll != 6 else winnings * -1}{"!" if roll != 6 else "..."}",
      timestamp=datetime.now(),
      color=discord.Color.purple()
    )
    rolledEmbed.set_footer(
      text=ctx.author.name,
      icon_url=ctx.author.avatar.url
    )
    await asyncio.sleep(4.5)

    await customutilities.updateBalance(ctx.author.id, winnings)
    await rolled.edit(embed=rolledEmbed)
  
  @commands.command(name="blackjack", aliases=["bj"])
  async def blackjack(self, ctx, power: int = commands.parameter(description="The amount of power to be put on bet.")):
    """Gambles your power away in a game of Blackjack. Pays out 2x, and Blackjacks pays out 2.5x"""
    await customutilities.lowBalance(ctx, power=power)
    bjEmbed = discord.Embed(
      description=f"Dealing cards...",
      timestamp=datetime.now(),
      color=discord.Color.purple()
    )
    bjEmbed.set_footer(
      text=ctx.author.name,
      icon_url=ctx.author.avatar.url
    )

    bjMessage = await ctx.reply(embed=bjEmbed)
    await asyncio.sleep(2)

    bjDeck = pd.Deck()
    bjDeck.shuffle()
    
    playerHand = bjDeck.deal(2)
    dealerHand = bjDeck.deal(2)
    
    initialScore = customutilities.handValue(playerHand)
    
    bjEmbed = discord.Embed(
      description=f"{"**BLACKJACK!**\n" if initialScore == 21 else ""}**Your Hand**: {" ".join(f"{card.value} of {card.suit} | " for card in playerHand)}\nScore: {initialScore}\n\n**Dealer's Hand**: Hidden | {" ".join(f"{card.value} of {card.suit} | " for card in dealerHand[1:])}",
      timestamp=datetime.now(),
      color=discord.Color.purple()
    )
    bjEmbed.set_footer(
      text=ctx.author.name,
      icon_url=ctx.author.avatar.url
    )

    view = BlackjackView(ctx, playerHand, dealerHand, bjEmbed, bjDeck, power, initialScore)

    if initialScore == 21:
      view.winnings = power + int((power * 0.5))

    view.message = await bjMessage.edit(embed=bjEmbed, view=view)


async def setup(bot):
  await bot.add_cog(FumoCommands(bot))