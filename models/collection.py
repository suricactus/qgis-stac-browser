from typing import (List, Dict, Any, Optional)

from .link import Link


class Collection:
    def __init__(self, api: Any, json: Dict[str, Any]) -> None:
        self._api = api
        self._json = json

    @property
    def json(self) -> Dict[str, Any]:
        return self._json

    @property
    def stacVersion(self) -> Optional[str]:
        return self._json.get('stac_version', None)

    @property
    def id(self) -> Optional[str]:
        return self._json.get('id', None)

    @property
    def title(self) -> Optional[str]:
        return self._json.get('title', None)

    @property
    def description(self) -> Optional[str]:
        return self._json.get('description', None)

    @property
    def keywords(self) -> List[str]:
        return self._json.get('keywords', [])

    @property
    def version(self) -> Optional[str]:
        return self._json.get('version', None)

    @property
    def license(self) -> Optional[str]:
        return self._json.get('license', None)

    @property
    def providers(self) -> List['Provider']:
        return [Provider(p) for p in self._json.get('providers', [])]

    @property
    def extent(self) -> 'Extent':
        return Extent(self._json.get('extent', {}))

    @property
    def properties(self) -> Dict[str, Any]:
        return self._json.get('properties', {})

    @property
    def links(self) -> List[Link]:
        return [Link(l) for l in self._json.get('links', [])]

    @property
    def bands(self) -> Dict[str, int]:
        bands = {}
        for i, band in enumerate(self.properties.get('eo:bands', [])):
            band['band'] = i + 1
            bands[band.get('name', None)] = band

        return bands

    @property
    def api(self) -> Any:
        return self._api

    def __lt__(self, other: 'Collection') -> bool:
        return self.title.lower() < other.title.lower()


class Extent:
    def __init__(self, json: Dict[str, Any]) -> None:
        self._json = json

    @property
    def spatial(self) -> List[str]:
        return self._json.get('spatial', [])

    @property
    def temporal(self) -> Optional[str]:
        return self._json.get('temporal', None)


class Provider:
    def __init__(self, json={}) -> None:
        self._json = json

    @property
    def name(self) -> Optional[str]:
        return self._json.get('name', None)

    @property
    def description(self) -> Optional[str]:
        return self._json.get('description', None)

    @property
    def roles(self) -> List[str]:
        return self._json.get('roles', [])

    @property
    def url(self) -> Optional[str]:
        return self._json.get('url', None)
