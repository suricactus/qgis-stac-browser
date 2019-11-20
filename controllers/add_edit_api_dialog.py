from typing import Any

import uuid
from urllib.error import URLError

from PyQt5 import uic
from PyQt5.QtWidgets import (QDialog, QWidget)

from qgis.utils import iface

from stac_browser.utils import ui
from stac_browser.utils.logging import error
from stac_browser.utils.types import (DataT, HooksT)
from stac_browser.threads.load_api_data_thread import LoadAPIDataThread
from stac_browser.models.api import API

FORM_CLASS: Any
FORM_CLASS, _ = uic.loadUiType(ui.path('add_edit_api_dialog.ui'))


class AddEditAPIDialog(QDialog, FORM_CLASS):
    def __init__(self, data: DataT = {}, hooks: HooksT = {}, parent: QWidget = None) -> None:
        super(AddEditAPIDialog, self).__init__(parent)

        self.data = data
        self.hooks = hooks

        self.setupUi(self)

        self._populateDetails()
        self._populateAuthMethodCombo()

        self.cancelButton.clicked.connect(self._onCancelClicked)
        self.removeButton.clicked.connect(self._onRemoveClicked)
        self.saveAddButton.clicked.connect(self._onSaveAddClicked)

    def _onCancelClicked(self) -> None:
        self.reject()

    def _onRemoveClicked(self) -> None:
        self.hooks['remove_api'](self.api)
        self.accept()

    def _setAllEnabled(self, is_enabled: bool) -> None:
        self.urlEditBox.setEnabled(is_enabled)
        self.authenticationCombo.setEnabled(is_enabled)
        self.removeButton.setEnabled(is_enabled)
        self.cancelButton.setEnabled(is_enabled)
        self.saveAddButton.setEnabled(is_enabled)

    def _onSaveAddClicked(self) -> None:
        self._setAllEnabled(False)
        self.saveAddButton.setText('Testing Connection...')

        api_id = str(uuid.uuid4())

        if self.api is not None:
            api_id = self.api.id

        api = API({'id': api_id, 'href': self.urlEditBox.text()})

        self.loading_thread = LoadAPIDataThread(api)
        self.loading_thread.error.connect(self._onApiError)
        self.loading_thread.success.connect(self._onApiSuccess)
        self.loading_thread.start()

    def _onApiError(self, err: Exception) -> None:
        self._setAllEnabled(True)
        if self.api is None:
            self.saveAddButton.setText('Add')
        else:
            self.saveAddButton.setText('Save')

        if type(err) == URLError:
            error(iface, f'Connection Failed; {err.reason}')
        else:
            error(iface, f'Connection Failed; {type(err).__name__}')

    def _onApiSuccess(self, api: API) -> None:
        if self.api is None:
            self.hooks['add_api'](api)
        else:
            self.hooks['edit_api'](api)
        self.accept()

    @property
    def api(self) -> API:
        return self.data.get('api', None)

    def _populateDetails(self) -> None:
        if self.api is None:
            self.saveAddButton.setText('Add')
            self.removeButton.hide()
            return

        self.urlEditBox.setText(self.api.href)

    def _populateAuthMethodCombo(self) -> None:
        self.authenticationCombo.addItem('No Auth')
