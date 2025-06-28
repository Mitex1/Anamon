# /utils/views.py
import discord

class PlayCardSelect(discord.ui.Select):
    def __init__(self, game_cog):
        player = game_cog.active_games[game_cog.current_interaction.channel.id].get_current_player()
        options = [discord.SelectOption(label=f"{card.data['name']}", value=str(card.data['card_id']), description=f"Typ: {card.data.get('card_type', 'Unbekannt').capitalize()}") for card in player.hand]
        super().__init__(placeholder="Spiele eine Karte von deiner Hand...", options=options, disabled=not options, row=1)
        self.game_cog = game_cog

    async def callback(self, interaction: discord.Interaction):
        await self.game_cog.handle_play_card(interaction, self.values[0])

class ChooseTargetSelect(discord.ui.Select):
    def __init__(self, player_state):
        options = []
        if player_state.active_pokemon:
            options.append(discord.SelectOption(label=f"Aktiv: {player_state.active_pokemon.data['name']}", value="active"))
        for i, pkm in enumerate(player_state.bench):
            if pkm:
                options.append(discord.SelectOption(label=f"Bank {i+1}: {pkm.data['name']}", value=f"bench_{i}"))
        super().__init__(placeholder="Wähle ein Ziel-Pokémon...", options=options, disabled=not options)

class AttackSelect(discord.ui.Select):
    def __init__(self, attacker):
        options = []
        if attacker.data.get('attack1_name'):
            options.append(discord.SelectOption(label=f"{attacker.data['attack1_name']} ({attacker.data.get('attack1_schaden', 0)})", value="1"))
        if attacker.data.get('attack2_name'):
            options.append(discord.SelectOption(label=f"{attacker.data['attack2_name']} ({attacker.data.get('attack2_schaden', 0)})", value="2"))
        super().__init__(placeholder="Wähle einen Angriff...", options=options, disabled=not options)

class GameView(discord.ui.View):
    def __init__(self, game_cog):
        super().__init__(timeout=600)
        self.game_cog = game_cog
        self.add_item(PlayCardSelect(game_cog))

    @discord.ui.button(label="Angreifen", style=discord.ButtonStyle.red, row=0)
    async def attack_button(self, interaction: discord.Interaction, button: discord.ui.Button):
        game = self.game_cog.active_games.get(interaction.channel.id)
        if not game or interaction.user.id != game.current_turn_player_id:
            return await interaction.response.send_message("Du bist nicht am Zug!", ephemeral=True)
        await self.game_cog.prompt_attack(interaction)

    @discord.ui.button(label="Zug beenden", style=discord.ButtonStyle.grey, row=0)
    async def end_turn_button(self, interaction: discord.Interaction, button: discord.ui.Button):
        game = self.game_cog.active_games.get(interaction.channel.id)
        if not game or interaction.user.id != game.current_turn_player_id:
            return await interaction.response.send_message("Du bist nicht am Zug!", ephemeral=True)
        await self.game_cog.end_turn(interaction)

class TargetingView(discord.ui.View):
    def __init__(self, game_cog, card_to_play):
        super().__init__(timeout=120)
        player = game_cog.active_games[game_cog.current_interaction.channel.id].get_current_player()
        target_select = ChooseTargetSelect(player)
        async def target_callback(interaction: discord.Interaction):
            await game_cog.execute_targeted_action(interaction, card_to_play, interaction.data['values'][0])
        target_select.callback = target_callback
        self.add_item(target_select)