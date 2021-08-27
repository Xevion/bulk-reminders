import logging
import os
from typing import Iterator, List

import jsonpickle

logger = logging.getLogger(__file__)
logger.setLevel(logging.DEBUG)


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
        logger.info('Loading from undo history file.')
        with open(self.file, 'r') as file:
            self.stages = jsonpickle.decode(file.read())

    def save(self) -> None:
        """Save data to the undo history file."""
        logger.info('Saving to undo history file.')
        with open(self.file, 'w') as file:
            file.write(jsonpickle.encode(self.stages, indent=4))

    def getTotal(self) -> int:
        """Returns the total number of undoable events known."""
        return sum(len(stage) for stage in self.stages)

    def exists(self, eventID: 'IDPair') -> int:
        """Check if a given Event ID exists anywhere in the undo history data. Returns the stage index or -1 if it wasn't found."""
        for stage in self.stages:
            for undoable in stage.events:
                if eventID == undoable.eventID:
                    logger.debug(f'Found Event {eventID} in Stage {stage.index}')
                    return stage.index
        return -1

    def all_pairs(self) -> Iterator['IDPair']:
        """Generator for every IDPair object within the master HistoryManager"""
        for stage in self.stages:
            for event in stage.events:
                yield event

    def __len__(self) -> int:
        """Returns the number of stages"""
        return len(self.stages)

    def nextIndex(self):
        """Gets the next index (for a new stage)"""
        if len(self.stages) == 0:
            return 0
        return self.stages[0].index + 1

    def addStage(self, newStage: 'Stage'):
        """Adds and inserts a new Stage at the start of the history."""
        logger.debug(f'Adding new stage with {len(newStage)} events.')
        self.stages.insert(0, newStage)
        self.save()


class Stage(object):
    def __init__(self, index: int, commonCalendar: str) -> None:
        self.index = index
        self.commonCalendar = commonCalendar
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

    def __hash__(self):
        """Returns a hash value for the IDPair"""
        return hash((self.calendarID, self.eventID))
