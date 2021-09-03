import logging
from typing import Iterator, List

from PyQt5 import QtCore, QtGui, QtWidgets
from PyQt5.QtWidgets import QMainWindow, QMessageBox

from bulk_reminders import api, undo
from bulk_reminders.api import Event
from bulk_reminders.gui_base import Ui_MainWindow
from bulk_reminders.load import LoadDialog
from bulk_reminders.oauth import OAuthDialog
from bulk_reminders.undo import IDPair, Stage

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

        self.history = undo.HistoryManager('history.json')

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
        latest = self.history.pop()
        logging.info(f'Deleting {len(latest.events)} Events from Calendar {latest.commonCalendar}')

        self.progressBar.show()
        self.progressBar.setMaximum(len(latest.events))
        for i, entry in enumerate(latest.events):
            logging.debug(f'Deleting Event {entry.eventID}')
            self.calendar.service.events().delete(calendarId=entry.calendarID, eventId=entry.eventID).execute()
            self.progressBar.setValue(i + 1)
        self.progressBar.hide()

        # Disable the undo button until undo stages are available
        self.undoButton.setDisabled(len(self.history) == 0)
        self.populate()  # Refresh

    def getForeign(self) -> Iterator[IDPair]:
        """Returns all events currently tracked that are not stored in the undo."""
        undoableIDs = set(self.history.all_pairs())
        for apiEvent in self.apiEvents:
            pair = IDPair(calendarID=self.currentCalendarID, eventID=apiEvent['id'])
            if pair not in undoableIDs:
                yield pair

    def submit(self) -> None:
        newStage = Stage(index=self.history.nextIndex(), commonCalendar=self.currentCalendarID)
        logger.info(f'Submitting {len(self.readyEvents)} events to API')

        self.progressBar.show()
        self.progressBar.setMaximum(len(self.readyEvents))
        for i, event in enumerate(self.readyEvents):
            logger.debug(f'Submitting "{event.summary}" scheduled to start on {event.start.isoformat()}....')
            result = self.calendar.service.events().insert(calendarId=self.currentCalendarID, body=event.body).execute()
            newStage.events.append(IDPair(self.currentCalendarID, result.get('id')))
            self.progressBar.setValue(i + 1)

        self.readyEvents.clear()
        self.progressBar.hide()

        self.history.addStage(newStage)
        self.populate()

    def populate(self) -> None:
        """Re-populate the table with all of the events"""
        self.apiEvents = self.calendar.getEvents(self.currentCalendarID)

        events = list(self.readyEvents)
        events.extend([Event.from_api(event, self.history) for event in self.apiEvents])

        ready, undoable, stage, foreign = len(self.readyEvents), self.history.getTotal(), len(self.history), len(list(self.getForeign()))
        total = ready + undoable + foreign
        self.eventCountLabel.setText(f'{len(self.readyEvents)} ready, {undoable} undoable in {stage} stages, {foreign} foreign ({total})')

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
