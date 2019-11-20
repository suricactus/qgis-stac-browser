from typing import (Any, List)

from urllib.error import (URLError, HTTPError)

from PyQt5 import uic
from PyQt5.QtWidgets import (QDialog, QWidget)
from PyQt5.QtCore import QEvent

from qgis.utils import iface

from stac_browser.utils import ui
from stac_browser.utils.logging import error
from stac_browser.utils.types import (HooksT, DataT)
from stac_browser.threads.load_items_thread import LoadItemsThread
from stac_browser.models.api import API

FORM_CLASS: Any
FORM_CLASS, _ = uic.loadUiType(ui.path('item_loading_dialog.ui'))


class ItemLoadingDialog(QDialog, FORM_CLASS):
    def __init__(self, data: DataT, hooks: HooksT, parent: QWidget):
        super(ItemLoadingDialog, self).__init__(parent)

        self.data = data
        self.hooks = hooks

        self.setupUi(self)
        self.setFixedSize(self.size())

        self.loadingThread = LoadItemsThread(self.data['api_collections'],
                                             self.data['extent'],
                                             self.data['start_time'],
                                             self.data['end_time'],
                                             self.data['query']
                                             )
        self.loadingThread.progress.connect(self._onProgress)
        self.loadingThread.error.connect(self._onError)
        self.loadingThread.finish.connect(self._onFinished)

        self.loadingThread.start()

    def _onProgress(self, api: API, collections: List, currentPage: int):
        collectionLabel = ', '.join([c.title for c in collections])

        self.loadingLabel.setText('\n'.join((
            f'Searching {api.title}',
            f'Collections: [{collectionLabel}]',
            f'Page {currentPage}...'
        )))

    def _onError(self, err: Exception) -> None:
        if type(err) == URLError:
            error(iface, f'Network Error: {err.reason}')
        elif type(err) == HTTPError:
            error(iface, f'Network Error: [{err.code}] {err.reason}')
        else:
            error(iface, f'Network Error: {type(err).__name__}')

        self.hooks['on_error']()

    def _onFinished(self, items) -> None:
        self.hooks['on_finished'](items)

    def closeEvent(self, event: QEvent) -> None:
        if event.spontaneous():
            self.loadingThread.terminate()
            self.hooks['on_close']()
