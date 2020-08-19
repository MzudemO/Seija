#!/usr/bin/env python3

from discord.ext import commands
import aiosqlite
from aioosuapi import aioosuapi
from aioosuwebapi import aioosuwebapi
import sys
import os


from modules import first_run

from modules.connections import bot_token as bot_token
from modules.connections import osu_api_key as osu_api_key
from modules.connections import client_id as client_id
from modules.connections import client_secret as client_secret
from modules.connections import database_file as database_file

user_extensions_directory = "user_extensions"

if not os.path.exists("data"):
    print("Please configure this bot according to readme file.")
    sys.exit("data folder and it's contents are missing")
if not os.path.exists(user_extensions_directory):
    os.makedirs(user_extensions_directory)

if os.environ.get('SEIJA_PREFIX'):
    command_prefix = os.environ.get('SEIJA_PREFIX')
else:
    command_prefix = "."

first_run.create_tables()

initial_extensions = [
    "cogs.BotManagement",
    "cogs.Docs",
    "cogs.MapsetChannel",
    "cogs.MapsetGitRepo",
    "cogs.MemberManagement",
    "cogs.MemberNameSyncing",
    "cogs.MemberStatistics",
    "cogs.MemberVerification",
    "cogs.ModChecker",
    "cogs.Osu",
    "cogs.Queue",
]


class Seija(commands.Bot):
    def __init__(self, *args, **kwargs):
        super().__init__(*args, **kwargs)
        self.background_tasks = []
        self.app_version = (open(".version", "r+").read()).strip()
        self.description = f"Seija {self.app_version}"
        self.database_file = database_file
        self.osu = aioosuapi(osu_api_key)
        self.osuweb = aioosuwebapi(client_id, client_secret)

        for extension in initial_extensions:
            try:
                self.load_extension(extension)
            except Exception as e:
                print(e)
        for user_extension in os.listdir(user_extensions_directory):
            if not user_extension.endswith(".py"):
                continue
            extension_name = user_extension.replace(".py", "")
            try:
                self.load_extension(f"{user_extensions_directory}.{extension_name}")
                print(f"User extension {extension_name} loaded")
            except Exception as e:
                print(e)

    async def start(self, *args, **kwargs):
        self.db = await aiosqlite.connect(self.database_file)

        await super().start(*args, **kwargs)

    async def close(self):
        # Cancel all Task object generated by cogs.
        # This prevents any task still running due to having long sleep time.
        for task in self.background_tasks:
            task.cancel()

        # Close osu web api session
        await self.osuweb.close()

        # Close connection to the database
        if self.db:
            await self.db.close()

        # Run actual discord.py close.
        # await super().close()

        # for now let's just quit() since the thing above does not work :c
        quit()

    async def on_ready(self):
        print("Logged in as")
        print(self.user.name)
        print(self.user.id)
        print("------")
        await first_run.add_admins(self)


client = Seija(command_prefix=command_prefix)
client.run(bot_token)
