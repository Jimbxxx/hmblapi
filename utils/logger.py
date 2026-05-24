import discord
import os

from utils.database import db

# -------------------------
# CHANNEL IDS
# -------------------------
TEAM_LOG = int(os.getenv("TEAM_LOG_CHANNEL_ID", 0))
DIVISION_LOG = int(os.getenv("DIVISION_LOG_CHANNEL_ID", 0))
MATCH_LOG = int(os.getenv("MATCH_LOG_CHANNEL_ID", 0))
TABLE_LOG = int(os.getenv("TABLE_LOG_CHANNEL_ID", 0))
PLAYER_LOG = int(os.getenv("PLAYER_LOG_CHANNEL_ID", 0))
TRANSFER_LOG = int(os.getenv("TRANSFER_LOG_CHANNEL_ID", 0))
SEASON_LOG = int(os.getenv("SEASON_LOG_CHANNEL_ID", 0))
PANEL_LOG = int(os.getenv("PANEL_LOG_CHANNEL_ID", 0))
SYSTEM_LOG = int(os.getenv("SYSTEM_LOG_CHANNEL_ID", 0))


# -------------------------
# CATEGORY ROUTING
# -------------------------
LOG_CHANNELS = {
    "team": TEAM_LOG,
    "division": DIVISION_LOG,
    "match": MATCH_LOG,
    "table": TABLE_LOG,
    "player": PLAYER_LOG,
    "transfer": TRANSFER_LOG,
    "season": SEASON_LOG,
    "panel": PANEL_LOG,
    "system": SYSTEM_LOG
}


# -------------------------
# MAIN LOGGER
# -------------------------
async def log(bot, category: str, title: str, description: str, color=0xf39c12):
    """
    Sends a structured embed log to the correct channel
    """

    channel_id = LOG_CHANNELS.get(category)

    if not channel_id:
        return  # silently ignore if misconfigured

    channel = bot.get_channel(channel_id)
    if not channel:
        return

    embed = discord.Embed(
        title=title,
        description=description,
        color=color
    )

    embed.set_footer(text=f"Category: {category}")

    try:
        await channel.send(embed=embed)
    except Exception as e:
        print(f"[LOGGER ERROR] {e}")


# -------------------------
# QUICK WRAPPERS (optional convenience)
# -------------------------
async def log_team(bot, title, description):
    await log(bot, "team", title, description)

async def log_division(bot, title, description):
    await log(bot, "division", title, description)

async def log_match(bot, title, description):
    await log(bot, "match", title, description)

async def log_system(bot, title, description):
    await log(bot, "system", title, description)