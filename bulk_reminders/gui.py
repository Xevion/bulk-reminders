import dateutil
from PyQt5 import QtCore, QtGui, QtWidgets
from PyQt5.QtWidgets import QDialog, QMainWindow, QTableWidgetItem
from dateutil.parser import isoparse

from bulk_reminders import api, undo
from bulk_reminders.gui_base import Ui_MainWindow
from bulk_reminders.oauth import OAuthDialog


class MainWindow(QMainWindow, Ui_MainWindow):
    def __init__(self, *args, **kwargs):
        # Initial UI setup
        super(MainWindow, self).__init__(*args, **kwargs)
        self.setupUi(self)
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

        # Setup Column View headers
        self.eventsView.setColumnCount(4)
        self.eventsView.setHorizontalHeaderLabels(['Summary', 'Status', 'Start', 'End'])
        header = self.eventsView.horizontalHeader()
        header.setSectionResizeMode(0, QtWidgets.QHeaderView.Stretch)
        header.setSectionResizeMode(1, QtWidgets.QHeaderView.ResizeToContents)
        header.setSectionResizeMode(2, QtWidgets.QHeaderView.ResizeToContents)
        header.setSectionResizeMode(3, QtWidgets.QHeaderView.ResizeToContents)
        self.eventsView.verticalHeader().hide()

        self.undoButton.clicked().connect(self.undoEvents)
        self.submitButton.clicked().connect(self.submitEvents)

        # Disable the undo button until undo stages are available
        if len(undo.stages) == 0:
            self.undoButton.setDisabled(True)

        self.populate()

    def undo(self) -> None:
        latest = undo.stages.pop(0)
        for entry in latest:

        # Disable the undo button until undo stages are available
        if len(undo.stages) == 0:
            self.undoButton.setDisabled(True)

    def populate(self) -> None:
        """Re-populate the table with all of the events"""
        self.events = self.calendar.getEvents(self.currentCalendarID)
        self.eventsView.setRowCount(len(self.events))
        for row, event in enumerate(self.events):
            print(event)
            summaryItem = QTableWidgetItem(event['summary'])
            summaryItem.setData(QtCore.Qt.UserRole)
            summaryItem.setForeground(QtGui.QColor("blue"))
            self.eventsView.setItem(row, 0, summaryItem)
            start, end = event['start'], event['end']
            start, end = start.get('date') or start.get('dateTime'), end.get('date') or end.get('dateTime')
            start, end = isoparse(start), isoparse(end)

            formatString = '%b %d, %Y'if event['start'].get('date') is not None else '%b %d, %Y %I:%M %Z'
            self.eventsView.setItem(row, 1, QTableWidgetItem('Foreign'))
            self.eventsView.setItem(row, 2, QTableWidgetItem(start.strftime(formatString)))
            self.eventsView.setItem(row, 3, QTableWidgetItem(end.strftime(formatString)))


    @QtCore.pyqtSlot(int)
    def comboBoxChanged(self, row) -> None:
        """When the Calendar Selection combobox"""
        self.currentCalendarID = self.comboModel.item(row).data()
        self.populate()
