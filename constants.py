import re


DESCRIPTION_LINK_REGEX = re.compile(r"\[.*?\]\{.*?:(.*?)\}")


STAT_STAGE_MULTIPLIERS = {
    -6: 2 / 8,
    -5: 2 / 7,
    -4: 2 / 6,
    -3: 2 / 5,
    -2: 2 / 4,
    -1: 2 / 3,
    0: 2 / 2,
    1: 3 / 2,
    2: 4 / 2,
    3: 5 / 2,
    4: 6 / 2,
    5: 7 / 2,
    6: 8 / 2,
}

MOVE_META_CATEGORIES = [
    "Inflicts damage",
    "No damage; inflicts status ailment",
    "No damage; lowers target's stats or raises user's stats",
    "No damage; heals the user",
    "Inflicts damage; inflicts status ailment",
    "No damage; inflicts status ailment; raises target's stats",
    "Inflicts damage; lowers target's stats",
    "Inflicts damage; raises user's stats",
    "Inflicts damage; absorbs damage done to heal the user",
    "One-hit KO",
    "Effect on the whole field",
    "Effect on one side of the field",
    "Forces target to switch out",
    "Unique effect",
]

MOVE_AILMENTS = {
    -1: "????",
    0: "none",
    1: "Paralysis",
    2: "Sleep",
    3: "Freeze",
    4: "Burn",
    5: "Poison",
    6: "Confusion",
    7: "Infatuation",
    8: "Trap",
    9: "Nightmare",
    12: "Torment",
    13: "Disable",
    14: "Yawn",
    15: "Heal Block",
    17: "No type immunity",
    18: "Leech Seed",
    19: "Embargo",
    20: "Perish Song",
    21: "Ingrain",
    24: "Silence",
}

TYPES = [
    None,
    "Normal",
    "Fighting",
    "Flying",
    "Poison",
    "Ground",
    "Rock",
    "Bug",
    "Ghost",
    "Steel",
    "Fire",
    "Water",
    "Grass",
    "Electric",
    "Psychic",
    "Ice",
    "Dragon",
    "Dark",
    "Fairy",
    "???",
    "Shadow",
]

MOVE_TARGETS = [
    None,
    "One specific move. How this move is chosen depends upon on the move being used.",
    "One other Pokémon on the field, selected by the trainer. Stolen moves reuse the same target.",
    "The user's ally (if any).",
    "The user's side of the field. Affects the user and its ally (if any).",
    "Either the user or its ally, selected by the trainer.",
    "The opposing side of the field. Affects opposing Pokémon.",
    "The user.",
    "One opposing Pokémon, selected at random.",
    "Every other Pokémon on the field.",
    "One other Pokémon on the field, selected by the trainer.",
    "All opposing Pokémon.",
    "The entire field. Affects all Pokémon.",
    "The user and its allies.",
    "Every Pokémon on the field.",
]

DAMAGE_CLASSES = [None, "Status", "Physical", "Special"]


TYPE_EFFICACY = [
    None,
    [None, 1, 1, 1, 1, 1, 0.5, 1, 0, 0.5, 1, 1, 1, 1, 1, 1, 1, 1, 1],
    [None, 2, 1, 0.5, 0.5, 1, 2, 0.5, 0, 2, 1, 1, 1, 1, 0.5, 2, 1, 2, 0.5],
    [None, 1, 2, 1, 1, 1, 0.5, 2, 1, 0.5, 1, 1, 2, 0.5, 1, 1, 1, 1, 1],
    [None, 1, 1, 1, 0.5, 0.5, 0.5, 1, 0.5, 0, 1, 1, 2, 1, 1, 1, 1, 1, 2],
    [None, 1, 1, 0, 2, 1, 2, 0.5, 1, 2, 2, 1, 0.5, 2, 1, 1, 1, 1, 1],
    [None, 1, 0.5, 2, 1, 0.5, 1, 2, 1, 0.5, 2, 1, 1, 1, 1, 2, 1, 1, 1],
    [None, 1, 0.5, 0.5, 0.5, 1, 1, 1, 0.5, 0.5, 0.5, 1, 2, 1, 2, 1, 1, 2, 0.5],
    [None, 0, 1, 1, 1, 1, 1, 1, 2, 1, 1, 1, 1, 1, 2, 1, 1, 0.5, 1],
    [None, 1, 1, 1, 1, 1, 2, 1, 1, 0.5, 0.5, 0.5, 1, 0.5, 1, 2, 1, 1, 2],
    [None, 1, 1, 1, 1, 1, 0.5, 2, 1, 2, 0.5, 0.5, 2, 1, 1, 2, 0.5, 1, 1],
    [None, 1, 1, 1, 1, 2, 2, 1, 1, 1, 2, 0.5, 0.5, 1, 1, 1, 0.5, 1, 1],
    [None, 1, 1, 0.5, 0.5, 2, 2, 0.5, 1, 0.5, 0.5, 2, 0.5, 1, 1, 1, 0.5, 1, 1],
    [None, 1, 1, 2, 1, 0, 1, 1, 1, 1, 1, 2, 0.5, 0.5, 1, 1, 0.5, 1, 1],
    [None, 1, 2, 1, 2, 1, 1, 1, 1, 0.5, 1, 1, 1, 1, 0.5, 1, 1, 0, 1],
    [None, 1, 1, 2, 1, 2, 1, 1, 1, 0.5, 0.5, 0.5, 2, 1, 1, 0.5, 2, 1, 1],
    [None, 1, 1, 1, 1, 1, 1, 1, 1, 0.5, 1, 1, 1, 1, 1, 1, 2, 1, 0],
    [None, 1, 0.5, 1, 1, 1, 1, 1, 2, 1, 1, 1, 1, 1, 2, 1, 1, 0.5, 0.5],
    [None, 1, 2, 1, 0.5, 1, 1, 1, 1, 0.5, 0.5, 1, 1, 1, 1, 1, 2, 2, 1],
]


ARTISTS = {
    405452200656109569: "@hirowilde",
    304098467192635392: "@superjedi224",
    130438329484181504: "@haltfire302",
    285861483412193280: "@anoea",
    326895657803710477: "@chaotichavoc",
    494656111627075594: "@dotkura",
    711892049842012190: "@somebluepigeon",
    444692790689923072: "@5h3s",
    550289905079812106: "@rengokukyojuro8008",
    810031895190306816: "@ironlegend09",
    611659645760831506: "@dagger_mace",
    850079219681722398: "@foxrii_",
    712521240602214400: "@blubambii",
    979108831118364774: "@clumsy.kenji",
    745825974880436294: "@qydv",
    690194873650905155: "@chri3418",
    676169170400051201: "@just_kumowo",
    559768825361596442: "@.typenull.",
    484526479770910728: "@stranger1200",
    859645802899963923: "@a_dood_1336",
    336148113465278464: "@bren.__.",
    243763234685976577: "@metspek",
    512697200879468549: "@asuka03",
    1042169206692651038: "@tazzy989",
    874420399608332370: "@angeljanin",
    286902705115627520: "@not_zack",
    449792537272516628: "@jynxerso",
    380082606391296001: "@tp.23",
    470615071035359262: "@ellewoods.",
    984530916565188648: "@cherinoo.",
    805868750666465350: "@bladempreg",
    1079903072572158003: "@t.empress",
    267550284979503104: "@witherr.",
    546492524366266369: "@frankmyocean",
}

GENDER_RATES = {
    0: [100, 0],
    1: [87.5, 12.5],
    2: [75, 25],
    4: [50, 50],
    6: [25, 75],
    7: [12.5, 87.5],
    8: [0, 100],
}

GENDER_TYPES = {0: "Unknown", 1: "Female", 2: "Male"}

GENDER_IMAGE_SUFFIXES = {"female": "F"}  # TODO: Use gender ID later when refactoring poketwo genders code