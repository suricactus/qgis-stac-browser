from typing import (List, Dict, Any)

from PyQt5 import uic
from PyQt5 import QtWidgets
from PyQt5 import QtCore
from PyQt5.QtCore import QEvent
from PyQt5.QtWidgets import (QDialog, QWidget)

from stac_browser.utils import ui
from stac_browser.utils.types import (DataT, HooksT)
from stac_browser.models.item import (Item, Asset)


FORM_CLASS: Any
FORM_CLASS, _ = uic.loadUiType(ui.path('download_selection_dialog.ui'))


DownloadData = Dict[str, Any]


class DownloadSelectionDialog(QDialog, FORM_CLASS):
    def __init__(self, data: DataT = {}, hooks: HooksT = {}, parent: QWidget = None) -> None:
        super(DownloadSelectionDialog, self).__init__(parent)

        self.data = data
        self.hooks = hooks
        self._currentItemIdx = 0

        self.setupUi(self)

        self.downloads: List[DownloadData] = []

        self._populateCurrentItem()

        self.nextButton.clicked.connect(self._onNextClicked)
        self.cancelButton.clicked.connect(self._onCancelClicked)

    def _populateCurrentItem(self) -> None:
        if self._currentItemIdx + 1 == len(self.items):
            self.nextButton.setText('Download')
        else:
            self.nextButton.setText('Next')

        collectionLabel = 'N/A'

        if self.currentItem.collection is not None:
            collectionLabel = self.currentItem.collection.id

        self.itemLabel.setText(self.currentItem.id)
        self.collectionLabel.setText(collectionLabel)
        self.assetListWidget.clear()

        for asset in sorted(self.currentItem.assets):
            assetNode = QtWidgets.QListWidgetItem(self.assetListWidget)
            assetNode.setText(f'{asset.prettyTitle}')
            assetNode.setFlags(
                assetNode.flags() | QtCore.Qt.ItemIsUserCheckable  # type: ignore
            )
            assetNode.setCheckState(QtCore.Qt.Unchecked)

    def _addCurrentItemToDownloads(self) -> None:
        applyToAll = (
            self.applyAllCheckbox.checkState() == QtCore.Qt.Checked
        )
        addToLayers = (
            self.addLayersCheckbox.checkState() == QtCore.Qt.Checked
        )
        streamCogs = (self.streamCheckbox.checkState() == QtCore.Qt.Checked)

        downloadData: DownloadData = {
            'item': self.currentItem,
            'options': {
                'add_to_layers': addToLayers,
                'stream_cogs': streamCogs,
                'assets': [a.key for a in self.selectedAssets],
            },
        }

        self.downloads.append(downloadData)

        if not applyToAll or self.currentItem.collection is None:
            return

        for i in range(self._currentItemIdx, len(self.items)):
            if self._itemInDownloads(self.items[i]):
                continue

            if self.items[i].collection is None:
                continue

            if self.items[i].collection == self.currentItem.collection:
                newDownloadData: DownloadData = {
                    'item': self.items[i],
                    'options': {
                        'add_to_layers': addToLayers,
                        'stream_cogs': streamCogs,
                        'assets': [a.key for a in self.selectedAssets],
                    },
                }
                self.downloads.append(newDownloadData)

    def _itemInDownloads(self, item: Item) -> bool:
        for d in self.downloads:
            if d['item'] == item:
                return True

        return False

    @property
    def selectedAssets(self) -> List[Asset]:
        sortedAssets = sorted(self.currentItem.assets)
        assets = []

        for i in range(self.assetListWidget.count()):
            asset_node = self.assetListWidget.item(i)
            if asset_node.checkState() != QtCore.Qt.Checked:
                continue
            assets.append(sortedAssets[i])

        return assets

    @property
    def currentItem(self) -> Item:
        if self._currentItemIdx >= len(self.items):
            return None

        return self.items[self._currentItemIdx]

    @property
    def items(self) -> List[Item]:
        return sorted(self.data.get('items', []))

    def _onNextClicked(self) -> None:
        self._addCurrentItemToDownloads()

        self._currentItemIdx += 1
        while self.currentItem is not None:
            if not self._itemInDownloads(self.currentItem):
                break
            self._currentItemIdx += 1

        if self.currentItem is None:
            self.accept()
            return

        self._populateCurrentItem()

    def _onCancelClicked(self) -> None:
        self.reject()

    def closeEvent(self, event: QEvent) -> None:
        if event.spontaneous():
            self.reject()
