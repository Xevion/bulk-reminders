import logging
from typing import Any, List, Set

from PyQt5 import QtCore, QtGui, QtWidgets
from PyQt5.QtWidgets import QMainWindow, QMessageBox

from bulk_reminders import api
from bulk_reminders.api import Event
from bulk_reminders.gui_base import Ui_MainWindow
from bulk_reminders.load import LoadDialog
from bulk_reminders.oauth import OAuthDialog
from bulk_reminders.undo import IDPair

logging.basicConfig(format='[%(asctime)s] [%(levelname)s] [%(threadName)s] %(message)s')
logger = logging.getLogger(__file__)
logger.setLevel(logging.DEBUG)


class MainWindow(QMainWindow, Ui_MainWindow):
    def __init__(self, *args, **kwargs):
        # Initial UI setup
        super(MainWindow, self).__init__(*args, **kwargs)
        self.setupUi(self)
        logger.debug('UI Initialized.')
        self.show()

        self.calendar = api.Calendar()
        self.currentCalendarID = 'primary'

        # Authenticate user into Google API Engine
        self.authenticated = self.calendar.authenticate_via_token()
        if not self.authenticated:
            temp_dialog = OAuthDialog(callback=self.calendar.authenticate_via_oauth)
            temp_dialog.show()
        self.calendar.setupService()

        # Get Calendars, Setup Calendar Selection Combobox
        calendars = self.calendar.getCalendarsSimplified()
        self.comboModel = QtGui.QStandardItemModel()
        for id, summary in calendars:
            item = QtGui.QStandardItem(summary)
            item.setData(id)
            self.comboModel.appendRow(item)
        self.calendarCombobox.setModel(self.comboModel)
        self.calendarCombobox.currentIndexChanged[int].connect(self.comboBoxChanged)

        # Make sure the current calendar ID matches up
        self.currentCalendarID = self.comboModel.item(self.calendarCombobox.currentIndex()).data()

        # Setup Column View headers
        self.eventsView.setColumnCount(4)
        self.eventsView.setHorizontalHeaderLabels(['Summary', 'Status', 'Start', 'End'])
        header = self.eventsView.horizontalHeader()
        header.setSectionResizeMode(0, QtWidgets.QHeaderView.Stretch)
        header.setSectionResizeMode(1, QtWidgets.QHeaderView.ResizeToContents)
        header.setSectionResizeMode(2, QtWidgets.QHeaderView.ResizeToContents)
        header.setSectionResizeMode(3, QtWidgets.QHeaderView.ResizeToContents)
        self.eventsView.verticalHeader().hide()

        self.undoButton.clicked.connect(self.undo)
        self.submitButton.clicked.connect(self.submit)

        self.history: List[IDPair] = []
        self.historyCalendarID: str = ''

        # Disable the undo button until undo stages are available
        if len(self.history) == 0:
            self.undoButton.setDisabled(True)

        self.loadEventsButton.clicked.connect(self.load_events)
        self.cachedLoadText = ''
        self.readyEvents: List[Event] = []
        self.apiEvents: List[dict] = []

        self.populate()

    def load_events(self) -> None:
        """Open the event loading dialog"""
        dial = LoadDialog()
        dial.plainTextEdit.setPlainText(self.cachedLoadText)
        result = dial.exec()

        if result == QMessageBox.Accepted:
            self.cachedLoadText = dial.plainTextEdit.toPlainText()
            self.readyEvents = dial.parsed
            self.populate()

    def undo(self) -> None:
        """Get the latest undo stage and delete all events in that stage"""
        logging.info(f'Deleting {len(self.history)} Events from Calendar {self.historyCalendarID}')

        self.progressBar.show()
        self.progressBar.setMaximum(len(self.history))
        for i, entry in enumerate(self.history):
            logging.debug(f'Deleting Event {entry.eventID}')
            self.calendar.service.events().delete(calendarId=entry.calendarID, eventId=entry.eventID).execute()
            self.progressBar.setValue(i + 1)
        self.progressBar.hide()

        # Disable the undo button until undo stages are available
        self.history = []
        self.undoButton.setDisabled(len(self.history) == 0)
        self.populate()  # Refresh

    def getForeign(self) -> Set[Any]:
        """Returns all events currently tracked that are not stored in the undo."""
        foreign = {event.get('id'): event for event in self.apiEvents}
        undoableIDs = set(pair.eventID for pair in self.history)
        return {foreign[eventID] for eventID in undoableIDs.difference(foreign.keys())}

    def submit(self) -> None:
        self.historyCalendarID = self.currentCalendarID
        self.history = []

        logger.info(f'Submitting {len(self.readyEvents)} events to API')

        self.progressBar.show()
        self.progressBar.setMaximum(len(self.readyEvents))
        for i, event in enumerate(self.readyEvents):
            logger.debug(f'Submitting "{event.summary}" scheduled to start on {event.start.isoformat()}....')
            result = self.calendar.service.events().insert(calendarId=self.currentCalendarID, body=event.body).execute()
            self.history.append(IDPair(self.currentCalendarID, result.get('id')))
            self.progressBar.setValue(i + 1)

        self.undoButton.setDisabled(len(self.history) == 0)
        self.readyEvents.clear()
        self.progressBar.hide()

        self.populate()

    def populate(self) -> None:
        """Re-populate the table with all of the events"""
        self.apiEvents = self.calendar.getEvents(self.currentCalendarID)

        events = list(self.readyEvents)
        events.extend([Event.from_api(event, self.history) for event in self.apiEvents])

        ready, undoable, foreign = len(self.readyEvents), len(self.history), len(list(self.getForeign()))
        total = ready + undoable + foreign
        self.eventCountLabel.setText(f'{len(self.readyEvents)} ready, {undoable} undoable, {foreign} foreign ({total})')

        self.eventsView.setRowCount(len(events))
        logger.debug(f'Populating table with {self.eventsView.rowCount()} events.')
        for row, event in enumerate(events):
            logger.debug(f'Event "{event.summary}" starts {event.start} and ends {event.end}')
            event.fill_row(row, self.eventsView)

        self.submitButton.setDisabled(len(self.readyEvents) < 0)

    @QtCore.pyqtSlot(int)
    def comboBoxChanged(self, row) -> None:
        """When the Calendar Selection combobox"""
        self.currentCalendarID = self.comboModel.item(row).data()
        logger.info(f'Switching to Calendar "{self.comboModel.item(row).text()} ({self.currentCalendarID})"')
        self.populate()
