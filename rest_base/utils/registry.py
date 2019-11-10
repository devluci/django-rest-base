from __future__ import annotations

import importlib
import re
from typing import Union, Any

__all__ = ['ModuleRegistry']


MODULE_NAME_REGEX = re.compile(r'^(?:[0-9a-zA-Z_]+\.)+[0-9a-zA-Z_]+$')


def _try_import(val: str):
    if MODULE_NAME_REGEX.match(val) is None:
        return val

    path, name = val.rsplit('.', 1)
    try:
        module = importlib.import_module(path)
    except ImportError:
        return val
    return getattr(module, name, val)


class EMPTY:
    pass


class INVALID:
    pass


class ModuleRegistry:
    def __init__(self, name: str, default: Any = EMPTY, include_module: bool = False):
        super().__setattr__('name', name)
        super().__setattr__('_registry', dict())
        super().__setattr__('_default', default)
        super().__setattr__('_include_module', include_module)

    def __getattr__(self, name, default=INVALID):
        value = self._registry.get(name, default)
        if value is INVALID:
            if self._default is EMPTY:
                raise AttributeError(f'{self.name} has no attribute {name}')
            else:
                return None
        return value

    def __setattr__(self, name, value):
        self._set(name, value)

    def __delattr__(self, name):
        try:
            del self._registry[name]
        except KeyError:
            if not self._ignore:
                raise AttributeError(f'{self.name} has no attribute {name}')

    def __getitem__(self, key):
        try:
            return self._registry[key]
        except KeyError:
            if self._ignore:
                return None
            raise

    def __setitem__(self, key, value):
        self._set(key, value)

    def __delitem__(self, key):
        try:
            del self._registry[key]
        except KeyError:
            if self._ignore:
                return None
            raise

    def _set(self, key, value):
        if callable(value):
            value.__name__ = key
            value.__qualname__ = f'{self.name}.{key}'
        elif isinstance(value, str):
            value = _try_import(value)

        self._registry[key] = value

    def dict(self) -> dict:
        return self._registry

    def update(self, other: Union[dict, ModuleRegistry]):
        if isinstance(other, dict):
            self._registry.update(other)
        elif isinstance(other, ModuleRegistry):
            self._registry.update(other._registry)
        else:
            raise TypeError('Only dictionaries and ModuleRegistry are allowed')
