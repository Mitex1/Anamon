# /cogs/card_creator.py
import discord
from discord.ext import commands
from discord import app_commands
import database as db
import json
from utils.card_generator import generate_card_image

class CardCreator(commands.Cog):
    def __init__(self, bot: commands.Bot):
        self.bot = bot

    @app_commands.command(name="erschaffe_pokemon", description="Erstelle eine neue Pokémon-Karte.")
    @app_commands.describe(
        name="Name", kp="Kraftpunkte", pokemon_typ="z.B. Feuer", stage="1 für Basis", bild_url="Direkte Bild-URL",
        attack1_name="Angriff 1", attack1_schaden="Schaden 1", attack1_cost="Kosten, z.B. Feuer,Farblos",
        attack2_name="[Opt.] Angriff 2", attack2_schaden="[Opt.] Schaden 2", attack2_cost="[Opt.] Kosten 2",
        weakness_typ="Schwäche", resistance_typ="Resistenz", resistance_value="Resistenzwert",
        retreat_cost="Rückzug", illustrator="Illustrator", card_number="Kartennr.", evolves_from="[Opt.] Entwickelt aus"
    )
    async def create_pokemon(self, interaction: discord.Interaction, name: str, kp: int, pokemon_typ: str, stage: int, bild_url: str,
                             attack1_name: str, attack1_schaden: int, attack1_cost: str,
                             attack2_name: str = None, attack2_schaden: int = 0, attack2_cost: str = None,
                             weakness_typ: str = None, resistance_typ: str = None, resistance_value: int = 0, 
                             retreat_cost: int = 0, illustrator: str = "Bot User", card_number: str = "001/100", evolves_from: str = None):
        
        try:
            parsed_cost1 = json.dumps([c.strip() for c in attack1_cost.split(',')]) if attack1_cost else None
            parsed_cost2 = json.dumps([c.strip() for c in attack2_cost.split(',')]) if attack2_cost else None
        except: return await interaction.response.send_message("Fehler bei Angriffskosten.", ephemeral=True)

        card_data = {
            "user_id": interaction.user.id, "name": name, "card_type": "pokemon", "kp": kp,
            "pokemon_typ": pokemon_typ, "stage": stage, "evolves_from": evolves_from, "bild_url": bild_url,
            "attack1_name": attack1_name, "attack1_schaden": attack1_schaden, "attack1_cost": parsed_cost1,
            "attack2_name": attack2_name, "attack2_schaden": attack2_schaden, "attack2_cost": parsed_cost2,
            "weakness_typ": weakness_typ, "resistance_typ": resistance_typ, "resistance_value": resistance_value,
            "retreat_cost": retreat_cost, "illustrator": illustrator, "card_number": card_number
        }
        card_id = await db.add_card(card_data)
        await interaction.response.send_message(f"Pokémon-Karte **{name}** (ID: {card_id}) wurde erstellt!", ephemeral=True)
    
    @app_commands.command(name="karte_zeigen", description="Zeigt eine erstellte Karte an.")
    async def show_card(self, interaction: discord.Interaction, karten_id: int):
        await interaction.response.defer()
        card_data = await db.get_card_by_id(karten_id)
        if not card_data:
            return await interaction.followup.send("Karte nicht gefunden.", ephemeral=True)
        
        image_file = await generate_card_image(card_data)
        file = discord.File(fp=image_file, filename=f"card_{karten_id}.png")
        await interaction.followup.send(file=file)

async def setup(bot: commands.Bot):
    await bot.add_cog(CardCreator(bot))