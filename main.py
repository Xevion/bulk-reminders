from PyQt5.QtWidgets import QApplication

from bulk_reminders.gui import MainWindow

if __name__ == '__main__':
    app = QApplication([])
    app.setApplicationName("TCPChat Client")
    window = MainWindow()
    app.exec_()
