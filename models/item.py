from typing import (List, Dict, Any, Callable, Optional) 

import os
import subprocess
import hashlib
import tempfile
from ..utils import network
from ..utils.types import (Properties, BBox)
from ..models.link import Link
from ..models.collection import Collection


class Item:
    def __init__(self, api: Any = None, json: Dict[str, Any] = {}) -> None:
        self._api = api
        self._json = json

    @property
    def hashedId(self) -> str:
        return hashlib.sha256(
            f'{self.api.href}/collections/{self.collection.id}/items/{self.id}'
            .encode('utf-8')
        ).hexdigest()

    @property
    def api(self) -> Any:
        return self._api

    @property
    def id(self) -> str:
        return self._json.get('id', None)

    @property
    def type(self) -> str:
        return self._json.get('type', None)

    @property
    def geometry(self) -> str:
        return self._json.get('geometry', None)

    @property
    def bbox(self) -> BBox:
        return self._json.get('bbox', None)

    @property
    def properties(self) -> Properties:
        return self._json.get('properties', {})

    @property
    def links(self) -> List[Link]:
        return [Link(l) for l in self._json.get('links', [])]

    @property
    def assets(self) -> List['Asset']:
        assets = []
        for key, d in self._json.get('assets', {}).items():
            assets.append(Asset(key, d, item=self))

        return assets

    @property
    def collection(self) -> Collection:
        collection_id = self.properties.get('collection', None)
        if collection_id is None:
            collection_id = self._json.get('collection', None)

        for collection in self.api.collections:
            if collection.id == collection_id:
                return collection

        return None

    @property
    def thumbnail(self) -> Optional['Asset']:
        for asset in self.assets:
            if asset.key == 'thumbnail':
                return asset
        return None

    @property
    def thumbnailUrl(self) -> Optional[str]:
        if self.thumbnail is None:
            return None

        return self.thumbnail.href

    @property
    def tempDir(self) -> str:
        tempDir = os.path.join(
            tempfile.gettempdir(),
            'qgis-stac-browser',
            self.hashedId
        )
        if not os.path.exists(tempDir):
            os.makedirs(tempDir)

        return tempDir

    @property
    def thumbnailPath(self) -> Optional[str]:
        if not self.collection:
            return None

        return os.path.join(self.tempDir, 'thumbnail.jpg')

    def thumbnailDownloaded(self) -> bool:
        return self.thumbnail is not None

    def downloadSteps(self, options) -> int:
        steps = 0

        for assetKey in options.get('assets', []):
            for asset in self.assets:
                if asset.key != assetKey:
                    continue

                if options.get('stream_cogs', False) and asset.cog is not None:
                    continue

                steps += 1

        if options.get('add_to_layers', False):
            steps += 1

        return steps

    def download(self, gdalPath: str, options: Properties, downloadDir: str, onUpdate: Callable = None) -> None:
        itemDownloadDir = os.path.join(downloadDir, self.id)

        if not os.path.exists(itemDownloadDir):
            os.makedirs(itemDownloadDir)

        raster_filenames = []

        for asset_key in options.get('assets', []):
            for asset in self.assets:
                if asset.key != asset_key:
                    continue

                if options.get('stream_cogs', False) and asset.cog is not None:
                    raster_filenames.append(asset.cog)
                    continue

                if onUpdate is not None:
                    onUpdate(f'Downloading {asset.href}')

                temp_filename = os.path.join(
                    itemDownloadDir,
                    asset.href.split('/')[-1]
                )
                if asset.isRaster:
                    raster_filenames.append(temp_filename)
                network.download(asset.href, temp_filename)

        if options.get('add_to_layers', False):
            if onUpdate is not None:
                onUpdate(f'Building Virtual Raster...')

            arguments = [
                os.path.join(gdalPath, 'gdalbuildvrt'),
                '-separate',
                os.path.join(downloadDir, f'{self.id}.vrt')
            ]
            arguments.extend(raster_filenames)
            subprocess.run(arguments)

    def __lt__(self, other):
        return self.id < other.id


class Asset:
    def __init__(self, key: str, json: Dict[str, Any], item: Item) -> None:
        self._key = key
        self._json = json
        self._item = item

    @property
    def isRaster(self) -> bool:
        return (self._json.get('eo:name', None) is not None)

    @property
    def key(self) -> str:
        return self._key

    @property
    def cog(self) -> Optional[str]:
        if self.type in ['image/x.geotiff', 'image/vnd.stac.geotiff']:
            return f'/vsicurl/{self.href}'

        return None

    @property
    def href(self) -> str:
        return self._json.get('href', '')

    @property
    def title(self) -> str:
        return self._json.get('title', '')

    @property
    def prettyTitle(self) -> str:
        if self.title is not None:
            return self.title

        return self.key

    @property
    def type(self) -> Optional[str]:
        return self._json.get('type', None)

    @property
    def band(self) -> int:
        if self._item.collection is None:
            return -1

        collectionBands = self._item.collection.properties.get('eo:bands', [])

        for i, c in enumerate(collectionBands):
            if c.get('name', None) == self.key:
                return i

        return -1

    def __lt__(self, other: 'Asset') -> bool:
        if self.band != -1 and other.band != -1:
            return self.band < other.band

        if self.band == -1 and other.band != -1:
            return False

        if self.band != -1 and other.band == -1:
            return True

        if self.title is None or other.title is None:
            return self.key.lower() < other.key.lower()

        return self.title.lower() < other.title.lower()
