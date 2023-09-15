import csv
from typing import Iterable
from pathlib import Path


def isnumber(v):
    try:
        int(v)
    except ValueError:
        return False
    return True


def get_data_from(filename):
    path = Path(__file__).parent / "csv" / filename

    with open(path) as f:
        reader = csv.DictReader(f)
        data = list({k: int(v) if isnumber(v) else v for k, v in row.items() if v != ""} for row in reader)

    return data


def comma_formatted(iterable: Iterable) -> str:
    """Function to take in a list and return a comma formatted string of its elements"""

    if len(iterable) == 0:
        return ""
    elif len(iterable) == 1:
        return str(iterable[0])

    return f"{', '.join(map(str, iterable[:-1]))} and {iterable[-1]}"
