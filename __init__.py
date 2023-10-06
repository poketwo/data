from collections import defaultdict
from urllib.parse import urljoin

from .constants import ARTISTS, DESCRIPTION_LINK_REGEX
from .utils import comma_formatted, get_data_from, isnumber

from . import models


def get_pokemon(instance):
    species = {x["id"]: x for x in get_data_from("pokemon.csv")}
    evolution = {x["evolved_species_id"]: x for x in reversed(get_data_from("evolution.csv"))}

    def get_evolution_trigger(pid):
        evo = evolution[pid]

        if evo["evolution_trigger_id"] == 1:
            level = evo.get("minimum_level", None)
            item = evo.get("held_item_id", None)
            move = evo.get("known_move_id", None)
            movetype = evo.get("known_move_type_id", None)
            time = evo.get("time_of_day", None)
            relative_stats = evo.get("relative_physical_stats", None)

            if "location_id" in evo:
                return models.OtherTrigger(instance=instance)

            if "minimum_happiness" in evo:
                item = 14001

            return models.LevelTrigger(
                level=level,
                item_id=item,
                move_id=move,
                move_type_id=movetype,
                time=time,
                relative_stats=relative_stats,
                instance=instance,
            )

        elif evo["evolution_trigger_id"] == 2:
            if "held_item_id" in evo:
                return models.TradeTrigger(evo["held_item_id"], instance=instance)
            return models.TradeTrigger(instance=instance)

        elif evo["evolution_trigger_id"] == 3:
            if "trigger_item_id" in evo:
                return models.ItemTrigger(evo["trigger_item_id"], instance=instance)
            return models.OtherTrigger(instance=instance)

        return models.OtherTrigger(instance=instance)

    pokemon = {}

    for row in species.values():
        if "enabled" not in row:
            continue

        evo_from = evo_to = None

        if "evo.from" in row:
            evo_from = models.Evolution.evolve_from(
                row["evo.from"], get_evolution_trigger(row["id"]), instance=instance
            )

        if "evo.to" in row:
            evo_to = []

            for s in str(row["evo.to"]).split():
                pto = species[int(s)]
                evo_to.append(models.Evolution.evolve_to(int(s), get_evolution_trigger(pto["id"]), instance=instance))

        if evo_to and len(evo_to) == 0:
            evo_to = None

        types = []
        if "type.0" in row:
            types.append(row["type.0"])
        if "type.1" in row:
            types.append(row["type.1"])

        names = []

        if "name.ja" in row:
            names.append(("🇯🇵", row["name.ja"]))

        if "name.ja_r" in row:
            names.append(("🇯🇵", row["name.ja_r"]))

        if "name.ja_t" in row and row["name.ja_t"] != row.get("name.ja_r"):
            names.append(("🇯🇵", row["name.ja_t"]))

        if "name.en" in row:
            names.append(("🇬🇧", row["name.en"]))

        if "name.en2" in row:
            names.append(("🇬🇧", row["name.en2"]))

        if "name.de" in row:
            names.append(("🇩🇪", row["name.de"]))

        if "name.fr" in row:
            names.append(("🇫🇷", row["name.fr"]))

        art_credit = row.get("credit")
        if art_credit:
            # Each user in the credit must be separated by `|`.
            # And gotta make sure that no username ever contains a `|`,
            # but ideally they should all be user ID anyway
            artist_ids = [int(s) if isnumber(s) else s.strip() for s in str(art_credit).split("|")]
            artists = [ARTISTS.get(aid, aid) for aid in artist_ids]
            art_credit = comma_formatted(artists)

        pokemon[row["id"]] = models.Species(
            id=row["id"],
            names=names,
            slug=row["slug"],
            base_stats=models.Stats(
                row["base.hp"],
                row["base.atk"],
                row["base.def"],
                row["base.satk"],
                row["base.sdef"],
                row["base.spd"],
            ),
            types=types,
            height=int(row["height"]) / 10,
            weight=int(row["weight"]) / 10,
            mega_id=row["evo.mega"] if "evo.mega" in row else None,
            mega_x_id=row["evo.mega_x"] if "evo.mega_x" in row else None,
            mega_y_id=row["evo.mega_y"] if "evo.mega_y" in row else None,
            catchable="catchable" in row,
            dex_number=row["dex_number"],
            abundance=row["abundance"] if "abundance" in row else 0,
            gender_rate=row["gender_rate"] if "gender_rate" in row else -1,
            has_gender_differences=row["has_gender_differences"] if "has_gender_differences" in row else 0,
            description=row.get("description", None),
            evolution_from=models.EvolutionList(evo_from) if evo_from else None,
            evolution_to=models.EvolutionList(evo_to) if evo_to else None,
            mythical="mythical" in row,
            legendary="legendary" in row,
            ultra_beast="ultra_beast" in row,
            event="event" in row,
            is_form="is_form" in row,
            form_item=row["form_item"] if "form_item" in row else None,
            region=row["region"],
            art_credit=art_credit,
            instance=instance,
        )

    moves = get_data_from("pokemon_moves.csv")
    version_group = defaultdict(int)
    for row in moves:
        version_group[row["pokemon_id"]] = max(version_group[row["pokemon_id"]], row["version_group_id"])

    for row in moves:
        if (
            row["pokemon_move_method_id"] == 1
            and row["pokemon_id"] in pokemon
            and row["version_group_id"] == version_group[row["pokemon_id"]]
        ):
            if row["move_id"] not in instance.moves:
                continue
            pokemon[row["pokemon_id"]].moves.append(
                models.PokemonMove(
                    row["move_id"],
                    models.LevelMethod(row["level"], instance=instance),
                    instance=instance,
                )
            )

    for p in pokemon.values():
        p.moves.sort(key=lambda x: x.method.level)

    return pokemon


def get_items(instance):
    data = get_data_from("items.csv")

    items = {}

    for row in data:
        items[row["id"]] = models.Item(
            id=row["id"],
            name=row["name"],
            description=row.get("description", None),
            cost=row["cost"],
            page=row["page"],
            action=row["action"],
            inline=(not "separate" in row),
            emote=row.get("emote", None),
            shard="shard" in row,
            instance=instance,
        )

    return items


def get_effects(instance):
    data = get_data_from("move_effect_prose.csv")

    effects = {}

    for row in data:
        description = DESCRIPTION_LINK_REGEX.sub(r"\1", row["short_effect"])
        description = description.replace("$effect_chance", "{effect_chance}")
        effects[row["move_effect_id"]] = models.MoveEffect(
            id=row["move_effect_id"], description=description, instance=instance
        )

    return effects


def get_moves(instance):
    data = get_data_from("moves.csv")
    names = {x["move_id"]: x["name"] for x in get_data_from("move_names.csv") if x["local_language_id"] == 9}

    meta = {x["move_id"]: x for x in get_data_from("move_meta.csv")}
    meta_stats = defaultdict(list)
    for x in get_data_from("move_meta_stat_changes.csv"):
        meta_stats[x["move_id"]].append(x)
        x.pop("move_id")

    moves = {}

    for row in data:
        if row["id"] > 10000:
            continue

        try:
            mmeta = meta[row["id"]]
        except KeyError:
            continue
        mmeta.pop("move_id")

        stat_changes = meta_stats.get(row["id"], [])
        stat_changes = [models.StatChange(**x) for x in stat_changes]

        effect_id = row["effect_id"]
        accuracy = row.get("accuracy", None)
        if "never misses" in instance.effects[effect_id].description.lower():
            accuracy = 100

        moves[row["id"]] = models.Move(
            id=row["id"],
            slug=row["identifier"],
            name=names[row["id"]],
            power=row.get("power", None),
            pp=row["pp"],
            accuracy=accuracy,
            priority=row["priority"],
            type_id=row["type_id"],
            target_id=row["target_id"],
            damage_class_id=row["damage_class_id"],
            effect_id=effect_id,
            effect_chance=row.get("effect_chance", None),
            instance=instance,
            meta=models.MoveMeta(**mmeta, stat_changes=stat_changes),
        )

    return moves


class DataManager(models.DataManagerBase):
    def __init__(self, assets_base_url=None):
        self.effects = get_effects(self)
        self.moves = get_moves(self)
        self.pokemon = get_pokemon(self)
        self.items = get_items(self)

        if assets_base_url is not None:
            self.assets_base_url = assets_base_url

    def asset(self, path):
        base_url = getattr(self, "assets_base_url", "https://cdn.poketwo.net")
        return urljoin(base_url, path)
