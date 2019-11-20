import socket
from PyQt5.QtCore import QThread, pyqtSignal
from urllib.error import URLError
from ..utils import network
from ..models.item import Item


class LoadPreviewThread(QThread):
    finished = pyqtSignal(Item, bool)

    def __init__(self, item: Item) -> None:
        QThread.__init__(self)
        self.item = item

    def run(self) -> None:
        try:
            network.download(self.item.thumbnailUrl, self.item.thumbnailPath)

            self.finished.emit(self.item, False)
        except URLError:
            self.finished.emit(self.item, True)
        except socket.timeout:
            self.finished.emit(self.item, True)
