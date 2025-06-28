# main.py
import discord
from discord.ext import commands
import os
import asyncio
import config
import database as db

class PokemonBot(commands.Bot):
    def __init__(self):
        intents = discord.Intents.default()
        intents.message_content = True
        intents.members = True
        super().__init__(command_prefix="!", intents=intents)

    async def setup_hook(self):
        await db.initialize()
        print("Datenbank initialisiert.")

        for filename in os.listdir('./cogs'):
            if filename.endswith('.py') and not filename.startswith('_'):
                try:
                    await self.load_extension(f'cogs.{filename[:-3]}')
                    print(f"Cog '{filename[:-3]}' geladen.")
                except Exception as e:
                    print(f"Fehler beim Laden von Cog {filename[:-3]}: {e}")
        
        synced = await self.tree.sync()
        print(f"{len(synced)} Slash-Befehle synchronisiert.")

    async def on_ready(self):
        print(f'Eingeloggt als {self.user}')
        await self.change_presence(activity=discord.Game(name="/start_spiel"))

async def main():
    bot = PokemonBot()
    await bot.start(config.DISCORD_TOKEN)

if __name__ == "__main__":
    try:
        asyncio.run(main())
    except KeyboardInterrupt:
        print("Bot wird heruntergefahren.")