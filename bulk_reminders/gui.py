from PyQt5 import QtCore, QtGui
from PyQt5.QtWidgets import QDialog, QMainWindow

from bulk_reminders import api
from bulk_reminders.gui_base import Ui_MainWindow
from bulk_reminders.oauth import OAuthDialog


class MainWindow(QMainWindow, Ui_MainWindow):
    def __init__(self, *args, **kwargs):
        # Initial UI setup
        super(MainWindow, self).__init__(*args, **kwargs)
        self.setupUi(self)
        self.show()

        calendar = api.Calendar()

        # Authenticate user into Google API Engine
        self.authenticated = calendar.authenticate_via_token()
        if not self.authenticated:
            temp_dialog = OAuthDialog(callback=calendar.authenticate_via_oauth)
            temp_dialog.show()
        calendar.setupService()

        # Get Calendars, Setup Calendar Selection Combobox
        calendars = calendar.getCalendarsSimplified()
        self.comboModel = QtGui.QStandardItemModel()
        for id, summary in calendars:
            item = QtGui.QStandardItem(summary)
            item.setData(id)
            self.comboModel.appendRow(item)
        self.calendarCombobox.setModel(self.comboModel)
        self.calendarCombobox.currentIndexChanged[int].connect(self.comboBoxChanged)

    @QtCore.pyqtSlot(int)
    def comboBoxChanged(self, row) -> None:
        """When the Calendar Selection combobox"""
        self.currentCalendar = self.comboModel.item(row).data()
