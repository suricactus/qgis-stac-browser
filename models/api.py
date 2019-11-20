from typing import (List, Dict, Callable, Any, Optional)

import re
from urllib.parse import urlparse
from .collection import Collection
from .link import Link
from .search_result import SearchResult
from ..utils import network
from ..utils.types import (DataT, BBox)


class API:
    def __init__(self, json: Dict[str, Any]) -> None:
        self._json = json
        self._data = self._json.get('data', None)
        self._collections = [
            Collection(self, c) for c in self._json.get('collections', [])
        ]

    def load(self) -> None:
        self._data = network.request(f'{self.href}/stac')
        self._collections = [
            self.loadCollection(c) for c in self.collectionIds
        ]

    def loadCollection(self, collectionId: str) -> Collection:
        return Collection(self,
                          network.request(
                              f'{self.href}/collections/{collectionId}'))

    def searchItems(self, collections: List[Collection] = [], bbox: BBox = [], startTime=None,
                    endTime=None, query: Dict['str', Any] = None, page: int = 1, nextPage=None, limit: int = 50,
                    onNextPage: Callable = None, pageLimit: int = 10) -> List[Any]:
        if page > pageLimit:
            return []

        if onNextPage is not None:
            onNextPage(self)

        if endTime is None:
            time = startTime.strftime('%Y-%m-%dT%H:%M:%SZ')
        else:
            start = startTime.strftime('%Y-%m-%dT%H:%M:%SZ')
            end = endTime.strftime('%Y-%m-%dT%H:%M:%SZ')
            time = f'{start}/{end}'

        body = {
            'collections': [c.id for c in collections],
            'bbox': bbox,
            'time': time,
            'limit': limit,
        }

        if query is not None:
            body['query'] = query

        if nextPage is not None:
            body['next'] = nextPage
        else:
            body['page'] = page

        searchResult = SearchResult(self,
                                    network.request(
                                         f'{self.href}/stac/search',
                                         data=body))

        items = searchResult.items

        if len(items) >= limit:
            items.extend(self.searchItems(collections, bbox, startTime,
                         endTime, query, page + 1, searchResult.next, limit,
                         onNextPage=onNextPage))

        return items

    def collectionIdFromHref(self, href: str) -> Optional[str]:
        p = re.compile(r'\/collections\/(.*)')
        m = p.match(urlparse(href).path)
        if m is None:
            return None

        if m.groups() is None:
            return None

        return m.groups()[0]

    @property
    def json(self) -> Dict[str, Any]:
        return {
            'id': self.id,
            'href': self.href,
            'data': self.data,
            'collections': [c.json for c in self.collections],
        }

    @property
    def id(self) -> str:
        return self._json.get('id')

    @property
    def title(self) -> str:
        return self.data.get('title', self.href)

    @property
    def href(self) -> str:
        return self._json.get('href')

    @property
    def version(self) -> Optional[str]:
        return self.data.get('stac_version', None)

    @property
    def description(self) -> Optional[str]:
        return self.data.get('description', None)

    @property
    def data(self) -> DataT:
        if self._data is None:
            return {}
        return self._data

    @property
    def links(self) -> List[Link]:
        return [Link(l) for l in self.data.get('links', [])]

    @property
    def collectionIds(self) -> List[str]:
        collectionIds = []
        p = re.compile(r'\/collections\/(.*)')

        for link in self.links:
            m = p.match(urlparse(link.href).path)
            if m is None:
                continue

            if m.groups() is None:
                continue

            collectionIds.append(m.groups()[0])

        return collectionIds

    @property
    def collections(self) -> List[Collection]:
        return self._collections

    def __lt__(self, other: 'API') -> bool:
        return self.title.lower() < other.title.lower()
