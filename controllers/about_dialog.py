from typing import Any
from PyQt5 import uic
from PyQt5.QtWidgets import (QDialog, QWidget)

from stac_browser.utils import ui


FORM_CLASS: Any
FORM_CLASS, _ = uic.loadUiType(ui.path('about_dialog.ui'))


class AboutDialog(QDialog, FORM_CLASS):
    def __init__(self, path: str, parent: QWidget = None) -> None:
        assert isinstance(path, str), 'provided path must be a string'

        super(AboutDialog, self).__init__(parent)

        self.setupUi(self)

        with open(path, 'r') as f:
            contents = f.read()

        self.textBrowser.setHtml(contents)

        self.closeButton.clicked.connect(self._onCloseClicked)

    def _onCloseClicked(self) -> None:
        self.reject()
