import json
import os

stages = []


def load() -> None:
    """Load data from the undo history file"""
    with open('history.json', 'r') as history:
        stages = json.load(history)


def save() -> None:
    """Save data to the undo history file."""
    with open('history.json', 'w') as history:
        stages = json.dump(history)


if os.path.exists('history.json'):
    load()


def getTotal() -> int:
    """Returns the total number of undoable events known."""
    return sum(len(stage) for stage in stages)
