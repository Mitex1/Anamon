# /utils/card_generator.py
from PIL import Image, ImageDraw, ImageFont
import requests
from io import BytesIO

TEMPLATE_PATH = "assets/template.png"

# Angepasst an deinen Screenshot!
FONT_FILES = {
    "name": "assets/gillsans_condensed_bold.otf",
    "evolution": "assets/gillsans_bold_italic.otf",
    "kp": "assets/futura_medium_bold.otf",
    "power_name": "assets/gillsans_condensed_bold.otf",
    "power_text": "assets/gillsans_regular.otf",
    "attack_name": "assets/gillsans_condensed_bold.otf",
    "attack_damage": "assets/gillsans_regular.otf",
    "illustrator": "assets/futura_medium_italic.ttf",
    "card_number": "assets/futura_medium.otf",
}

# Passe diese Koordinaten an dein Template an!
NAME_POS = (60, 55); NAME_FONT_SIZE = 38
EVOLUTION_POS = (140, 35); EVOLUTION_FONT_SIZE = 18
KP_POS = (480, 55); KP_FONT_SIZE = 38
BILD_POS = (55, 115); BILD_SIZE = (410, 230)
ATTACK1_NAME_POS = (70, 420); ATTACK_FONT_SIZE = 24
ATTACK1_DMG_POS = (450, 420); ATTACK_DMG_FONT_SIZE = 30
ILLUSTRATOR_POS = (70, 520); ILLUSTRATOR_FONT_SIZE = 16
CARD_NUM_POS = (400, 520); CARD_NUM_FONT_SIZE = 16

def draw_text_with_spacing(draw, pos, text, font, fill, spacing=0):
    x, y = pos
    for char in text:
        draw.text((x, y), char, font=font, fill=fill)
        try:
            x += font.getlength(char) + spacing
        except AttributeError:
            x += font.getsize(char)[0] + spacing

async def generate_card_image(card_data: dict) -> BytesIO:
    card_bg = Image.open(TEMPLATE_PATH).convert("RGBA")
    draw = ImageDraw.Draw(card_bg)

    try:
        response = requests.get(card_data.get('bild_url', ''), stream=True)
        response.raise_for_status()
        pokemon_img = Image.open(BytesIO(response.content)).convert("RGBA").resize(BILD_SIZE, Image.Resampling.LANCZOS)
        card_bg.paste(pokemon_img, BILD_POS, pokemon_img if pokemon_img.mode == 'RGBA' else None)
    except: pass

    try:
        name_font = ImageFont.truetype(FONT_FILES["name"], NAME_FONT_SIZE)
        evolution_font = ImageFont.truetype(FONT_FILES["evolution"], EVOLUTION_FONT_SIZE)
        kp_font = ImageFont.truetype(FONT_FILES["kp"], KP_FONT_SIZE)
        attack_name_font = ImageFont.truetype(FONT_FILES["attack_name"], ATTACK_FONT_SIZE)
        attack_damage_font = ImageFont.truetype(FONT_FILES["attack_damage"], ATTACK_DMG_FONT_SIZE)
        illustrator_font = ImageFont.truetype(FONT_FILES["illustrator"], ILLUSTRATOR_FONT_SIZE)
        card_num_font = ImageFont.truetype(FONT_FILES["card_number"], CARD_NUM_FONT_SIZE)
    except IOError as e:
        print(f"Schriftart-Fehler: {e}.")
        name_font = ImageFont.load_default()

    draw.text(NAME_POS, card_data.get('name', ''), font=name_font, fill="black")
    if card_data.get('evolves_from'):
        draw.text(EVOLUTION_POS, f"Evolves from {card_data['evolves_from']}", font=evolution_font, fill="black")
    draw.text(KP_POS, f"{card_data.get('kp', '')} HP", font=kp_font, fill="black", anchor="ra")
    
    attack1_spacing = -1.5 
    draw_text_with_spacing(draw, ATTACK1_NAME_POS, card_data.get('attack1_name', ''), attack_name_font, fill="black", spacing=attack1_spacing)
    draw.text(ATTACK1_DMG_POS, str(card_data.get('attack1_schaden', '')), font=attack_damage_font, fill="black", anchor="ra")
    
    draw.text(ILLUSTRATOR_POS, f"Illus. {card_data.get('illustrator', 'Unknown')}", font=illustrator_font, fill="black")
    draw.text(CARD_NUM_POS, card_data.get('card_number', '0/0'), font=card_num_font, fill="black", anchor="ma")

    final_buffer = BytesIO()
    card_bg.save(final_buffer, format='PNG')
    final_buffer.seek(0)
    return final_buffer