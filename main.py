import os
import random
import discord
from discord.ext import commands
import pandas as pd
from flask import Flask
from threading import Thread

# ------------------------------------------------
# Keep-alive (for UptimeRobot)

app = Flask("")


@app.route("/")
def home():
    return "Bot is running!"


def run_webserver():
    app.run(host="0.0.0.0", port=8080)


# ------------------------------------------------
# Setup

intents = discord.Intents.default()
intents.message_content = True

bot = commands.Bot(command_prefix=">", intents=intents)


@bot.event
async def on_ready():
    print(f"{bot.user} has logged in.")


currency_df = pd.read_csv("/root/data/Currency.csv")
allowed_channels_df = pd.read_csv("/root/data/Allowed_Channels.csv")

currency_df["UID"] = currency_df["UID"].astype(int)
currency_df["Scales"] = currency_df["Scales"].astype(int)

scales_emoji = "<:TWN_Scales:1416861558822141972>"

# House rarity lists (used to modify the scale reward when users send emojis/words)
COMMON_HOUSES = ["ghost", "pumpkin", "moon"]
RARE_HOUSES = ["web", "cat"]

# Track consecutive overdraw attempts per user in-memory (resets on successful change / restart)
overdraw_attempts = {}

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
        print("The command was not send in an allowed channel")
        return
    elif "trick or treat" in message.content.lower():

        # Determine how many scales to give based on rarity keywords / emoji names
        content_lower = message.content.lower()
        common_count = sum(content_lower.count(k) for k in COMMON_HOUSES)
        rare_count = sum(content_lower.count(k) for k in RARE_HOUSES)

        # Base reward is 1. Each common house found gives +1. Each rare house gives +3.
        scales_gain = 1 + common_count * 1 + rare_count * 3

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
                    "Scales": int(scales_gain),
                }
                currency_df = pd.concat(
                    [currency_df, pd.DataFrame([new_row])], ignore_index=True
                )
                currency_df.to_csv("/root/data/Currency.csv", index=False)

            else:
                # Update existing row
                currency_df.loc[
                    currency_df["UID"] == message.author.id, "Scales"
                ] += int(scales_gain)
                currency_df.to_csv("/root/data/Currency.csv", index=False)

        # Treat:
        else:
            halloween_role = message.guild.get_role(1431723739317534760)

            if any(role.id == 1431723739317534760 for role in message.author.roles):
                response = "You got a treat! You traded in an extra Halloween role for candy scales!"
                currency_df.loc[
                    currency_df["UID"] == message.author.id, "Scales"
                ] += int(scales_gain)
                currency_df.to_csv("/root/data/Currency.csv", index=False)

            else:
                response = "You got a treat! The Halloween role is now yours!"
                await message.author.add_roles(halloween_role)

        await message.channel.send(response)
    await bot.process_commands(message)


# Command to add channels to the "Allowed Channels"
@bot.command()
# 993335062688972801 = Staff Role ID
@commands.has_role(993335062688972801)
async def add_channel(ctx, channel: discord.TextChannel):
    df = pd.read_csv("/root/data/Allowed_Channels.csv")
    # Check if channel is on list, if no add it
    if channel.id not in df["Allowed_Channels"].values:
        new_row = pd.DataFrame([{"Allowed_Channels": channel.id}])
        df = pd.concat([df, new_row], ignore_index=True)
        df.to_csv("/root/data/Allowed_Channels.csv", index=False)
        await ctx.send(f"{channel.mention} has been added")
    # If exists, let user know
    else:
        await ctx.send(f"{channel.mention} is already on the list")


# Command to remove channels from the "Allowed Channels"
@bot.command()
# 993335062688972801 = Staff Role ID
@commands.has_role(993335062688972801)
async def remove_channel(ctx, channel: discord.TextChannel):
    global allowed_channels_df  # <-- Use the global DataFrame

    # Check if channel is on list, if yes remove it
    if channel.id in allowed_channels_df["Allowed_Channels"].values:
        # Remove channel by filtering the global DataFrame
        allowed_channels_df = allowed_channels_df[
            allowed_channels_df["Allowed_Channels"] != channel.id
        ]

        allowed_channels_df.to_csv("/root/data/Allowed_Channels.csv", index=False)
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


@bot.command()
async def pinginging(ctx):
    await ctx.send("pongongong")


# use either with !balance @user for a specific user or !balance for yourself
@bot.command()
async def balance(ctx, user: discord.User = None):
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


# Command to give scales to a user
@bot.command()
# 993335062688972801 = Staff Role ID
@commands.has_role(993335062688972801)
async def give(ctx, user: discord.User, amount: int):
    """Give a specified user `amount` scales and save to Currency.csv.

    Usage: >give @user 10
    """
    global currency_df

    # Basic validation
    if amount <= 0:
        await ctx.send("Amount must be a positive integer.")
        return

    try:
        # If user has no record, create one
        if user.id not in currency_df["UID"].values:
            new_row = {"UID": user.id, "Username": user.name, "Scales": amount}
            currency_df = pd.concat(
                [currency_df, pd.DataFrame([new_row])], ignore_index=True
            )
        else:
            # Update existing row
            currency_df.loc[currency_df["UID"] == user.id, "Scales"] += amount

        # Keep types consistent and write file
        currency_df["UID"] = currency_df["UID"].astype(int)
        currency_df["Scales"] = currency_df["Scales"].astype(int)
        currency_df.to_csv("/root/data/Currency.csv", index=False)

        new_balance = int(
            currency_df.loc[currency_df["UID"] == user.id, "Scales"].iloc[0]
        )
        embed = discord.Embed(
            title=f"Added scales to {user.name}",
            description=f"Added {amount} {scales_emoji} to {user.mention}'s balance.\nNew balance: {new_balance} {scales_emoji}",
        )

        await ctx.send(embed=embed)

    except Exception as e:
        await ctx.send(f"Failed to update balance: {e}")


# Command to deduct scales from a user (staff only)
@bot.command()
# 993335062688972801 = Staff Role ID
@commands.has_role(993335062688972801)
async def deduct(ctx, user: discord.User, amount: int):
    """Remove a specified amount of scales from a user and save to Currency.csv.

    Usage: >deduct @user 5
    If the deduction exceeds the user's balance, their balance will be floored at 0.
    """
    global currency_df

    if amount <= 0:
        await ctx.send("Amount must be a positive integer.")
        return

    try:
        # If the user has no record, treat as zero balance
        if user.id not in currency_df["UID"].values:
            await ctx.send("The user is out of scales")
            return

        current = int(currency_df.loc[currency_df["UID"] == user.id, "Scales"].iloc[0])

        # If the user already has zero, inform and do nothing
        if current == 0:
            await ctx.send("The user is out of scales")
            return

        # If attempting to deduct more than they have, set balance to zero and notify
        if amount > current:
            currency_df.loc[currency_df["UID"] == user.id, "Scales"] = 0
            # Keep types consistent and write file
            currency_df["UID"] = currency_df["UID"].astype(int)
            currency_df["Scales"] = currency_df["Scales"].astype(int)
            currency_df.to_csv("/root/data/Currency.csv", index=False)
            await ctx.send(
                "You deducted more than the user has! The users balance has been set to 0"
            )
            return

        # Normal deduction
        new_balance = current - amount
        currency_df.loc[currency_df["UID"] == user.id, "Scales"] = new_balance
        # Keep types consistent and write file
        currency_df["UID"] = currency_df["UID"].astype(int)
        currency_df["Scales"] = currency_df["Scales"].astype(int)
        currency_df.to_csv("/root/data/Currency.csv", index=False)
        embed = discord.Embed(
            title=f"Removed scales from {user.name}",
            description=f"Removed {amount} {scales_emoji} from {user.mention}.\nNew balance: {new_balance} {scales_emoji}",
        )

        await ctx.send(embed=embed)

    except Exception as e:
        await ctx.send(f"Failed to update balance: {e}")


# Leaderboard command with reaction-based pagination (shows all users, 10 per page)
@bot.command()
async def lb(ctx):
    """Show the leaderboard (all users) with reaction pagination, 10 entries per page."""
    global currency_df

    try:
        # include all users (including zero balances)
        df_sorted = currency_df.sort_values("Scales", ascending=False)
        if df_sorted.empty:
            await ctx.send("No leaderboard data available.")
            return

        rows = list(df_sorted.to_dict("records"))
        page_size = 10
        total = len(rows)
        total_pages = (total + page_size - 1) // page_size

        def make_embed(page_index: int) -> discord.Embed:
            start = page_index * page_size
            end = min(start + page_size, total)
            lines = []
            for i, row in enumerate(rows[start:end], start=start + 1):
                uid = int(row.get("UID", 0))
                stored_name = str(row.get("Username", "Unknown"))
                member = None
                try:
                    if ctx.guild:
                        member = ctx.guild.get_member(uid)
                except Exception:
                    member = None
                display = member.display_name if member else stored_name
                scales = int(row.get("Scales", 0))
                lines.append(f"{i}. {display} — {scales} {scales_emoji}")

            embed = discord.Embed(
                title=f"Scales Leaderboard",
                description="\n".join(lines) if lines else "No entries",
                color=0xFFD700,
            )
            embed.set_footer(text=f"Page {page_index+1}/{total_pages}")
            return embed

        # send first page
        page = 0
        message = await ctx.send(embed=make_embed(page))

        # if only one page, we're done
        if total_pages <= 1:
            return

        # add controls
        LEFT = "◀️"
        RIGHT = "▶️"
        for emoji in (LEFT, RIGHT):
            try:
                await message.add_reaction(emoji)
            except Exception:
                # ignore reaction failures
                pass

        def check(reaction, user):
            return (
                user == ctx.author
                and reaction.message.id == message.id
                and str(reaction.emoji) in (LEFT, RIGHT)
            )

        # wait for reactions and update embed accordingly
        while True:
            try:
                reaction, user = await bot.wait_for(
                    "reaction_add", timeout=120.0, check=check
                )
            except Exception:
                try:
                    await message.clear_reactions()
                except Exception:
                    pass
                break

            emoji = str(reaction.emoji)
            try:
                # remove the user's reaction to keep the UI clean (best-effort)
                await message.remove_reaction(reaction.emoji, user)
            except Exception:
                pass

            if emoji == RIGHT:
                page = (page + 1) % total_pages
                try:
                    await message.edit(embed=make_embed(page))
                except Exception:
                    pass
            elif emoji == LEFT:
                page = (page - 1) % total_pages
                try:
                    await message.edit(embed=make_embed(page))
                except Exception:
                    pass

    except Exception as e:
        await ctx.send(f"Failed to build leaderboard: {e}")


# ------------------------------------------------
# Bot run

if __name__ == "__main__":
    thread = Thread(target=run_webserver, daemon=True)
    thread.start()

    bot.run("SECRET SHHHHHHHHH")
