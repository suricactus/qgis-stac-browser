import socket
from PyQt5.QtCore import QThread, pyqtSignal
from urllib.error import URLError
from ..models.api import API


class LoadAPIDataThread(QThread):
    error = pyqtSignal(Exception)
    success = pyqtSignal(API)

    def __init__(self, api: API) -> None:
        QThread.__init__(self)
        self.api = api

    def run(self) -> None:
        try:
            self.api.load()
            self.success.emit(self.api)
        except URLError as err:
            self.error.emit(err)
        except socket.timeout as err:
            self.error.emit(err)
