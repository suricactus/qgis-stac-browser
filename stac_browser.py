from typing import (List, Dict, Any, Tuple, Callable)

import time
import os.path
import sys

from PyQt5.QtGui import QIcon
from PyQt5.QtWidgets import (QWidget, QAction)

from qgis.gui import QgisInterface
from qgis.core import QgsRectangle

from .resources import *
from .controllers.collection_loading_dialog import CollectionLoadingDialog
from .controllers.query_dialog import QueryDialog
from .controllers.item_loading_dialog import ItemLoadingDialog
from .controllers.results_dialog import ResultsDialog
from .controllers.downloading_controller import DownloadController
from .controllers.download_selection_dialog import DownloadSelectionDialog
from .controllers.configure_apis_dialog import ConfigureAPIDialog
from .controllers.about_dialog import AboutDialog
from .utils.config import Config
from .utils.logging import error
from .utils import crs
from .models.api import API
from .models.item import Item


class STACBrowser:
    def __init__(self, iface: QgisInterface) -> None:
        self.iface = iface
        self.plugin_dir = os.path.dirname(__file__)

        self.actions = []
        self.application = None
        self.menu = 'STAC Browser'

        self.currentWindow = 'COLLECTION_LOADING'

        self.windows = {
            'COLLECTION_LOADING': {
                'class': CollectionLoadingDialog,
                'hooks': {
                    'on_finished': self.collectionLoadFinished,
                    'on_close': self.onClose
                },
                'data': None,
                'dialog': None
            },
            'QUERY': {
                'class': QueryDialog,
                'hooks': {
                    'on_close': self.onClose,
                    'on_search': self.onSearch
                },
                'data': None,
                'dialog': None
            },
            'ITEM_LOADING': {
                'class': ItemLoadingDialog,
                'hooks': {
                    'on_close': self.onClose,
                    'on_finished': self.itemLoadFinished,
                    'on_error': self.resultsError
                },
                'data': None,
                'dialog': None
            },
            'RESULTS': {
                'class': ResultsDialog,
                'hooks': {
                    'on_close': self.onClose,
                    'on_back': self.onBack,
                    'on_download': self.onDownload,
                    'select_downloads': self.selectDownloads
                },
                'data': None,
                'dialog': None
            },
        }

    def onSearch(self, apiCollections: List[API], extentRect: QgsRectangle, timePeriod: Tuple[str, str], query: Dict[str, Any]) -> None:
        (startTime, endTime) = timePeriod

        # the API consumes only EPSG:4326
        extentRect = crs.transform(extentRect.crs(), 4326, extentRect)

        extent = [
            extentRect.xMinimum(),
            extentRect.yMinimum(),
            extentRect.xMaximum(),
            extentRect.yMaximum()
        ]

        self.windows['ITEM_LOADING']['data'] = {
            'api_collections': apiCollections,
            'extent': extent,
            'start_time': startTime,
            'end_time': endTime,
            'query': query,
        }
        self.currentWindow = 'ITEM_LOADING'
        self.windows['QUERY']['dialog'].close()
        self._loadWindow()

    def onBack(self) -> None:
        self.windows['RESULTS']['data'] = None
        self.windows['RESULTS']['dialog'].close()
        self.windows['RESULTS']['dialog'] = None

        self.currentWindow = 'QUERY'
        self._loadWindow()

    def onClose(self) -> None:
        if self.windows is None:
            return
        self.resetWindows()

    def onDownload(self, downloadItems: List[Item], downloadDir: str) -> None:
        self._downloadController = DownloadController(
            data={
                'downloads': downloadItems,
                'download_directory': downloadDir,
            },
            hooks={}
        )
        self.resetWindows()

    def downloadingFinished(self) -> None:
        self.windows['DOWNLOADING']['dialog'].close()
        self.currentWindow = 'COLLECTION_LOADING'
        self.resetWindows()

    def collectionLoadFinished(self, apis: List[API]) -> None:
        self.windows['QUERY']['data'] = {'apis': apis}
        self.currentWindow = 'QUERY'
        self.windows['COLLECTION_LOADING']['dialog'].close()
        self._loadWindow()

    def resultsError(self) -> None:
        self.windows['ITEM_LOADING']['dialog'].close()
        self.windows['ITEM_LOADING']['dialog'] = None
        self.windows['ITEM_LOADING']['data'] = None
        self.currentWindow = 'QUERY'
        self._loadWindow()

    def itemLoadFinished(self, items: List[Item]) -> None:
        self.windows['RESULTS']['data'] = {'items': items}
        self.currentWindow = 'RESULTS'
        self.windows['ITEM_LOADING']['dialog'].close()
        self.windows['ITEM_LOADING']['data'] = None
        self.windows['ITEM_LOADING']['dialog'] = None
        self._loadWindow()

    def selectDownloads(self, items: List[Item], downloadDir: str) -> None:
        dialog = DownloadSelectionDialog(
            data={'items': items},
            hooks={'on_close': self.onClose},
            parent=self.windows['RESULTS']['dialog']
        )

        result = dialog.exec_()

        if not result:
            return

        self.onDownload(dialog.downloads, downloadDir)

    def addAction(self, 
                icon_path: str, 
                text: str, 
                callback: Callable, 
                enabledFlag: bool = True,
                addToMenu: bool = True, 
                addToToolbar: bool = True, 
                statusTip: str = None,
                whatsThis: str = None, 
                parent: QWidget = None) -> QAction:
        icon = QIcon(icon_path)
        action = QAction(icon, text, parent)
        action.triggered.connect(callback)
        action.setEnabled(enabledFlag)

        if statusTip is not None:
            action.setStatusTip(statusTip)

        if whatsThis is not None:
            action.setWhatsThis(whatsThis)

        if addToToolbar:
            self.iface.addToolBarIcon(action)

        if addToMenu:
            self.iface.addPluginToWebMenu(self.menu, action)

        self.actions.append(action)

        return action

    def _loadWindow(self) -> None:
        isPythonVersionOk = self.checkPythonVersion()

        if not isPythonVersionOk:
            return

        if self.currentWindow == 'COLLECTION_LOADING':
            config = Config()

            if config.last_update is not None \
                    and time.time() - config.last_update \
                    < config.api_update_interval:
                self.currentWindow = 'QUERY'
                self.windows['QUERY']['data'] = {'apis': config.apis}

        window = self.windows.get(self.currentWindow, None)

        if window is None:
            error(self.iface, f'Window {self.currentWindow} does not exist')
            return

        if window['dialog'] is None:
            window['dialog'] = window.get('class')(
                data=window.get('data'),
                hooks=window.get('hooks'),
                parent=self.iface.mainWindow()
            )
            window['dialog'].show()
        else:
            window['dialog'].raise_()
            window['dialog'].show()
            window['dialog'].activateWindow()

    def resetWindows(self) -> None:
        for key, window in self.windows.items():
            if window['dialog'] is not None:
                window['dialog'].close()

            window['data'] = None
            window['dialog'] = None

        self.currentWindow = 'COLLECTION_LOADING'

    def checkPythonVersion(self) -> bool:
        if sys.version_info < (3, 6):
            v = '.'.join((
                str(sys.version_info.major),
                str(sys.version_info.minor),
                str(sys.version_info.micro)
            ))
            error(
                self.iface,
                ''.join((
                    'This plugin requires Python >= 3.6; ',
                    f'You are running {v}'
                ))
            )
            return False
        return True

    def _configureApis(self) -> None:
        correctVersion = self.checkPythonVersion()

        if not correctVersion:
            return

        dialog = ConfigureAPIDialog(
            data={'apis': Config().apis},
            hooks={},
            parent=self.iface.mainWindow()
        )
        dialog.exec_()

    def _about(self) -> None:
        dialog = AboutDialog(
            os.path.join(self.plugin_dir, 'about.html'),
            parent=self.iface.mainWindow()
        )
        dialog.exec_()

    def initGui(self) -> None:
        self.addAction(
            ':/plugins/stac_browser/assets/icon.png',
            text='Browse STAC Catalogs',
            callback=self._loadWindow,
            parent=self.iface.mainWindow())

        self.addAction(
            ':/plugins/stac_browser/assets/cog.svg',
            text='Configure APIs',
            addToToolbar=False,
            callback=self._configureApis,
            parent=self.iface.mainWindow())

        self.addAction(
            ':/plugins/stac_browser/assets/info.svg',
            text='About',
            addToToolbar=False,
            callback=self._about,
            parent=self.iface.mainWindow())

    def unload(self) -> None:
        for action in self.actions:
            self.iface.removePluginWebMenu('STAC Browser', action)
            self.iface.removeToolBarIcon(action)
