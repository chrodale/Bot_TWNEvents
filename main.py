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

scales_emoji = "<:scales~1:1416861558822141972>"


# ------------------------------------------------
# Response controller


# Trigger on message
@bot.event
async def on_message(message):
    global currency_df

    # Make sure the message is valid
    if (
        message.author.bot
        or message.channel.id not in allowed_channels_df["Allowed_Channels"].values
    ):
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
                    "Scales": 1,
                }
                currency_df = pd.concat(
                    [currency_df, pd.DataFrame([new_row])], ignore_index=True
                )
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


# Command to add channels to the "Allowed Channels"
@bot.command()
# 993335062688972801 = Staff Role ID
@commands.has_role(993335062688972801)
async def add_channel(ctx, channel: discord.TextChannel):
    df = pd.read_csv("Allowed_Challens.csv")
    # Check if channel is on list, if no add it
    if channel.id not in df["Allowed_Channels"].values:
        df = df.append({"Allowed_Channels": channel.id}, ignore_index=True)
        df.to_csv("Allowed_Channels.csv", index=False)
        await ctx.send(f"{channel.mention} has been added")
    # If exists, let user know
    else:
        await ctx.send(f"{channel.mention} is already on the list")


# Command to remove channels from the "Allowed Channels"
@bot.command()
# 993335062688972801 = Staff Role ID
@commands.has_role(993335062688972801)
async def remove_channel(ctx, channel: discord.TextChannel):
    df = pd.read_csv("Allowed_Challens.csv")
    # Check if channel is on list, if yes remove it
    if channel.id in df["Allowed_Channels"].values:
        # Remove channel if found
        df = df[df["Allowed_Channels"] != channel.id]
        df.to_csv("Allowed_Channels.csv", index=False)
        await ctx.send(f"{channel.mention} has been removed")
    # If channel is not on list, tell user
    else:
        await ctx.send(f"{channel.mention} is not on the list")


# Command to list all channels from the "Allowed Channels"
@bot.command()
# 993335062688972801 = Staff Role ID
@commands.has_role(993335062688972801)
async def list_channels(ctx):
    try:
        df = allowed_channels_df
        if df.empty:
            ctx.send("No channels found")
        channel_mentions = []
        for channel_id in df["Allowed_Channels"]:
            channel = bot.get_channel(int(channel_id))
            if channel:
                channel_mentions.append(channel.mention)
            else:
                channel_mentions.append(f"(Unknown Channel ID: {channel_id})")

        response = "## List of Allowed Channels:\n" + "\n".join(channel_mentions)
        await ctx.send(response)
    except FileNotFoundError:
        await ctx.send("Allowed_Channels.csv not found")
    except Exception as e:
        await ctx.send(f"Error Occoured: {e}")


# use either with !balance @user for a specific user or !balance for yourself
@bot.command()
async def balance(ctx, user: discord.User):
    # if no user is specified, use the command user
    if user is None:
        user = ctx.author
    df = currency_df
    user_data = df[df["UID"] == user.id]
    # if user is found give out the balance
    if not user_data.empty:
        balance = user_data.iloc[0]["Scales"]
        balance_embed = discord.Embed(
            title=f"{user.name}'s balance",
            description=f"Your balance is {balance} {scales_emoji}",
            color=0x4FBB4F,
        )
        await ctx.send(embed=balance_embed)
    else:
        await ctx.send("**This user currently has no balance**")


# ------------------------------------------------
# Bot run

TOKEN = os.environ.get("TOKEN")
if not TOKEN:
    raise ValueError("No TOKEN found.")

bot.run(TOKEN)
