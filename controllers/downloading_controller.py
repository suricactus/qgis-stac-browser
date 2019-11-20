from typing import (List, Dict, Any, Optional)

import os
import urllib

from PyQt5 import QtCore
from PyQt5.QtCore import QEvent
from PyQt5.QtWidgets import QProgressBar

from qgis.core import (QgsRasterLayer, QgsProject, Qgis)
from qgis.gui import QgsMessageBar
from qgis.utils import iface

from stac_browser.utils.logging import error
from stac_browser.utils.types import (DataT, HooksT)
from stac_browser.threads.download_items_thread import DownloadItemsThread
from stac_browser.models.item import Item


class DownloadController:
    def __init__(self, data: DataT = {}, hooks: HooksT = {}) -> None:
        self.data = data
        self.hooks = hooks

        self._progressMessageBar: Optional[QgsMessageBar] = None
        self._progress: Optional[QProgressBar] = None
        self._loadingClosed = False

        self.loadingThread = DownloadItemsThread(self._downloads, self._downloadDirectory)
        self.loadingThread.process.connect(self._onProgressUpdate)
        self.loadingThread.error.connect(self._onError)
        self.loadingThread.gdal_error_signal.connect(self._onGdalError)
        self.loadingThread.addLayer.connect(self._onAddLayer)
        self.loadingThread.finish.connect(self._onDownloadingFinished)
        self.loadingThread.start()

    @property
    def _downloads(self) -> List[Dict[str, Any]]:
        return self.data.get('downloads', [])

    @property
    def _downloadDirectory(self) -> str:
        return self.data.get('download_directory', None)

    def _onGdalError(self, err: Exception) -> None:
        error(iface, f'Unable to find "gdalbuildvrt" in current path')

    def _onError(self, item: Item, err: Exception) -> None:
        if type(err) == urllib.error.URLError:
            error(iface, f'Failed to load {item.id}; {err.reason}')
        else:
            error(iface, f'Failed to load {item.id}; {type(err).__name__}')

    def _onAddLayer(self, currentStep: int, totalSteps: int, item: Item, downloadDirectory: str) -> None:
        self._onProgressUpdate(currentStep, totalSteps, 'ADDING_TO_LAYERS')

        filename = os.path.join(downloadDirectory, f'{item.id}.vrt')
        layer = QgsRasterLayer(filename, item.id)

        QgsProject.instance().addMapLayer(layer)

    def _onDestroyed(self, event: QEvent) -> None:
        self._loadingClosed = True
        if not self.loadingThread.isFinished:
            self.loadingThread.terminate()

    def _onProgressUpdate(self, currentStep: int, totalSteps: int, status: str) -> None:
        if self._loadingClosed:
            return

        if self._progressMessageBar is None:
            self._progressMessageBar = iface.messageBar().createMessage(status)
            self._progressMessageBar.destroyed.connect(self._onDestroyed)
            self._progress = QProgressBar()
            self._progress.setMaximum(totalSteps)
            self._progress.setAlignment(
                QtCore.Qt.AlignRight | QtCore.Qt.AlignVCenter
            )
            self._progressMessageBar.layout().addWidget(self._progress)
            iface.messageBar().pushWidget(self._progressMessageBar, Qgis.Info)
        else:
            self._progressMessageBar.setText(status)

        if self._progress is not None:
            self._progress.setValue(currentStep - 1)

    def _onDownloadingFinished(self) -> None:
        iface.messageBar().clearWidgets()
