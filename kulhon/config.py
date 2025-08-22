LEVEL_UP_XP_BASE = 100
LEVEL_UP_XP_MAX_STEP = 500  # maximální přírůstek XP na level

def xp_for_next_level(level: int) -> int:
    """Vrací XP potřebné pro daný level (nekumulativně), přírůstek je max 500."""
    if level < 1:
        return 0
    if level == 1:
        return LEVEL_UP_XP_BASE
    prev = xp_for_next_level(level - 1)
    step = min(int(prev * 0.5), LEVEL_UP_XP_MAX_STEP)
    return prev + step

def total_xp_for_level(level: int) -> int:
    """Vrací celkové XP potřebné pro dosažení daného levelu (kumulativně)."""
    total = 0
    for l in range(1, level):
        total += xp_for_next_level(l)
    return total

def get_xp_bonus_percent(level: int) -> float:
    """
    Vrací procentuální XP bonus podle levelu (ranku).
    Na levelu 100 je bonus +50 %, roste lineárně, max. 200 % (tj. 2.0× XP).
    Vrací desetinné číslo, takže XP bonus může být i např. +73.5 %.
    """
    if level < 1:
        return 0.0
    bonus = 0.5 * (level / 100)
    return min(bonus, 2.0)  # max +200 %

RANKS = {
    1: "Nováček",
    5: "Učeň",
    10: "Dobrodruh",
    20: "Veterán",
    30: "Mistr",
    50: "Legenda",
    100: "Nesmrtelný"
}

def get_rank(level: int) -> str:
    """Vrací rank podle levelu (nejvyšší dosažený)."""
    best = ""
    for lvl, name in sorted(RANKS.items()):
        if level >= lvl:
            best = name
        else:
            break
    return best or "Nováček"

LEVEL_UP_HP_BONUS = 10
LEVEL_UP_KULHON_BONUS = 500
LEVEL_UP_DMG_BONUS = 2
RAID_LEVEL_RANGE = 5
RAID_ALLOW_BOT_ATTACK = True

JOBS = {
    "rybaření": {"xp": (12, 30), "money": (30, 80), "emoji": "🎣"},
    "farmaření": {"xp": (10, 40), "money": (25, 100), "emoji": "🌾"},
    "těžení": {"xp": (15, 35), "money": (40, 90), "emoji": "⛏️"},
    "lov": {"xp": (20, 45), "money": (50, 120), "emoji": "🏹"},
    "stavba": {"xp": (10, 25), "money": (35, 70), "emoji": "🧱"},
    "dřevorubectví": {"xp": (13, 28), "money": (30, 75), "emoji": "🌲"},
    "kopání hlíny": {"xp": (8, 20), "money": (20, 60), "emoji": "🪣"},
    "kovářství": {"xp": (25, 50), "money": (60, 130), "emoji": "⚒️"},
    "alchymie": {"xp": (18, 35), "money": (45, 90), "emoji": "🧪"},
    "kuchař": {"xp": (14, 32), "money": (30, 85), "emoji": "🍳"},
    "obchodník": {"xp": (20, 40), "money": (70, 150), "emoji": "💰"},
    "rudník": {"xp": (17, 38), "money": (50, 100), "emoji": "🪨"},
}

# Pravděpodobnosti a nastavení miniher
COINFLIP_WIN_CHANCE = 50
SHELLGAME_WIN_CHANCE = 33
SLOTMACHINE_JACKPOT_CHANCE = 5   # 5% šance na jackpot (3 stejné)
SLOTMACHINE_DOUBLE_CHANCE = 20    # 20% šance na dva stejné
DICEDUEL_WIN_CHANCE = 33

# Cooldowny pro mini hry v sekundách
COINFLIP_COOLDOWN = 60
SHELLGAME_COOLDOWN = 60
SLOTMACHINE_COOLDOWN = 60
DICEDUEL_COOLDOWN = 60
