# cogs/game_logic.py
import discord
from discord.ext import commands
from discord import app_commands
import random
import database as db
from utils.views import GameView, TargetingView, AttackSelect
from collections import Counter

# --- Klassen: InGameCard, PlayerState, GameState (bleiben wie im letzten Code) ---
class InGameCard:
    def __init__(self, card_data: dict):
        self.data = card_data; self.attached_energy = []; self.damage_counters = 0
    @property
    def current_hp(self): return self.data.get('kp', 0) - self.damage_counters
    def is_knocked_out(self): return self.current_hp <= 0

class PlayerState:
    def __init__(self, user, deck: list):
        self.user = user; self.deck = [InGameCard(c) for c in deck if c]; random.shuffle(self.deck)
        self.hand = []; self.prize_cards = []; self.active_pokemon: InGameCard = None
        self.bench = [None] * 5; self.discard_pile = []
        self.has_attached_energy_this_turn = False; self.has_played_supporter_this_turn = False

class GameState:
    def __init__(self, player1: PlayerState, player2: PlayerState):
        self.players = {p.user.id: p for p in [player1, player2]}; self.current_turn_player_id = player1.user.id
        self.turn_number = 1; self.game_over = False; self.winner = None; self.message: discord.Message = None
    def switch_turn(self):
        self.get_current_player().has_attached_energy_this_turn = False
        self.get_current_player().has_played_supporter_this_turn = False
        other_ids = list(self.players.keys()); other_ids.remove(self.current_turn_player_id)
        self.current_turn_player_id = other_ids[0]; self.turn_number += 1
    def get_current_player(self) -> PlayerState: return self.players[self.current_turn_player_id]
    def get_opponent(self) -> PlayerState:
        other_ids = list(self.players.keys()); other_ids.remove(self.current_turn_player_id)
        return self.players[other_ids[0]]
# --- Ende der Klassen ---

class GameLogic(commands.Cog):
    def __init__(self, bot: commands.Bot):
        self.bot = bot
        self.active_games = {}
        self.current_interaction: discord.Interaction = None

    async def create_game_embed(self, game: GameState):
        player = game.get_current_player()
        opponent = game.get_opponent()
        embed = discord.Embed(title="Pokémon TCG", color=discord.Color.gold())
        
        p_active_name = player.active_pokemon.data['name'] if player.active_pokemon else "Leer"
        p_hp = f"({player.active_pokemon.current_hp}/{player.active_pokemon.data['kp']} KP)" if player.active_pokemon else ""
        embed.add_field(name=f"Feld von {player.user.display_name}", value=f"**Aktiv:** {p_active_name} {p_hp}\n**Hand:** {len(player.hand)} | **Preise:** {len(player.prize_cards)} | **Deck:** {len(player.deck)}", inline=False)
        
        o_active_name = opponent.active_pokemon.data['name'] if opponent.active_pokemon else "Leer"
        o_hp = f"({opponent.active_pokemon.current_hp}/{opponent.active_pokemon.data['kp']} KP)" if opponent.active_pokemon else ""
        embed.add_field(name=f"Feld von {opponent.user.display_name}", value=f"**Aktiv:** {o_active_name} {o_hp}\n**Hand:** {len(opponent.hand)} | **Preise:** {len(opponent.prize_cards)} | **Deck:** {len(opponent.deck)}", inline=False)
        
        embed.set_footer(text=f"Runde {game.turn_number} - {game.get_current_player().user.display_name} ist am Zug.")
        return embed

    @app_commands.command(name="start_spiel", description="Starte ein Spiel.")
    async def start_game_cmd(self, interaction: discord.Interaction, gegner: discord.Member):
        if gegner.bot or gegner.id == interaction.user.id:
            return await interaction.response.send_message("Ungültiger Gegner.", ephemeral=True)
        if interaction.channel.id in self.active_games:
            return await interaction.response.send_message("In diesem Kanal läuft bereits ein Spiel!", ephemeral=True)

        p1_cards = await db.get_user_cards(interaction.user.id)
        p2_cards = await db.get_user_cards(gegner.id)
        if len(p1_cards) < 7 or len(p2_cards) < 7:
            return await interaction.response.send_message("Beide Spieler benötigen mind. 7 erstellte Karten.", ephemeral=True)

        await interaction.response.defer()
        p1_deck = [await db.get_card_by_id(c['card_id']) for c in p1_cards]
        p2_deck = [await db.get_card_by_id(c['card_id']) for c in p2_cards]

        game = GameState(PlayerState(interaction.user, p1_deck), PlayerState(gegner, p2_deck))
        self.active_games[interaction.channel.id] = game

        for p in game.players.values():
            p.hand = [p.deck.pop() for _ in range(7)]
            p.prize_cards = [p.deck.pop() for _ in range(6)]
            basic_pokemon = [c for c in p.hand if c.data.get('card_type') == 'pokemon' and c.data.get('stage') == 1]
            if basic_pokemon:
                p.active_pokemon = basic_pokemon[0]
                p.hand.remove(basic_pokemon[0])
        
        await interaction.followup.send(f"Spiel zwischen {interaction.user.mention} und {gegner.mention} beginnt!")
        game.message = await interaction.followup.send("Spielfeld wird aufgebaut...")
        await self.update_game_state(interaction.channel.id, f"Setup beendet. {game.get_current_player().user.display_name} beginnt!")

    async def update_game_state(self, channel_id: int, status_message: str = None):
        game = self.active_games.get(channel_id)
        if not game: return
        if game.game_over: return await self.handle_game_over(channel_id)

        embed = await self.create_game_embed(game)
        self.current_interaction = game.message
        view = GameView(self)
        
        content = status_message if status_message else f"Runde {game.turn_number} - **{game.get_current_player().user.display_name}** ist am Zug."
        await game.message.edit(content=content, embed=embed, view=view)

    async def handle_play_card(self, interaction: discord.Interaction, card_id_str: str):
        self.current_interaction = interaction
        game = self.active_games[interaction.channel.id]
        player = game.get_current_player()
        card = next((c for c in player.hand if str(c.data['card_id']) == card_id_str), None)

        if card.data['card_type'] == 'energy':
            if player.has_attached_energy_this_turn:
                return await interaction.response.send_message("Bereits Energie angelegt!", ephemeral=True)
            view = TargetingView(self, card)
            return await interaction.response.send_message("Wähle ein Ziel:", view=view, ephemeral=True)
        
        if card.data['card_type'] == 'pokemon':
            if None in player.bench:
                player.bench[player.bench.index(None)] = card
                player.hand.remove(card)
                await interaction.response.defer()
            else: return await interaction.response.send_message("Bank ist voll!", ephemeral=True)

        await self.update_game_state(interaction.channel.id, f"{player.user.display_name} hat {card.data['name']} gespielt.")

    async def execute_targeted_action(self, interaction: discord.Interaction, card, target_str: str):
        game = self.active_games[interaction.channel.id]
        player = game.get_current_player()
        target = player.active_pokemon if target_str == 'active' else player.bench[int(target_str.split('_')[1])]
        
        if card.data['card_type'] == 'energy':
            target.attached_energy.append(card)
            player.hand.remove(card)
            player.has_attached_energy_this_turn = True
        
        await interaction.response.edit_message(content=f"Karte an {target.data['name']} angelegt.", view=None)
        await self.update_game_state(interaction.channel.id)

    async def prompt_attack(self, interaction: discord.Interaction):
        self.current_interaction = interaction
        game = self.active_games[interaction.channel.id]
        attacker = game.get_current_player().active_pokemon
        if not attacker: return await interaction.response.send_message("Kein aktives Pokémon!", ephemeral=True)

        if not attacker.data.get('attack2_name'):
            await interaction.response.defer()
            return await self.execute_attack(interaction, "1")
        
        view = discord.ui.View()
        select = AttackSelect(attacker)
        async def cb(inter: discord.Interaction):
            await inter.response.edit_message(content="Angriff ausgewählt...", view=None)
            await self.execute_attack(inter, inter.data['values'][0])
        select.callback = cb
        view.add_item(select)
        await interaction.response.send_message("Wähle einen Angriff:", view=view, ephemeral=True)

    async def execute_attack(self, interaction: discord.Interaction, attack_num: str):
        game = self.active_games[interaction.channel.id]
        player, opponent = game.get_current_player(), game.get_opponent()
        attacker, defender = player.active_pokemon, opponent.active_pokemon
        
        # Energieprüfung
        cost = attacker.data.get(f'attack{attack_num}_cost', [])
        if len(attacker.attached_energy) < len(cost):
             return await interaction.followup.send("Nicht genug Energie!", ephemeral=True)

        damage = attacker.data[f'attack{attack_num}_schaden']
        if defender.data.get('weakness_typ') == attacker.data.get('pokemon_typ'): damage *= 2
        if defender.data.get('resistance_typ') == attacker.data.get('pokemon_typ'): damage = max(0, damage - defender.data.get('resistance_value', 0))
        defender.damage_counters += damage
        status = f"{attacker.data['name']} greift {defender.data['name']} an und fügt {damage} Schaden zu!"

        if defender.is_knocked_out():
            status += f"\n**{defender.data['name']} wurde besiegt!**"
            player.discard_pile.append(defender)
            for e in defender.attached_energy: player.discard_pile.append(e)
            
            if player.prize_cards:
                player.hand.append(player.prize_cards.pop())
                status += f"\n{player.user.display_name} zieht eine Preiskarte."
                if not player.prize_cards:
                    game.game_over = True; game.winner = player.user
            
            opponent.active_pokemon = None
            if not any(p for p in opponent.bench if p):
                game.game_over = True; game.winner = player.user
            else:
                for i, pkm in enumerate(opponent.bench):
                    if pkm: opponent.active_pokemon = pkm; opponent.bench[i] = None; break
                status += f"\n{opponent.user.display_name} setzt {opponent.active_pokemon.data['name']} als aktives Pokémon ein."
        
        if not game.game_over:
            await self.end_turn(interaction, is_attack=True, status_message=status)
        else:
            await self.update_game_state(interaction.channel.id, status)

    async def end_turn(self, interaction: discord.Interaction, is_attack=False, status_message: str = ""):
        if not is_attack: await interaction.response.defer()
        game = self.active_games[interaction.channel.id]
        game.switch_turn()
        new_player = game.get_current_player()
        
        if not new_player.deck:
            game.game_over = True; game.winner = game.get_opponent().user
            status_message += f"\n{new_player.user.display_name} kann keine Karte ziehen und verliert!"
        else:
            new_player.hand.append(new_player.deck.pop())
            status_message += f"\nDer Zug geht an {new_player.user.display_name}. Er/Sie zieht eine Karte."
        
        await self.update_game_state(interaction.channel.id, status_message)

    async def handle_game_over(self, channel_id):
        game = self.active_games.get(channel_id)
        embed = discord.Embed(title="Spiel beendet!", description=f"🏆 **{game.winner.display_name}** hat gewonnen! 🏆", color=discord.Color.gold())
        await game.message.edit(content="Das Spiel ist vorbei.", embed=embed, view=None)
        del self.active_games[channel_id]

async def setup(bot: commands.Bot):
    await bot.add_cog(GameLogic(bot))