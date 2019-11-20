from typing import (Any, List)

from PyQt5 import uic
from PyQt5.QtWidgets import (QDialog, QWidget, QListWidgetItem)

from stac_browser.utils import ui
from stac_browser.utils.config import Config
from stac_browser.utils.types import (DataT, HooksT)
from stac_browser.controllers.add_edit_api_dialog import AddEditAPIDialog
from stac_browser.models.api import API

FORM_CLASS: Any
FORM_CLASS, _ = uic.loadUiType(ui.path('configure_apis_dialog.ui'))


class ConfigureAPIDialog(QDialog, FORM_CLASS):
    def __init__(self, data: DataT = {}, hooks: HooksT = {}, parent: QWidget = None) -> None:
        super(ConfigureAPIDialog, self).__init__(parent)

        self.data = data
        self.hooks = hooks

        self.setupUi(self)

        self._populateApiList()
        self._populateApiDetails()

        self.list.activated.connect(self._onListClicked)
        self.apiAddButton.clicked.connect(self._onAddApiClicked)
        self.apiEditButton.clicked.connect(self._onEditApiClicked)
        self.closeButton.clicked.connect(self._onCloseClicked)

    def _onCloseClicked(self) -> None:
        self.reject()

    def _onAddApiClicked(self) -> None:
        dialog = AddEditAPIDialog(
            data={'api': None},
            hooks={
                "remove_api": self.removeApi,
                "add_api": self.addApi,
                "edit_api": self.editApi
            },
            parent=self
        )

        dialog.exec_()

    def _onEditApiClicked(self) -> None:
        dialog = AddEditAPIDialog(
            data={'api': self.selectedApi},
            hooks={
                "remove_api": self.removeApi,
                "add_api": self.addApi,
                "edit_api": self.editApi
            },
            parent=self
        )

        dialog.exec_()

    def editApi(self, api: API) -> None:
        config = Config()
        newApis = []

        for a in config.apis:
            if a.id == api.id:
                continue

            newApis.append(a)

        newApis.append(api)
        config.apis = newApis
        config.save()

        self.data['apis'] = config.apis
        self._populateApiList()
        self._populateApiDetails()

    def addApi(self, api: API) -> None:
        config = Config()
        apis = config.apis
        apis.append(api)
        config.apis = apis
        config.save()

        self.data['apis'] = config.apis
        self._populateApiList()
        self._populateApiDetails()

    def removeApi(self, api: API) -> None:
        config = Config()
        newApis = []

        for a in config.apis:
            if a.id == api.id:
                continue

            newApis.append(a)

        config.apis = newApis
        config.save()

        self.data['apis'] = config.apis
        self._populateApiList()
        self._populateApiDetails()

    def _populateApiList(self) -> None:
        self.list.clear()

        for api in self.apis:
            apiNode = QListWidgetItem(self.list)
            apiNode.setText(f'{api.title}')

    def _populateApiDetails(self) -> None:
        if self.selectedApi is None:
            self.apiUrlLabel.hide()
            self.apiUrlValue.hide()
            self.apiTitleLabel.hide()
            self.apiTitleValue.hide()
            self.apiVersionLabel.hide()
            self.apiVersionValue.hide()
            self.apiDescriptionLabel.hide()
            self.apiDescriptionValue.hide()
            self.apiEditButton.hide()
            return

        self.apiUrlValue.setText(self.selectedApi.href)
        self.apiTitleValue.setText(self.selectedApi.title)
        self.apiVersionValue.setText(self.selectedApi.version)
        self.apiDescriptionValue.setText(self.selectedApi.description)

        self.apiUrlLabel.show()
        self.apiUrlValue.show()
        self.apiTitleLabel.show()
        self.apiTitleValue.show()
        self.apiVersionLabel.show()
        self.apiVersionValue.show()
        self.apiDescriptionLabel.show()
        self.apiDescriptionValue.show()
        self.apiEditButton.show()

    @property
    def apis(self) -> List[API]:
        return self.data.get('apis', [])

    @property
    def selectedApi(self) -> API:
        items = self.list.selectedIndexes()
        for i in items:
            return self.apis[i.row()]
        return None

    def _onListClicked(self) -> None:
        self._populateApiDetails()
