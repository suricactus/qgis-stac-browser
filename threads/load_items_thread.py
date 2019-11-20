from typing import (List, Dict)

import socket
from PyQt5.QtCore import (QThread, pyqtSignal)
from urllib.error import URLError
from ..models.api import API
from ..models.item import Item


class LoadItemsThread(QThread):
    progress = pyqtSignal(API, list, int)
    error = pyqtSignal(Exception)
    finish = pyqtSignal(list)

    def __init__(self, apiCollections: List[API], extent, startTime, endTime, query: Dict) -> None:
        QThread.__init__(self)
        self._currentPage = 0

        self.apiCollections = apiCollections
        self.extent = extent
        self.startTime = startTime
        self.endTime = endTime
        self.query = query
        self._currentCollections = []

    def run(self) -> None:
        try:
            allItems: List[Item] = []

            for apiCollection in self.apiCollections:
                api = apiCollection['api']
                collections = apiCollection['collections']

                self._currentPage = 0
                self._currentCollections = collections

                items = api.searchItems(collections,
                                         self.extent,
                                         self.startTime,
                                         self.endTime,
                                         self.query,
                                         onNextPage=self._onNextPage)
                allItems.extend(items)
            self.finish.emit(allItems)
        except URLError as err:
            self.error.emit(err)
        except socket.timeout as err:
            self.error.emit(err)

    def _onNextPage(self, api: None) -> None:
        self._currentPage += 1
        self.progress.emit(
            api,
            self._currentCollections,
            self._currentPage
        )
