from typing import Callable, Optional

from PyQt5.QtCore import Qt
from PyQt5.QtWidgets import QDialog

from bulk_reminders.oauth_base import Ui_Dialog

class OAuthDialog(QDialog, Ui_Dialog):
    def __init__(self, *args, callback: Optional[Callable] = None, **kwargs):
        super(QDialog, self).__init__(*args, **kwargs)
        self._closable = False
        self.setupUi(self)
        self.show()

        if callback is not None:
            callback()
            self.accept()
        else:
            self.reject()
        self._closable = True

    def closeEvent(self, evnt):
        if self.closable:
            super(QDialog, self).closeEvent(evnt)
        else:
            evnt.ignore()
            self.setWindowState(Qt.WindowMinimized)

