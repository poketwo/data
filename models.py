import random
import unicodedata
from collections import defaultdict
from functools import cached_property
from typing import Any, List, NamedTuple, Optional, Tuple, Union

from . import constants


def deaccent(text):
    norm = unicodedata.normalize("NFD", text)
    result = "".join(ch for ch in norm if unicodedata.category(ch) != "Mn")
    return unicodedata.normalize("NFC", result)


class UnregisteredError(Exception):
    __slots__ = ()


class UnregisteredDataManager:
    __slots__ = ()


# Moves


class MoveEffect(NamedTuple):
    id: int
    description: str

    instance: Any = None


class StatChange(NamedTuple):
    stat_id: int
    change: int

    @cached_property
    def stat(self):
        return ("hp", "atk", "defn", "satk", "sdef", "spd", "evasion", "accuracy")[
            self.stat_id - 1
        ]


class StatStages(NamedTuple):
    hp: int = 0
    atk: int = 0
    defn: int = 0
    satk: int = 0
    sdef: int = 0
    spd: int = 0
    evasion: int = 0
    accuracy: int = 0
    crit: int = 0


class MoveResult(NamedTuple):
    success: bool
    damage: int
    healing: int
    ailment: str
    messages: List[str]
    stat_changes: List[StatChange]


class MoveMeta(NamedTuple):
    meta_category_id: int
    meta_ailment_id: int
    drain: int
    healing: int
    crit_rate: int
    ailment_chance: int
    flinch_chance: int
    stat_chance: int
    min_hits: Optional[int] = None
    max_hits: Optional[int] = None
    min_turns: Optional[int] = None
    max_turns: Optional[int] = None
    stat_changes: List[StatChange] = None

    @cached_property
    def meta_category(self):
        return constants.MOVE_META_CATEGORIES[self.meta_category_id]

    @cached_property
    def meta_ailment(self):
        return constants.MOVE_AILMENTS[self.meta_ailment_id]


class Move(NamedTuple):
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

    instance: Any = None

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
            typ_mult *= constants.TYPE_EFFICACY[self.type_id][
                constants.TYPES.index(typ)
            ]

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


class Item(NamedTuple):
    id: int
    name: str
    description: str
    cost: int
    page: int
    action: str
    inline: bool
    emote: str = None
    shard: bool = False

    instance: Any = None

    def __str__(self):
        return self.name


class LevelMethod(NamedTuple):
    level: int

    instance: Any = None

    @cached_property
    def text(self):
        return f"Level {self.level}"


class PokemonMove(NamedTuple):
    move_id: int
    method: Any

    instance: Any = None

    @cached_property
    def move(self):
        return self.instance.moves[self.move_id]

    @cached_property
    def text(self):
        return self.method.text


# Evolution


class LevelTrigger(NamedTuple):
    level: int
    item_id: int
    move_id: int
    move_type_id: int
    time: str
    relative_stats: int

    instance: Any = None

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
    def text(self):
        if self.level is None:
            text = f"when leveled up"
        else:
            text = f"starting from level {self.level}"

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

        return text


class ItemTrigger(NamedTuple):
    item_id: int

    instance: Any = None

    @cached_property
    def item(self):
        return self.instance.items[self.item_id]

    @cached_property
    def text(self):
        return f"using a {self.item}"


class TradeTrigger(NamedTuple):
    item_id: int = None

    instance: Any = None

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


class OtherTrigger(NamedTuple):
    instance: Any = None

    @cached_property
    def text(self):
        return "somehow"


class Evolution(NamedTuple):
    target_id: int
    trigger: Any
    type: bool

    instance: Any = None

    @classmethod
    def evolve_from(cls, target: int, trigger: Any, instance=None):
        return cls(target, trigger, False, instance=instance)

    @classmethod
    def evolve_to(cls, target: int, trigger: Any, instance=None):
        return cls(target, trigger, True, instance=instance)

    @cached_property
    def dir(self) -> str:
        return "to" if self.type == True else "from" if self.type == False else "??"

    @cached_property
    def target(self):
        return self.instance.pokemon[self.target_id]

    @cached_property
    def text(self):
        if getattr(self.target, f"evolution_{self.dir}") is not None:
            pevo = getattr(self.target, f"evolution_{self.dir}")
            return f"evolves {self.dir} {self.target} {self.trigger.text}, which {pevo.text}"

        return f"evolves {self.dir} {self.target} {self.trigger.text}"


class EvolutionList:
    __slots__ = ("items",)

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


class Stats(NamedTuple):
    hp: int
    atk: int
    defn: int
    satk: int
    sdef: int
    spd: int


# Species


class Species(NamedTuple):
    id: int
    name: str
    names: List[Tuple[str, str]]
    slug: str
    base_stats: Stats
    height: int
    weight: int
    dex_number: int
    catchable: bool
    types: List[str]
    abundance: int
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
    moves: List[PokemonMove] = None
    region: str = None

    instance: Any = None

    def __str__(self):
        return self.name

    @cached_property
    def moveset(self):
        return [self.instance.moves[x] for x in self.moveset_ids]

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
    def image_url(self):
        return f"https://assets.poketwo.net/images/{self.id}.png?v=26"

    @cached_property
    def shiny_image_url(self):
        return f"https://assets.poketwo.net/shiny/{self.id}.png?v=26"

    @cached_property
    def correct_guesses(self):
        extra = []
        if self.is_form:
            extra.extend(self.instance.pokemon[self.dex_number].correct_guesses)
        if "nidoran" in self.slug:
            extra.append("nidoran")
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
        if self.is_form and self.form_item is not None:
            species = self.instance.pokemon[self.dex_number]
            item = self.instance.items[self.form_item]
            return f"{self.name} transforms from {species} when given a {item.name}."

        if self.evolution_from is not None and self.evolution_to is not None:
            return (
                f"{self.name} {self.evolution_from.text} and {self.evolution_to.text}."
            )
        elif self.evolution_from is not None:
            return f"{self.name} {self.evolution_from.text}."
        elif self.evolution_to is not None:
            return f"{self.name} {self.evolution_to.text}."
        else:
            return None


class DataManagerBase:
    __slots__ = ("pokemon", "items", "effects", "moves")

    def __init__(self, pokemon, items, effects, moves) -> None:
        self.pokemon = pokemon
        self.items = items
        self.effects = effects
        self.moves = moves

    def all_pokemon(self):
        return self.pokemon.values()

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

    def all_items(self):
        return self.items.values()

    @cached_property
    def species_by_dex_number_index(self):
        ret = defaultdict(list)
        for pokemon in self.pokemon.values():
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
        return self.move_by_name_index.get(deaccent(name.lower().replace("′", "'")))

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
