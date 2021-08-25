import json
import os
from typing import List


class HistoryManager(object):
    def __init__(self, file: str) -> None:
        self.file = file
        self.stages: List[Stage] = []

        # Immediately load data if possible
        if os.path.exists(self.file):
            self.load()

    def pop(self) -> 'Stage':
        """Remove the latest Stage and return it"""
        return self.stages.pop(0)

    def load(self) -> None:
        """Load data from the undo history file"""
        with open(self.file, 'r') as history:
            self.stages = json.load(history)

    def save(self) -> None:
        """Save data to the undo history file."""
        with open(self.file, 'w') as history:
            json.dump(self.stages, history)

    def getTotal(self) -> int:
        """Returns the total number of undoable events known."""
        return sum(len(stage) for stage in self.stages)

    def exists(self, id: 'IDPair') -> int:
        """Check if a given ID exists anywhere in the undo history data. Returns the stage index or -1 if it wasn't found."""
        for stage in self.stages:
            for stageID in stage.events:
                if id == stageID:
                    return stage.index
        return -1


class Stage(object):
    def __init__(self, index: int) -> None:
        self.index = index
        self.events: List[IDPair] = []

    def __contains__(self, item) -> bool:
        if type(item) is IDPair:
            return item in self.events
        return False

    def __len__(self) -> int:
        """The len function on a Stage object returns the number of events in the stage."""
        return len(self.events)


class IDPair(object):
    def __init__(self, calendarID: str, eventID: str) -> None:
        self.calendarID, self.eventID = calendarID, eventID

    def __eq__(self, other):
        """Check equality between two IDPair objects or two item tuple."""
        if type(other) is IDPair:
            return self.calendarID == other.calendarID and self.eventID == other.calendarID
        elif type(other) is tuple:
            return len(other) == 2 and other == (self.calendarID, self.eventID)
        return False
