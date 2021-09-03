import logging
import os
import re
from typing import List, Optional

from PyQt5.QtCore import QSize, QTimer
from PyQt5.QtGui import QMovie
from PyQt5.QtWidgets import QApplication, QDialog, QLabel

from bulk_reminders.api import Event
from bulk_reminders.load_base import Ui_Dialog

logger = logging.getLogger(__file__)
logger.setLevel(logging.DEBUG)

REGEX_FULL_PARSE = re.compile(
    r'\s*([\w\d\s,-.;\'!\[\]()]{1,})\s+\|\s+(\d{4}-\d{2}-\d{2})\s*(\d{1,2}:\d{2}(?:AM|PM))?\s*(\d{4}-\d{2}-\d{2})?\s*(\d{1,2}:\d{2}(?:AM|PM))?')


class LoadDialog(QDialog, Ui_Dialog):
    def __init__(self, *args, **kwargs):
        super(QDialog, self).__init__(*args, **kwargs)
        self.setupUi(self)

        self.spinner = QLabel()
        path = os.path.join(os.path.dirname(os.path.abspath(__file__)), 'loading.gif')
        self.movie = QMovie(path)
        self.movie.setScaledSize(QSize(26, 26))
        self.spinner.setMovie(self.movie)
        self.movie.start()
        self.spinner.hide()
        self.spinner.setFixedSize(23, 23)
        self.horizontalLayout.addWidget(self.spinner)

        self.plainTextEdit.textChanged.connect(self.edited)
        self.parseTimer = QTimer()
        self.parseTimer.timeout.connect(self.parse)
        self.parseTimer.setSingleShot(True)

        self.parsed: List[Event] = []
        self.eventCountLabel.setText('0 groups found.')

        self.show()

    def parse(self) -> None:
        """Parse the events entered into the dialog"""
        self.spinner.hide()
        results = [result.groups() for result in re.finditer(REGEX_FULL_PARSE, self.plainTextEdit.toPlainText())]
        resultsText = f'{len(results)} group{"s" if len(results) != 1 else ""} found.'
        try:
            self.parsed = list(map(Event.parse_raw, results))
            for event in self.parsed:
                logger.debug(f'Parsed: Event "{event.summary}" starts {event.start} and ends {event.end}')
        except ValueError as error:
            logger.warning('Dialog input has data errors (invalid dates etc.)', exc_info=error)
            resultsText += ' Data error.'
        self.eventCountLabel.setText(resultsText)

    def edited(self) -> None:
        """Prepare a timer to be fired to parse the edited text"""
        self.parseTimer.stop()
        self.spinner.show()
        self.parseTimer.start(500)  # 0.5 seconds
