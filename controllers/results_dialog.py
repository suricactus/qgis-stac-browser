from typing import (Any, List, Optional)

import os

from PyQt5 import uic, QtCore
from PyQt5.QtWidgets import (QFileDialog, QWidget, QDialog, QTableWidgetItem)
from PyQt5.QtCore import (QUrl, Qt, QEvent)
from PyQt5.QtGui import (QDesktopServices, QColor, QStandardItemModel, QStandardItem, QImage, QPixmap)

from qgis.gui import QgsRubberBand
from qgis.core import (QgsWkbTypes, QgsPointXY, QgsGeometry, QgsReferencedRectangle)
from qgis.utils import iface

from stac_browser.utils import ui
from stac_browser.utils import crs
from stac_browser.utils.config import Config
from stac_browser.utils.types import (DataT, HooksT)
from stac_browser.threads.load_preview_thread import LoadPreviewThread
from stac_browser.models.item import Item

FORM_CLASS: Any
FORM_CLASS, _ = uic.loadUiType(ui.path('results_dialog.ui'))


class ResultsDialog(QDialog, FORM_CLASS):
    def __init__(self, data: DataT, hooks: HooksT, parent: QWidget = None) -> None:
        super(ResultsDialog, self).__init__(parent)

        self.data = data
        self.hooks = hooks
        self.canvas = iface.mapCanvas()

        self.setupUi(self)

        self._itemListModel: QStandardItemModel
        self._selected_item = None
        self._config = Config()
        self._rubberband = self._createRubberband()

        self._populateItemList()
        self._populateDownloadDirectory()

        self.list.activated.connect(self.on_list_clicked)
        self.selectButton.clicked.connect(self._onSelectAllClicked)
        self.deselectButton.clicked.connect(self._onDeselectAllClicked)
        self.downloadButton.clicked.connect(self._onDownloadClicked)
        self.downloadPathButton.clicked.connect(self._onDownloadPathClicked)
        self.backButton.clicked.connect(self._onBackClicked)
        self.previewExternalButton.clicked.connect(self._onPreviewExternalClicked)

    def _populateItemList(self) -> None:
        self._itemListModel = QStandardItemModel(self.list)

        for item in self.items:
            i = QStandardItem(item.id)
            i.setCheckable(True)
            self._itemListModel.appendRow(i)

        self.list.setModel(self._itemListModel)

    def _populateDownloadDirectory(self) -> None:
        self.downloadDirectory.setText(self._config.download_directory)

    def _populateItemDetails(self, item: Item) -> None:
        propertyKeys = sorted(list(item.properties.keys()))

        self.propertiesTable.setColumnCount(2)
        self.propertiesTable.setRowCount(len(propertyKeys))

        for i, key in enumerate(propertyKeys):
            self.propertiesTable.setItem(i, 0, QTableWidgetItem(key))
            self.propertiesTable.setItem(
                i,
                1,
                QTableWidgetItem(str(item.properties[key]))
            )
        self.propertiesTable.resizeColumnsToContents()

    @property
    def items(self) -> List[Item]:
        return sorted(self.data.get('items', []))

    @property
    def _downloadDir(self) -> str:
        return self.downloadDirectory.text()

    def _getSelectedItems(self) -> List[Item]:
        selectedItems = []

        for i in range(self._itemListModel.rowCount()):
            if self._itemListModel.item(i).checkState() == Qt.Checked:
                selectedItems.append(self.items[i])

        return selectedItems

    def _onDownloadClicked(self) -> None:
        self._resetFootprint()

        self.hooks['select_downloads'](self._getSelectedItems(), self._downloadDir)

    def _onDownloadPathClicked(self) -> None:
        self._resetFootprint()

        directory = QFileDialog.getExistingDirectory(
            self,
            'Select Download Directory',
            '',
            QFileDialog.ShowDirsOnly | QFileDialog.DontResolveSymlinks
        )
        if directory:
            self._config.download_directory = directory
            self._config.save()
            self._populateDownloadDirectory()

    def _onSelectAllClicked(self) -> None:
        self._resetFootprint()

        for i in range(self._itemListModel.rowCount()):
            item = self._itemListModel.item(i)
            item.setCheckState(Qt.Checked)

        self._updateDownloadEnabled()

    def _onDeselectAllClicked(self) -> None:
        self._resetFootprint()

        for i in range(self._itemListModel.rowCount()):
            item = self._itemListModel.item(i)
            item.setCheckState(Qt.Unchecked)

        self._updateDownloadEnabled()

    # this must remain snake_case for some reason... 
    @QtCore.pyqtSlot(QtCore.QModelIndex)
    def on_list_clicked(self, index: int) -> None:
        self._resetFootprint()

        print('asd', index)

        items = self.list.selectedIndexes()

        for i in items:
            item = self.items[i.row()]
            self._selectItem(item)

        self._updateDownloadEnabled()

    def _selectItem(self, item: Item) -> None:
        self._selected_item = item
        self._setPreview(item, None)
        self._populateItemDetails(item)
        self._drawFootprint(item)

    def _onImageLoaded(self, item: Item, err: Exception) -> None:
        if self._selected_item != item:
            return

        self._setPreview(item, err)

    def _setPreview(self, item: Item, err: Optional[Exception]) -> None:
        if item.thumbnailUrl is None:
            self.imageView.setText('No Preview Available')
            return

        if err:
            self.imageView.setText('Error Loading Preview')
            return

        if item.thumbnailPath is not None:
            if not os.path.exists(item.thumbnailPath):
                self.imageView.setText('Loading Preview...')
                self.loadingThread = LoadPreviewThread(item)
                self.loadingThread.finished.connect(self._onImageLoaded)
                self.loadingThread.start()
                return

            imageProfile = QImage(item.thumbnailPath)
            imageProfile = imageProfile.scaled(
                self.imageView.size().width(),
                self.imageView.size().height(),
                aspectRatioMode=Qt.KeepAspectRatio,
                transformMode=Qt.SmoothTransformation
            )
            self.imageView.setPixmap(QPixmap.fromImage(imageProfile))

        self.previewExternalButton.setEnabled(True)

    def resizeEvent(self, event: QEvent) -> None:
        if self._selected_item is None:
            return

        self._setPreview(self._selected_item, None)

    def closeEvent(self, event: QEvent) -> None:
        self._resetFootprint()

        if event.spontaneous():
            self.hooks['on_close']()

    def _onBackClicked(self) -> None:
        self._resetFootprint()

        self.hooks['on_back']()

    def _onPreviewExternalClicked(self) -> None:
        assert self._selected_item
        assert self._selected_item.thumbnailPath

        QDesktopServices.openUrl(QUrl.fromLocalFile(self._selected_item.thumbnailPath))

    def _resetFootprint(self) -> None:
        self._rubberband.reset(QgsWkbTypes.PolygonGeometry)

    def _drawFootprint(self, item: Item) -> None:
        self._rubberband.reset(QgsWkbTypes.PolygonGeometry)

        if not item.geometry:
            return

        geom = None

        if item.geometry['type'] == 'Polygon':
            parts = [[QgsPointXY(x, y) for [x, y] in part]
                     for part in item.geometry['coordinates']]
            geom = QgsGeometry.fromPolygonXY(parts)
        elif item.geometry['type'] == 'MultiPolygon':
            parts = [[[QgsPointXY(x, y) for [x, y] in part] for part in multi]
                     for multi in item.geometry['coordinates']]
            geom = QgsGeometry.fromMultiPolygonXY(parts)
        else:
            # unsupported geometry type
            return

        self._rubberband.setToGeometry(geom, crs.crs4326)
        self._rubberband.show()

        bbox = crs.transform(crs.crs4326, crs.getProjectCrs(), geom.boundingBox())

        # TODO one day setExtent will support QgsReferencedRectangle :)
        self.canvas.setExtent(QgsReferencedRectangle(bbox, crs.getProjectCrs()))
        self.canvas.refresh()

    def _createRubberband(self) -> QgsRubberBand:
        rubberband = QgsRubberBand(self.canvas, True)
        rubberband.setColor(QColor(254, 178, 76, 63))
        rubberband.setWidth(1)

        return rubberband

    def _updateDownloadEnabled(self) -> None:
        enabled = bool(len(self._getSelectedItems()) > 0)

        self.downloadButton.setEnabled(enabled)
