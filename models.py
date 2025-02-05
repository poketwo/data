from __future__ import annotations

import random
import typing
import unicodedata
from abc import ABC
from collections import defaultdict
from dataclasses import dataclass
from functools import cached_property
from typing import List, Literal, Optional, Set, Union

from data.utils import comma_formatted

from . import constants


def deaccent(text):
    norm = unicodedata.normalize("NFD", text)
    result = "".join(ch for ch in norm if unicodedata.category(ch) != "Mn")
    return unicodedata.normalize("NFKC", result)


class UnregisteredError(Exception):
    pass


class UnregisteredDataManager:
    pass


# Moves


@dataclass
class MoveEffect:
    id: int
    description: str

    instance: typing.Any = UnregisteredDataManager()


@dataclass
class StatChange:
    stat_id: int
    change: int

    @cached_property
    def stat(self):
        return ("hp", "atk", "defn", "satk", "sdef", "spd", "evasion", "accuracy")[
            self.stat_id - 1
        ]


@dataclass
class StatStages:
    hp: int = 0
    atk: int = 0
    defn: int = 0
    satk: int = 0
    sdef: int = 0
    spd: int = 0
    evasion: int = 0
    accuracy: int = 0
    crit: int = 0

    def update(self, stages):
        self.hp += stages.hp
        self.atk += stages.atk
        self.defn += stages.defn
        self.satk += stages.satk
        self.sdef += stages.sdef
        self.spd += stages.spd
        self.evasion += stages.evasion
        self.accuracy += stages.accuracy
        self.crit += stages.crit


@dataclass
class MoveResult:
    success: bool
    damage: int
    healing: int
    ailment: str
    messages: typing.List[str]
    stat_changes: typing.List[StatChange]


@dataclass
class MoveMeta:
    meta_category_id: int
    meta_ailment_id: int
    drain: int
    healing: int
    crit_rate: int
    ailment_chance: int
    flinch_chance: int
    stat_chance: int
    min_hits: typing.Optional[int] = None
    max_hits: typing.Optional[int] = None
    min_turns: typing.Optional[int] = None
    max_turns: typing.Optional[int] = None
    stat_changes: typing.List[StatChange] = None

    def __post_init__(self):
        if self.stat_changes is None:
            self.stat_changes = []

    @cached_property
    def meta_category(self):
        return constants.MOVE_META_CATEGORIES[self.meta_category_id]

    @cached_property
    def meta_ailment(self):
        return constants.MOVE_AILMENTS[self.meta_ailment_id]


@dataclass
class Move:
    id: int
    slug: str
    name: str
    power: int
    pp: int
    accuracy: int
    priority: int
    target_id: int
    type_id: int
    damage_class_id: int
    effect_id: int
    effect_chance: int
    meta: MoveMeta

    instance: typing.Any = UnregisteredDataManager()

    @cached_property
    def type(self):
        return constants.TYPES[self.type_id]

    @cached_property
    def target_text(self):
        return constants.MOVE_TARGETS[self.target_id]

    @cached_property
    def damage_class(self):
        return constants.DAMAGE_CLASSES[self.damage_class_id]

    @cached_property
    def effect(self):
        return self.instance.effects[self.effect_id]

    @cached_property
    def description(self):
        return self.effect.description.format(effect_chance=self.effect_chance)

    def __str__(self):
        return self.name

    def calculate_turn(self, pokemon, opponent):
        if self.damage_class_id == 1 or self.power is None:
            success = True
            damage = 0
            hits = 0
        else:
            success = random.randrange(100) < (self.accuracy or 0) * (
                constants.STAT_STAGE_MULTIPLIERS[pokemon.stages.accuracy] * 2 + 1
            ) / (constants.STAT_STAGE_MULTIPLIERS[opponent.stages.evasion] * 2 + 1)

            hits = random.randint(self.meta.min_hits or 1, self.meta.max_hits or 1)

            if self.damage_class_id == 2:
                atk = pokemon.atk * constants.STAT_STAGE_MULTIPLIERS[pokemon.stages.atk]
                defn = (
                    opponent.defn
                    * constants.STAT_STAGE_MULTIPLIERS[opponent.stages.defn]
                )
            else:
                atk = (
                    pokemon.satk * constants.STAT_STAGE_MULTIPLIERS[pokemon.stages.satk]
                )
                defn = (
                    opponent.sdef
                    * constants.STAT_STAGE_MULTIPLIERS[opponent.stages.sdef]
                )

            damage = int((2 * pokemon.level / 5 + 2) * self.power * atk / defn / 50 + 2)

        healing = damage * self.meta.drain / 100
        healing += pokemon.max_hp * self.meta.healing / 100

        for ailment in pokemon.ailments:
            if ailment == "Paralysis":
                if random.random() < 0.25:
                    success = False
            elif ailment == "Sleep":
                if self.id not in (173, 214):
                    success = False
            elif ailment == "Freeze":
                if self.id not in (588, 172, 221, 293, 503, 592):
                    success = False
            elif ailment == "Burn":
                if self.damage_class_id == 2:
                    damage /= 2

            # elif ailment == "Confusion":
            #     pass
            # elif ailment == "Infatuation":
            #     pass
            # elif ailment == "Trap":
            #     pass
            # elif ailment == "Nightmare":
            #     pass
            # elif ailment == "Torment":
            #     pass
            # elif ailment == "Disable":
            #     pass
            # elif ailment == "Yawn":
            #     pass
            # elif ailment == "Heal Block":
            #     pass
            # elif ailment == "No type immunity":
            #     pass
            # elif ailment == "Leech Seed":
            #     pass
            # elif ailment == "Embargo":
            #     pass
            # elif ailment == "Perish Song":
            #     pass
            # elif ailment == "Ingrain":
            #     pass
            # elif ailment == "Silence":
            #     pass

        ailment = (
            self.meta.meta_ailment
            if random.randrange(100) < self.meta.ailment_chance
            else None
        )

        typ_mult = 1
        for typ in opponent.species.types:
            try:
                typ_mult *= constants.TYPE_EFFICACY[self.type_id][
                    constants.TYPES.index(typ)
                ]
            except IndexError:  # Type does not exist in the TYPE_EFFICACY list. Such as the Shadow type.
                pass

        damage *= typ_mult
        messages = []

        if typ_mult == 0:
            messages.append("It's not effective...")
        elif typ_mult > 1:
            messages.append("It's super effective!")
        elif typ_mult < 1:
            messages.append("It's not very effective...")

        if hits > 1:
            messages.append(f"It hit {hits} times!")

        changes = []

        for change in self.meta.stat_changes:
            if random.randrange(100) < self.meta.stat_chance:
                changes.append(change)

        if self.type in pokemon.species.types:
            damage *= 1.5

        return MoveResult(
            success=success,
            damage=damage,
            healing=healing,
            ailment=ailment,
            messages=messages,
            stat_changes=changes,
        )


# Items


@dataclass
class Item:
    id: int
    name: str
    description: str
    cost: int
    page: int
    action: str
    inline: bool
    emote: str = None
    shard: bool = False

    instance: typing.Any = UnregisteredDataManager()

    def __str__(self):
        return self.name


class MoveMethod(ABC):
    pass


@dataclass
class LevelMethod(MoveMethod):
    level: int

    instance: typing.Any = UnregisteredDataManager()

    @cached_property
    def text(self):
        return f"Level {self.level}"


@dataclass
class PokemonMove:
    move_id: int
    method: MoveMethod

    instance: typing.Any = UnregisteredDataManager()

    @cached_property
    def move(self):
        return self.instance.moves[self.move_id]

    @cached_property
    def text(self):
        return self.method.text


# Evolution


@dataclass
class EvolutionTrigger(ABC):
    pass


@dataclass
class LevelTrigger(EvolutionTrigger):
    level: int
    item_id: int
    move_id: int
    move_type_id: int
    time: str
    relative_stats: int
    gender_id: str
    natures: List[str]

    instance: typing.Any = UnregisteredDataManager()

    @cached_property
    def item(self):
        if self.item_id is None:
            return None
        return self.instance.items[self.item_id]

    @cached_property
    def move(self):
        if self.move_id is None:
            return None
        return self.instance.moves[self.move_id]

    @cached_property
    def move_type(self):
        if self.move_type_id is None:
            return None
        return constants.TYPES[self.move_type_id]

    @cached_property
    def gender(self):
        if self.gender_id is None:
            return None
        return constants.GENDER_TYPES[self.gender_id]

    @cached_property
    def text(self):
        if self.level is None:
            text = f"when leveled up"
        else:
            text = f"starting from level {self.level}"

        if self.gender:
            text += f" as {self.gender}"

        if self.item is not None:
            text += f" while holding a {self.item}"

        if self.move is not None:
            text += f" while knowing {self.move}"

        if self.move_type is not None:
            text += f" while knowing a {self.move_type}-type move"

        if self.relative_stats == 1:
            text += f" when its Attack is higher than its Defense"
        elif self.relative_stats == -1:
            text += f" when its Defense is higher than its Attack"
        elif self.relative_stats == 0:
            text += f" when its Attack is equal to its Defense"

        if self.time is not None:
            text += " in the " + self.time + "time"

        if self.natures:
            text += (
                f" with a Nature of {comma_formatted(self.natures, conjunction='or')}"
            )

        return text


@dataclass
class ItemTrigger(EvolutionTrigger):
    item_id: int

    instance: typing.Any = UnregisteredDataManager()

    @cached_property
    def item(self):
        return self.instance.items[self.item_id]

    @cached_property
    def text(self):
        return f"using a {self.item}"


@dataclass
class TradeTrigger(EvolutionTrigger):
    item_id: int = None

    instance: typing.Any = UnregisteredDataManager()

    @cached_property
    def item(self):
        if self.item_id is None:
            return None
        return self.instance.items[self.item_id]

    @cached_property
    def text(self):
        if self.item_id is None:
            return "when traded"
        return f"when traded while holding a {self.item}"


@dataclass
class OtherTrigger(EvolutionTrigger):
    instance: typing.Any = UnregisteredDataManager()

    @cached_property
    def text(self):
        return "somehow"


@dataclass
class Evolution:
    target_id: int
    trigger: EvolutionTrigger
    type: bool

    instance: typing.Any = UnregisteredDataManager()

    @classmethod
    def evolve_from(cls, target: int, trigger: EvolutionTrigger, instance=None):
        if instance is None:
            instance: typing.Any = UnregisteredDataManager()
        return cls(target, trigger, False, instance=instance)

    @classmethod
    def evolve_to(cls, target: int, trigger: EvolutionTrigger, instance=None):
        if instance is None:
            instance: typing.Any = UnregisteredDataManager()
        return cls(target, trigger, True, instance=instance)

    @cached_property
    def dir(self) -> str:
        return "to" if self.type == True else "from" if self.type == False else "??"

    @cached_property
    def target(self):
        return self.instance.pokemon[self.target_id]

    @cached_property
    def current(self):
        for dir in ("to", "from"):
            species = next(
                (
                    s
                    for s in self.instance.all_pokemon()
                    if getattr(s, f"evolution_{dir}")
                    and self in getattr(s, f"evolution_{dir}").items
                ),
                None,
            )
            if species:
                return species

    @cached_property
    def text(self):
        # At the moment this says 'transforms' only for Piroette Meloetta, Resolute Keldeo and School WIshiwashi since
        # we're piggybacking off the evolution method. But in the future this could show the incorrect action, although unlikely.
        action = "evolves"
        if (
            self.target.is_form
            and self.target.dex_number
            == self.current.dex_number  # checks if target is a form of the same base pokemon, aka 'transforms to'
            and self.dir != "from"
        ) or (
            self.current.is_form
            and self.target.id
            == self.current.dex_number  # checks if target is the base species, aka 'transforms from'
        ):
            action = "transforms"

        if getattr(self.target, f"evolution_{self.dir}") is not None:
            pevo = getattr(self.target, f"evolution_{self.dir}")
            return f"{action} {self.dir} {self.target} {self.trigger.text}, which {pevo.text}"

        return f"{action} {self.dir} {self.target} {self.trigger.text}"


@dataclass
class EvolutionList:
    items: list

    def __init__(self, evolutions: Union[list, Evolution]):
        if type(evolutions) == Evolution:
            evolutions = [evolutions]
        self.items = evolutions

    @cached_property
    def text(self):
        txt = " and ".join(e.text for e in self.items)
        txt = txt.replace(" and ", ", ", txt.count(" and ") - 1)
        return txt


# Stats


@dataclass
class Stats:
    hp: int
    atk: int
    defn: int
    satk: int
    sdef: int
    spd: int

    @property
    def total(self) -> int:
        return self.hp + self.atk + self.defn + self.satk + self.sdef + self.spd


# Species


@dataclass
class Species:
    id: int
    names: typing.List[typing.Tuple[str, str]]
    slug: str
    base_stats: Stats
    height: int
    weight: int
    dex_number: int
    catchable: bool
    types: typing.List[str]
    abundance: int
    gender_rate: int
    has_gender_differences: int
    description: str = None
    mega_id: int = None
    mega_x_id: int = None
    mega_y_id: int = None
    evolution_from: EvolutionList = None
    evolution_to: EvolutionList = None
    mythical: bool = False
    legendary: bool = False
    ultra_beast: bool = False
    event: bool = False
    is_form: bool = False
    form_item: int = None
    _moves: typing.List[PokemonMove] = None
    region: str = None
    art_credit: str = None

    instance: typing.Any = UnregisteredDataManager()

    def __post_init__(self):
        self.name = next(filter(lambda x: x[0] == "🇬🇧", self.names))[1]
        if self._moves is None:
            self._moves = []

    def __str__(self):
        return self.name

    @cached_property
    def moves(self) -> List[PokemonMove]:
        if not self._moves:
            if self.base_species:
                self._moves.extend(self.base_species.moves)

        return self._moves

    @cached_property
    def moveset(self) -> List[Move]:
        return [pmove.move for pmove in self.moves]

    @cached_property
    def gender_ratios(self):
        return constants.GENDER_RATES[self.gender_rate]

    @cached_property
    def default_gender(self) -> Literal["Unknown", "Male", "Female"] | None:
        if self.gender_rate == -1:
            return "Unknown"

        if 100 in self.gender_ratios:  # If species is exclusively one gender
            always_male = self.gender_ratios[0] == 100
            if always_male:
                return "Male"
            else:
                return "Female"
        else:  # If both male and female are possible
            return None  # There is no default

    @cached_property
    def mega(self):
        if self.mega_id is None:
            return None

        return self.instance.pokemon[self.mega_id]

    @cached_property
    def mega_x(self):
        if self.mega_x_id is None:
            return None

        return self.instance.pokemon[self.mega_x_id]

    @cached_property
    def mega_y(self):
        if self.mega_y_id is None:
            return None

        return self.instance.pokemon[self.mega_y_id]

    @cached_property
    def gmax(self) -> Species | None:
        return self.instance.gmax_mapping.get(self.id)

    @cached_property
    def is_gmax(self) -> bool:
        return self.id in self.instance.list_gmax

    @cached_property
    def variants(self) -> List[Species]:
        return self.instance.all_species_by_number(self.dex_number)

    def get_evoline(self, evos_done: Set[int]) -> Set[int]:
        evoline = {self.id}
        evos = (self.evolution_from.items if self.evolution_from else []) + (self.evolution_to.items if self.evolution_to else [])
        for evo in evos:
            evo_species = self.instance.species_by_number(evo.target_id)
            if evo_species.id in evos_done:
                continue
            evoline.update(evo_species.get_evoline(evoline))
            evos_done.add(evo_species.id)

        return evoline

    @cached_property
    def evolution_line(self) -> List[Species]:
        return [self.instance.species_by_number(i) for i in sorted(self.get_evoline({self.id}))]

    @cached_property
    def base_species(self) -> Species | None:
        if self.id != self.dex_number:
            return self.instance.species_by_number(self.dex_number)
        else:
            return None

    @cached_property
    def image_url(self):
        return self.instance.asset(f"/images/{self.id}.png")

    @cached_property
    def shiny_image_url(self):
        return self.instance.asset(f"/shiny/{self.id}.png")

    @cached_property
    def image_url_female(self):
        if self.has_gender_differences == 1:
            return self.instance.asset(f"/images/{self.id}F.png")

    @cached_property
    def shiny_image_url_female(self):
        if self.has_gender_differences == 1:
            return self.instance.asset(f"/shiny/{self.id}F.png")

    @cached_property
    def correct_guesses(self):
        extra = []

        if self.is_form or self.event:
            extra.extend(self.instance.pokemon[self.dex_number].correct_guesses)

        if "nidoran" in self.slug:
            extra.append("nidoran")

        # Elsa Galarian Ponyta
        if self.id == 50053:
            extra.extend(self.instance.pokemon[10159].correct_guesses)

        # Halloween Alolan Ninetales
        if self.id == 50076:
            extra.extend(self.instance.pokemon[10104].correct_guesses)

        # Pride Gardevoir & Delphox
        if self.id == 50107:
            # can't set two dex_numbers
            extra.extend(self.instance.pokemon[655].correct_guesses)
            extra.append("pride gardevoir")
            extra.append("pride delphox")

        # Pyjama Plusle & Minun
        if self.id == 50149:
            # can't set two dex_numbers
            extra.extend(self.instance.pokemon[312].correct_guesses)
            extra.append("christmas minun")

        # Santa Hisuian Zorua
        if self.id == 50145:
            extra.extend(self.instance.pokemon[10230].correct_guesses)
            extra.append("christmas zorua")

        # Reindeer Deerling
        if self.id == 50147:
            extra.append("christmas deerling")

        # Birthday Cake Alolan Vulpix
        if self.id == 50168:
            extra.extend(self.instance.pokemon[10103].correct_guesses)
            extra.extend(["anniversary alolan vulpix", "anniversary vulpix"])

        # Día de Muertos pokémon
        if self.id in range(50192, 50199):
            extra.append(f"day of the dead {self.base_species.name.lower()}")

        # La Catrina Hisuian Lilligant
        if self.id == 50198:
            extra.extend(self.instance.pokemon[10229].correct_guesses)
            extra.extend(["dia de muertos lilligant", "day of the dead hisuian lilligant"])

        # Grinch Grimmsnarl
        if self.id == 50207:
            extra.append("christmas grimmsnarl")

        return extra + [deaccent(x.lower()) for _, x in self.names] + [self.slug]

    @cached_property
    def trade_evolutions(self):
        if self.evolution_to is None:
            return []

        evos = []

        for e in self.evolution_to.items:
            if isinstance(e.trigger, TradeTrigger):
                evos.append(e)

        return evos

    @cached_property
    def evolution_text(self):
        text = ""
        if self.is_form and self.form_item is not None:
            species = self.instance.pokemon[self.dex_number]
            item = self.instance.items[self.form_item]
            text += f" transforms from {species} when given a {item.name}"
        elif self.evolution_from is not None:
            text += f" {self.evolution_from.text}"

        if text and self.evolution_to is not None:
            text += " and"

        if self.evolution_to is not None:
            text += f" {self.evolution_to.text}"

        if text:
            return f"{self.name}{text}."
        else:
            return None

    def __repr__(self):
        return f"<Species: {self.name}>"

    def get_image_url(
        self,
        shiny: Optional[bool] = False,
        gender: Optional[Literal["unknown", "male", "female"]] = None,
    ) -> str:

        if gender is not None:
            gender = gender.lower()

        attr_parts = ["image_url"]

        if shiny:
            attr_parts.insert(0, "shiny")

        if self.has_gender_differences:
            match gender:
                case "female":
                    attr_parts.append(gender)

        attr = "_".join(attr_parts)
        return getattr(self, attr)


@dataclass
class DataManagerBase:
    pokemon: typing.Dict[int, Species] = None
    items: typing.Dict[int, Item] = None
    effects: typing.Dict[int, MoveEffect] = None
    moves: typing.Dict[int, Move] = None

    def all_pokemon(self):
        return self.pokemon.values()

    @cached_property
    def total_pokedex_count(self) -> int:
        return sum(x.catchable and x.id < 10000 for x in self.all_pokemon())

    @cached_property
    def list_alolan(self):
        return [
            10091,
            10092,
            10093,
            10100,
            10101,
            10102,
            10103,
            10104,
            10105,
            10106,
            10107,
            10108,
            10109,
            10110,
            10111,
            10112,
            10113,
            10114,
            10115,
            50076,
            50168,
        ]

    @cached_property
    def list_galarian(self):
        return [
            10158,
            10159,
            10160,
            10161,
            10162,
            10163,
            10164,
            10165,
            10166,
            10167,
            10168,
            10169,
            10170,
            10171,
            10172,
            10173,
            10174,
            10175,
            10176,
            10177,
            50053,
        ]

    @cached_property
    def list_hisuian(self):
        return [
            10221,
            10222,
            10223,
            10224,
            10225,
            10226,
            10227,
            10228,
            10229,
            10230,
            10231,
            10232,
            10233,
            10234,
            10235,
            10236,
            10237,
            10238,
            10239,
            50145,
            50198,
        ]

    @cached_property
    def list_paldean(self):
        return [
            10250,
            10251,
            10252,
            10253,
        ]

    @cached_property
    def list_paradox(self):
        return [
            984,
            985,
            986,
            987,
            988,
            989,
            990,
            991,
            992,
            993,
            994,
            995,
            1005,
            1006,
            1007,
            1008,
            1009,
            1010,
            1020,
            1021,
            1022,
            1023,
        ]

    @cached_property
    def list_mythical(self):
        return [v.id for v in self.pokemon.values() if v.mythical]

    @cached_property
    def list_legendary(self):
        return [v.id for v in self.pokemon.values() if v.legendary]

    @cached_property
    def list_ub(self):
        return [v.id for v in self.pokemon.values() if v.ultra_beast]

    @cached_property
    def list_event(self):
        return [v.id for v in self.pokemon.values() if v.event]

    @cached_property
    def list_mega(self):
        return (
            [v.mega_id for v in self.pokemon.values() if v.mega_id is not None]
            + [v.mega_x_id for v in self.pokemon.values() if v.mega_x_id is not None]
            + [v.mega_y_id for v in self.pokemon.values() if v.mega_y_id is not None]
        )

    @cached_property
    def gmax_mapping(self):
        mapping = {
            3: 10186,
            6: 10187,
            9: 10188,
            12: 10189,
            25: 10190,
            52: 10191,
            68: 10192,
            94: 10193,
            99: 10194,
            131: 10195,
            133: 10196,
            143: 10197,
            569: 10198,
            809: 10199,
            812: 10200,
            815: 10201,
            818: 10202,
            823: 10203,
            826: 10204,
            834: 10205,
            839: 10206,
            841: 10207,
            842: 10208,
            844: 10209,
            849: 10210,
            851: 10211,
            858: 10212,
            861: 10213,
            869: 10214,
            879: 10215,
            884: 10216,
            890: 10217,
            892: 10218,
            10183: 10219,
            10178: 10220,
        }
        return {
            sid: self.species_by_number(gmax_id) for sid, gmax_id in mapping.items()
        }

    @cached_property
    def list_gmax(self):
        return [s.id for s in self.gmax_mapping.values()]

    @cached_property
    def species_id_by_type_index(self):
        ret = defaultdict(list)
        for pokemon in self.pokemon.values():
            for type in pokemon.types:
                ret[type.lower()].append(pokemon.id)
        return dict(ret)

    def list_type(self, type: str):
        return self.species_id_by_type_index.get(type.lower(), [])

    @cached_property
    def species_id_by_region_index(self):
        ret = defaultdict(list)
        for pokemon in self.pokemon.values():
            ret[pokemon.region.lower()].append(pokemon.id)
        return dict(ret)

    def list_region(self, region: str):
        return self.species_id_by_region_index.get(region.lower(), [])

    @cached_property
    def species_id_by_move_index(self):
        ret = defaultdict(list)
        for pokemon in self.all_pokemon():
            for pmove in pokemon.moves:
                ls = ret[pmove.move_id]
                if pokemon.id not in ls:
                    ls.append(pokemon.id)
        return dict(ret)

    def list_move(self, move_name: str):
        if not move_name:
            return [s.id for s in self.all_pokemon() if s.moves]

        move = self.move_by_name(move_name)
        if move is None:
            return []

        return self.species_id_by_move_index.get(move.id, [])

    def all_items(self):
        return self.items.values()

    @cached_property
    def species_by_dex_number_index(self):
        ret = defaultdict(list)
        for pokemon in self.pokemon.values():
            ret[pokemon.id].append(pokemon)
            if pokemon.id != pokemon.dex_number:
                ret[pokemon.dex_number].append(pokemon)
        return dict(ret)

    def all_species_by_number(self, number: int) -> Species:
        return self.species_by_dex_number_index.get(number, [])

    def all_species_by_name(self, name: str) -> Species:
        return self.species_by_name_index.get(
            deaccent(name.lower().replace("′", "'")), []
        )

    def find_all_matches(self, name: str) -> Species:
        return [
            y.id
            for x in self.all_species_by_name(name)
            for y in self.all_species_by_number(x.id)
        ]

    def species_by_number(self, number: int) -> Species:
        try:
            return self.pokemon[number]
        except KeyError:
            return None

    @cached_property
    def species_by_name_index(self):
        ret = defaultdict(list)
        for pokemon in self.pokemon.values():
            for name in pokemon.correct_guesses:
                ret[name].append(pokemon)
        return dict(ret)

    def species_by_name(self, name: str) -> Species:
        try:
            st = deaccent(name.lower().replace("′", "'"))
            return self.species_by_name_index[st][0]
        except (KeyError, IndexError):
            return None

    @cached_property
    def species_id_by_default_gender_index(self):
        ret = defaultdict(list)
        for pokemon in self.pokemon.values():
            default_gender = pokemon.default_gender
            default_gender = (
                default_gender.lower()
                if isinstance(default_gender, str)
                else default_gender
            )
            ret[default_gender].append(pokemon.id)
        return dict(ret)

    def list_default_gender(self, gender: str | None):
        gender = gender.lower() if isinstance(gender, str) else gender
        return self.species_id_by_default_gender_index.get(gender, [])

    def item_by_number(self, number: int) -> Item:
        try:
            return self.items[number]
        except KeyError:
            return None

    @cached_property
    def item_by_name_index(self):
        return {item.name.lower(): item for item in self.items.values()}

    def item_by_name(self, name: str) -> Item:
        return self.item_by_name_index.get(deaccent(name.lower().replace("′", "'")))

    def move_by_number(self, number: int) -> Move:
        try:
            return self.moves[number]
        except KeyError:
            return None

    @cached_property
    def move_by_name_index(self):
        return {move.name.lower(): move for move in self.moves.values()}

    def move_by_name(self, name: str) -> Move:
        # Replace to ’ (RIGHT SINGLE QUOTATION MARK) because move names use that instead of ' (APOSTROPHE)
        return self.move_by_name_index.get(deaccent(name.lower().replace("′", "’")))

    def random_spawn(self, rarity="normal"):
        if rarity == "mythical":
            pool = [x for x in self.all_pokemon() if x.catchable and x.mythical]
        elif rarity == "legendary":
            pool = [x for x in self.all_pokemon() if x.catchable and x.legendary]
        elif rarity == "ultra_beast":
            pool = [x for x in self.all_pokemon() if x.catchable and x.ultra_beast]
        else:
            pool = [x for x in self.all_pokemon() if x.catchable]

        x = random.choices(pool, weights=[x.abundance for x in pool], k=1)[0]

        return x

    @cached_property
    def spawn_weights(self):
        return [p.abundance for p in self.pokemon.values()]
