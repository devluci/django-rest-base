from typing import Dict, List, TypeVar, Set, Hashable

__all__ = ['get_dict_list', 'get_dict_set', 'get_dict_dict']

Key = TypeVar('Key', bound=Hashable)
Value = TypeVar('Value')


def get_dict_list(d: Dict[Key, List[Value]], key: Key) -> List[Value]:
    _list = d.get(key)
    if _list is None:
        _list = d[key] = list()
    return _list


def get_dict_set(d: Dict[Key, Set[Value]], key: Key) -> Set[Value]:
    _set = d.get(key)
    if _set is None:
        _set = d[key] = set()
    return _set


def get_dict_dict(d: Dict[Key, Dict[Value]], key: Key) -> Dict[Value]:
    _dict = d.get(key)
    if _dict is None:
        _dict = d[key] = dict()
    return _dict
