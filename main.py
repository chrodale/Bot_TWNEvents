import os
import random
import discord
from discord.ext import commands
import pandas as pd

# ------------------------------------------------
# Setup

intents = discord.Intents.default()
intents.message_content = True

bot = commands.Bot(command_prefix="", intents=intents)

@bot.event
async def on_ready():
    print(f"{bot.user} has logged in.")

currency_df = pd.read_csv("Currency.csv")
allowed_channels_df = pd.read_csv("Allowed_Channels.csv")

currency_df["UID"] = currency_df["UID"].astype(int)
currency_df["Scales"] = currency_df["Scales"].astype(int)

# ------------------------------------------------
# Response controller

# Trigger on message
@bot.event
async def on_message(message):
    global currency_df
    
    # Make sure the message is valid
    if message.author.bot or message.channel.id not in allowed_channels_df["Allowed_Channels"].values:
        return
    elif "trick or treat" in message.content.lower():

        # Determine if trick or treat
        roll = random.randint(1, 2)

        # Trick: 
        if roll == 1:
            response = "You have been tricked! Your candy count has increased."

            if message.author.id not in currency_df["UID"].values:
                # Create a new row
                new_row = {
                    "UID": message.author.id,
                    "Username": message.author.name,
                    "Scales": 1
                }
                currency_df = pd.concat([currency_df, pd.DataFrame([new_row])], ignore_index=True)
                currency_df.to_csv("Currency.csv")

            else:
                # Update existing row
                currency_df.loc[currency_df["UID"] == message.author.id, "Scales"] += 1
                currency_df.to_csv("Currency.csv")

        # Treat:
        else: 
            response = "You got a treat! (But no candy)"

            # update treat response here
    
        await message.channel.send(response)
    await bot.process_commands(message)

# ------------------------------------------------
# Bot run

TOKEN = os.environ.get("TOKEN")
if not TOKEN:
    raise ValueError("No TOKEN found.")

bot.run(TOKEN)
