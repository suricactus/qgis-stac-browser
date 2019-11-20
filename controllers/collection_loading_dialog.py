from typing import (Dict, Any, List, Callable)

import time
import urllib.error

from PyQt5 import uic
from PyQt5.QtCore import QEvent
from PyQt5.QtWidgets import (QDialog, QWidget)

from qgis.gui import QgisInterface
from qgis.utils import iface

from stac_browser.utils import ui
from stac_browser.utils.config import Config
from stac_browser.utils.logging import error
from stac_browser.utils.types import (DataT, HooksT)
from stac_browser.threads.load_collections_thread import LoadCollectionsThread
from stac_browser.models.api import API


FORM_CLASS: Any
FORM_CLASS, _ = uic.loadUiType(ui.path('collection_loading_dialog.ui'))


class CollectionLoadingDialog(QDialog, FORM_CLASS):
    def __init__(self, data: DataT = {}, hooks: HooksT = {}, parent: QWidget = None) -> None:
        super(CollectionLoadingDialog, self).__init__(parent)

        self.data = data
        self.hooks = hooks

        self.setupUi(self)
        self.setFixedSize(self.size())

        self.loadingThread = LoadCollectionsThread(Config().apis)

        self.loadingThread.progress.connect(self._onProgressUpdate)
        self.loadingThread.error.connect(self._onError)
        self.loadingThread.finished.connect(self._onLoadingFinished)

        self.loadingThread.start()

    def _onProgressUpdate(self, progress: float, api: API) -> None:
        self.label.setText(f'Loading {api}')
        self.progressBar.setValue(int(progress * 100))

    def _onError(self, err: Exception, api: API) -> None:
        if type(err) == urllib.error.URLError:
            error(iface, f'Failed to load {api.href}; {err.reason}')
        else:
            error(iface, f'Failed to load {api.href}; {type(err).__name__}')

    def _onLoadingFinished(self, apis: List[API]) -> None:
        config = Config()
        config.apis = apis
        config.last_update = time.time()
        config.save()

        self.progressBar.setValue(100)
        self.hooks['on_finished'](apis)

    def closeEvent(self, event: QEvent) -> None:
        if event.spontaneous():
            self.loadingThread.terminate()
            self.hooks['on_close']()
