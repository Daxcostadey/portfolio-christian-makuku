import copy
import re

SETTINGS_NAME = "data/settings.json"

FONTS = {
    "Sora": "Sora",
    "Manrope": "Manrope",
    "Poppins": "Poppins",
    "Montserrat": "Montserrat",
    "Inter": "Inter",
    "DM Sans": "DM Sans",
    "Space Grotesk": "Space Grotesk",
    "Playfair Display": "Playfair Display",
    "Lora": "Lora",
}

LANGS = ["fr", "en", "sw"]
TEXT_FIELDS = [
    ("hero.kicker", "Accroche (au-dessus du nom)", False),
    ("hero.role", "Titre / métier", False),
    ("hero.lead", "Présentation courte (accueil)", True),
    ("about.title", "Titre de la section Profil", False),
    ("about.p1", "Profil, paragraphe 1", True),
    ("about.p2", "Profil, paragraphe 2", True),
    ("about.p3", "Profil, paragraphe 3", True),
    ("contact.lead", "Texte de la section Contact", True),
]
SECTIONS = [
    ("profil", "Profil"),
    ("parcours", "Parcours"),
    ("ia", "Intelligence artificielle"),
    ("competences", "Compétences"),
    ("formation", "Formation"),
    ("recent", "Réalisations récentes"),
    ("contact", "Contact"),
]

DEFAULTS = {
    "profile": {
        "name": "Christian Makuku Valentin",
        "phone": "+242 05 010 94 03",
        "email": "daxcosta244@gmail.com",
        "address": "Rue Lagué N°66, Moungali, Brazzaville",
        "location": "Moungali, Brazzaville",
        "since": "2017",
        "ai_tools": "55+",
        "photo": "",
    },
    "texts": {lang: {} for lang in LANGS},
    "theme": {
        "primary": "#facc15",
        "secondary": "#f59e0b",
        "accent": "#15803d",
        "background": "#ffffff",
        "font_head": "Sora",
        "font_body": "Manrope",
    },
    "sections": {key: True for key, _ in SECTIONS},
}

HEX = re.compile(r"^#[0-9a-fA-F]{6}$")


def merge(saved):
    data = copy.deepcopy(DEFAULTS)
    for group, values in (saved or {}).items():
        if group in data and isinstance(values, dict):
            if group == "texts":
                for lang in LANGS:
                    data["texts"][lang].update(values.get(lang) or {})
            else:
                data[group].update(values)
    return data


def _rgb(h):
    return tuple(int(h[i:i + 2], 16) for i in (1, 3, 5))


def _mix(a, b, t):
    ra, rb = _rgb(a), _rgb(b)
    return "#" + "".join(f"{round(x + (y - x) * t):02x}" for x, y in zip(ra, rb))


def theme_css(theme):
    d = DEFAULTS["theme"]
    rules = []
    if theme["primary"] != d["primary"]:
        p = theme["primary"]
        rules += [f"--yellow:{p}", f"--yellow-soft:{_mix(p, '#ffffff', .8)}"]
    if theme["secondary"] != d["secondary"]:
        s = theme["secondary"]
        rules += [f"--amber:{s}", f"--amber-dark:{_mix(s, '#000000', .35)}"]
    if theme["accent"] != d["accent"]:
        a = theme["accent"]
        rules += [f"--green:{a}", f"--green-dark:{_mix(a, '#000000', .4)}", f"--green-soft:{_mix(a, '#ffffff', .85)}"]
    if theme["primary"] != d["primary"] or theme["background"] != d["background"]:
        rules.append(f"--cream:{_mix(theme['primary'], theme['background'], .93)}")
    if theme["font_head"] != d["font_head"]:
        rules.append(f"--font-head:\"{theme['font_head']}\", system-ui, sans-serif")
    if theme["font_body"] != d["font_body"]:
        rules.append(f"--font-body:\"{theme['font_body']}\", system-ui, sans-serif")
    css = ":root{" + ";".join(rules) + "}" if rules else ""
    if theme["background"] != d["background"]:
        css += f"body{{background:{theme['background']}}}"
    return css


def fonts_url(theme):
    fams = []
    for f in dict.fromkeys([theme["font_head"], theme["font_body"]]):
        fams.append("family=" + f.replace(" ", "+") + ":wght@400;500;600;700")
    return "https://fonts.googleapis.com/css2?" + "&".join(fams) + "&display=swap"


def clean_color(value, fallback):
    value = (value or "").strip()
    return value.lower() if HEX.match(value) else fallback


def initials(name):
    words = [w for w in name.split() if w]
    return "".join(w[0] for w in words[:2]).upper() or "CM"
