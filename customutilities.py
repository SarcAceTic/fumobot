from discord.ext import commands
from datetime import timedelta
import asqlite
import pydealer as pd
from pydealer.const import VALUES

# THIS IS ALL FOR CONVERTERS

class Duration(commands.Converter):
  async def convert(self, ctx, argument):
    units = {'d': 86400, 'h': 3600, 'm': 60, 's': 1}
    seconds = 0
    currentTime = ""

    for char in argument:
      if char.isdigit():
        currentTime += char
      elif char in units and currentTime:
        seconds += int(currentTime) * units[char]
        currentTime = ""
      
    return timedelta(seconds=seconds)

def cardEmoji(card):
  emojis = {
    "Ace of Spades": "<:AceofSpades:1331377971021217802>",
    "King of Spades": "<:KingofSpades:1331378168178802830>",
    "Queen of Spades": "<:QueenofSpades:1331378251389472871>",
    "Jack of Spades": "<:JackofSpades:1331378073429475398>",
    "10 of Spades": "<:10ofSpades:1331377871385530480>",
    "9 of Spades": "<:9ofSpades:1331377797569970278>",
    "8 of Spades": "<:8ofSpades:1331377713851662356>",
    "7 of Spades": "<:7ofSpades:1331377628585922660>",
    "6 of Spades": "<:6ofSpades:1331377553629384815>",
    "5 of Spades": "<:5ofSpades:1331377470108340254>",
    "4 of Spades": "<:4ofSpades:1331377293515292672>",
    "3 of Spades": "<:3ofSpades:1331377272623730780>",
    "2 of Spades": "<:2ofSpades:1331377197105283072>",
    "Ace of Clubs": "<:AceofClubs:1331377890075607072>",
    "King of Clubs": "<:KingofClubs:1331378103716544603>",
    "Queen of Clubs": "<:QueenofClubs:1331378189749981357>",
    "Jack of Clubs": "<:JackofClubs:1331377992688992276>",
    "10 of Clubs": "<:10ofClubs:1331377818738888814>",
    "9 of Clubs": "<:9ofClubs:1331377738354917427>",
    "8 of Clubs": "<:8ofClubs:1331377649913827339>",
    "7 of Clubs": "<:7ofClubs:1331377571547578519>",
    "6 of Clubs": "<:6ofClubs:1331377494737027225>",
    "5 of Clubs": "<:5ofClubs:1331377416202883173>",
    "4 of Clubs": "<:4ofClubs:1331377334057570437>",
    "3 of Clubs": "<:3ofClubs:1331377216462000188>",
    "2 of Clubs": "<:2ofClubs:1331377137747492884>",
    "Ace of Hearts": "<:AceofHearts:1331377948493611110>",
    "King of Hearts": "<:KingofHearts:1331378148675293256>",
    "Queen of Hearts": "<:QueenofHearts:1331378227804901428>",
    "Jack of Hearts": "<:JackofHearts:1331378041984778292>",
    "10 of Hearts": "<:10ofHearts:1331377853366927380>",
    "9 of Hearts": "<:9ofHearts:1331377777101770874>",
    "8 of Hearts": "<:8ofHearts:1331377694549475439>",
    "7 of Hearts": "<:7ofHearts:1331377611401728081>",
    "6 of Hearts": "<:6ofHearts:1331377532284698656>",
    "5 of Hearts": "<:5ofHearts:1331377450302832650>",
    "4 of Hearts": "<:4ofHearts:1331377372103966842>",
    "3 of Hearts": "<:3ofHearts:1331377257696071782>",
    "2 of Hearts": "<:2ofHearts:1331377179224703026>",
    "Ace of Diamonds": "<:AceofDiamonds:1331377914511626250>",
    "King of Diamonds": "<:KingofDiamonds:1331378128924315729>",
    "Queen of Diamonds": "<:QueenofDiamonds:1331378211120087040>",
    "Jack of Diamonds": "<:JackofDiamonds:1331378018014199828>",
    "10 of Diamonds": "<:10ofDiamonds:1331377837873303644>",
    "9 of Diamonds": "<:9ofDiamonds:1331377757644390543>",
    "8 of Diamonds": "<:8ofDiamonds:1331377677395034194>",
    "7 of Diamonds": "<:7ofDiamonds:1331377591050833961>",
    "6 of Diamonds": "<:6ofDiamonds:1331377515997958154>",
    "5 of Diamonds": "<:5ofDiamonds:1331377431566618714>",
    "4 of Diamonds": "<:4ofDiamonds:1331377355041800282>",
    "3 of Diamonds": "<:3ofDiamonds:1331377240600084621>",
    "2 of Diamonds": "<:2ofDiamonds:1331377157028577380>",
  }

  return f"{emojis.get(f"{card.value} of {card.suit}")}"
# USEFUL FUNCTIONS
def handValue(hand):
  value = 0
  aces = 0

  for card in hand:
    if card.value in ["King", "Queen", "Jack"]:
      value += 10
    elif card.value == "Ace":
      value += 11
      aces += 1
    else:
      value += int(card.value)
  
  while value > 21 and aces:
    value -= 11
    aces -= 1
  
  return value

async def updateBalance(id: int, power: int):
  async with asqlite.connect("fumo.db") as db:
    async with db.cursor() as cursor:
      await cursor.execute(
        """
        UPDATE players SET balance = balance + ? WHERE id = ?
        """, (power, id)
      )
      await db.commit()

async def checkBalance(id: int):
  """Checks a user's balance based on the given ID."""
  async with asqlite.connect("fumo.db") as db:
    async with db.cursor() as cursor:
      result = await cursor.execute(
        """
        SELECT balance FROM players WHERE id = ?
        """, (id)
      )
      row = await result.fetchone()
      return row
  
# THIS IS FOR CHECKS

class Hierarchy(commands.CheckFailure):
  pass

class NotEnoughMoney(commands.CheckFailure):
  pass

class YoureTheOwner(commands.CheckFailure):
  pass

def roleIsHigher(ctx, member, target):
  if isinstance(target, list):
    for t in target:
      if member.top_role <= t.top_role:
        raise Hierarchy()
      else:
        return
  if member.top_role <= target.top_role:
    raise Hierarchy()
  elif target == target.guild.owner:
    raise YoureTheOwner()
  return

async def lowBalance(ctx, power: int):
  result = await checkBalance(ctx.author.id)
  if result[0] < power:
    raise NotEnoughMoney()
      

  