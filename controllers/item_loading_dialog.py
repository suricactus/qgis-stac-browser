from PyQt5 import uic, QtWidgets
import urllib

from ..utils import ui
from ..utils.logging import error
from ..threads.load_items_thread import LoadItemsThread


FORM_CLASS, _ = uic.loadUiType(ui.path('item_loading_dialog.ui'))


class ItemLoadingDialog(QtWidgets.QDialog, FORM_CLASS):
    def __init__(self, data={}, hooks={}, parent=None, iface=None):
        super(ItemLoadingDialog, self).__init__(parent)

        self.data = data
        self.hooks = hooks
        self.iface = iface

        self.setupUi(self)
        self.setFixedSize(self.size())

        self.loading_thread = LoadItemsThread(self.data['api_collections'],
                                              self.data['extent'],
                                              self.data['start_time'],
                                              self.data['end_time'],
                                              self.data['query'],
                                              on_progress=self.on_progress,
                                              on_error=self.on_error,
                                              on_finished=self.on_finished)

        self.loading_thread.start()

    def on_progress(self, api, collections, current_page):
        collection_label = ', '.join([c.title for c in collections])
        self.loadingLabel.setText('\n'.join((
            f'Searching {api.title}',
            f'Collections: [{collection_label}]',
            f'Page {current_page}...'
        )))

    def on_error(self, e):
        if type(e) == urllib.error.URLError:
            error(self.iface, f'Network Error: {e.reason}')
        elif type(e) == urllib.error.HTTPError:
            error(self.iface, f'Network Error: [{e.code}] {e.reason}')
        else:
            error(self.iface, f'Network Error: {type(e).__name__}')
        self.hooks['on_error']()

    def on_finished(self, items):
        self.hooks['on_finished'](items)

    def closeEvent(self, event):
        if event.spontaneous():
            self.loading_thread.terminate()
            self.hooks['on_close']()
