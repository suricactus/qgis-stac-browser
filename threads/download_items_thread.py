from typing import (List, Dict, Any)

import socket
from PyQt5.QtCore import (QThread, pyqtSignal)
from urllib.error import URLError
from ..models.item import Item
from ..utils import fs


class DownloadItemsThread(QThread):
    process = pyqtSignal(int, int, str)
    # TODO remove this gdal_error_signal, use the normal error signal
    gdal_error_signal = pyqtSignal(Exception)
    error = pyqtSignal(Item, Exception)
    addLayer = pyqtSignal(int, int, Item, str)
    finish = pyqtSignal()

    def __init__(self, downloads: List[Dict[str, Any]], downloadDir: str) -> None:
        QThread.__init__(self)

        self.downloads = downloads
        self.downloadDir = downloadDir

        self._currentItem = 0
        self._currentStep = 0
        self._totalSteps = 0

        for download in self.downloads:
            item = download['item']
            options = download['options']

            self._totalSteps += item.downloadSteps(options)

    def run(self) -> None:
        gdalPath = fs.gdalPath()

        for i, download in enumerate(self.downloads):
            self._currentItem = i

            item = download['item']
            options = download['options']

            try:
                item.download(
                    gdalPath,
                    options,
                    self.downloadDir,
                    onUpdate=self._onUpdate
                )

                if options.get('add_to_layers', False):
                    self.addLayer.emit(
                        self._currentStep,
                        self._totalSteps,
                        item,
                        self.downloadDir
                    )
            except URLError as err:
                self.error.emit(item, err)
            except socket.timeout as err:
                self.error.emit(item, err)
            except FileNotFoundError as err:
                self.gdal_error_signal.emit(err)

        self.finish.emit()

    def _onUpdate(self, status: str) -> None:
        self._currentStep += 1
        self.process.emit(
            self._currentStep,
            self._totalSteps,
            f'[{self._currentItem + 1}/{len(self.downloads)}] {status}'
        )
