import os
import random
import discord
from discord.ext import commands
import pandas as pd

global halloween_df

# ------------------------------------------------
# Setup

intents = discord.Intents.default()
intents.message_content = True

bot = commands.Bot(command_prefix="", intents=intents)

@bot.event
async def on_ready():
    print(f"{bot.user} has logged in.")

halloween_df = pd.read_csv(r"Drive Sync/TWN_Halloween_26.csv")

halloween_df["UID"] = halloween_df["UID"].astype(int)
halloween_df["Candy_Scales"] = halloween_df["Candy_Scales"].astype(int)

# ------------------------------------------------
# Response controller

@bot.event
async def on_message(message):
    global halloween_df
    if message.author.bot:
        return
    if "trick or treat" in message.content.lower():
        
        roll = random.randint(1, 2)
        
        if roll == 1:
            response = "You have been tricked! Your candy count has increased."

            if message.author.id not in halloween_df["UID"].values:

                new_row = {
                    "UID": message.author.id,
                    "Username": message.author.name,
                    "Candy_Scales": 1
                }
                
                halloween_df = pd.concat([halloween_df, pd.DataFrame([new_row])], ignore_index=True)
                halloween_df.to_csv(r"Drive Sync/TWN_Halloween_26.csv")

            else:

                halloween_df.loc[halloween_df["UID"] == message.author.id, "Candy_Scales"] += 1
                halloween_df.to_csv(r"Drive Sync/TWN_Halloween_26.csv")
    
        else: 
            response = "You got a treat! (But no candy)"

            # insert treat response here
    
        await message.channel.send(response)
        
    await bot.process_commands(message)


# ------------------------------------------------
# Commands

@bot.command()
async def ping(ctx):
    await ctx.send("pong!")

# ------------------------------------------------
# Bot run

TOKEN = os.environ.get("TOKEN")
if not TOKEN:
    raise ValueError("No TOKEN found. Set the TOKEN environment variable.")

bot.run(TOKEN)
