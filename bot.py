from requests import put, delete
from os import environ

from requests.api import request

DISCORD_API_ENDPOINT = "https://discord.com/api/v6"
DISCORD_BOT_TOKEN = environ["DISCORD_BOT_TOKEN"]
DISCORD_GUILD_ID = environ["DISCORD_GUILD_ID"]
DISCORD_ROLE_ID = environ["DISCORD_ROLE_ID"]


def bot_request(url, request_type):
    if request_type == "put":
        func = put
    if request_type == "delete":
        func = delete

    headers = {
        "Content-Type": "application/x-www-form-urlencoded",
        "Accept": "application/json",
        "Authorization": f"Bot {DISCORD_BOT_TOKEN}",
    }
    r = func(f"{DISCORD_API_ENDPOINT}{url}", headers=headers)
    r.raise_for_status()

    return True


def add_role(discord_id):
    bot_request(
        f"/guilds/{DISCORD_GUILD_ID}/members/{discord_id}/roles/{DISCORD_ROLE_ID}",
        "put",
    )


def remove_role(discord_id):
    bot_request(
        f"/guilds/{DISCORD_GUILD_ID}/members/{discord_id}/roles/{DISCORD_ROLE_ID}",
        "delete",
    )
