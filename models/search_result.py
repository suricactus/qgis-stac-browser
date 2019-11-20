from typing import (Optional, List, Dict, Any)

from .item import Item
from .link import Link


class SearchResult:
    def __init__(self, api: Any, json: Dict[str, Any]) -> None:
        self._api = api
        self._json = json

    @property
    def api(self) -> Any:
        return self._api

    @property
    def type(self) -> Optional[str]:
        return self._json.get('type', None)

    @property
    def meta(self) -> Optional[Dict[str, Any]]:
        return self._json.get('meta', None)

    @property
    def next(self) -> Optional[str]:
        if self._json.get('search:metadata', None) is None:
            return None

        return self._json.get('search:metadata', {}).get('next', None)

    @property
    def items(self) -> List[Item]:
        return [Item(self.api, f) for f in self._json.get('features', [])]

    @property
    def links(self) -> List[Link]:
        return [Link(l) for l in self._json.get('links', [])]
