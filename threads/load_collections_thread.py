import socket
from PyQt5.QtCore import QThread, pyqtSignal
from urllib.error import URLError
from ..models.api import API


class LoadCollectionsThread(QThread):
    """Thread to asyncroniously load collections."""

    progress = pyqtSignal(float, str)
    error = pyqtSignal(Exception, API)
    finished = pyqtSignal(list)

    def __init__(self, apiList: API) -> None:
        QThread.__init__(self)

        self.apiList = apiList

    def run(self) -> None:
        apis = []

        for i, api in enumerate(self.apiList):
            progress = (float(i) / float(len(self.apiList)))
            self.progress.emit(progress, api.href)
            
            try:
                api.load()
                apis.append(api)
            except URLError as e:
                self.error.emit(e, api)
            except socket.timeout as e:
                self.error.emit(e, api)

        self.finished.emit(apis)
