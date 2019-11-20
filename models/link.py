from typing import Optional


class Link:
    def __init__(self, json={}):
        self._json = json

    @property
    def href(self) -> Optional[str]:
        return self._json.get('href', None)

    @property
    def rel(self) -> Optional[str]:
        return self._json.get('rel', None)

    @property
    def type(self) -> Optional[str]:
        return self._json.get('type', None)

    @property
    def title(self) -> Optional[str]:
        return self._json.get('title', None)
