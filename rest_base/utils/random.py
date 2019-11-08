try:
    import numpy as np
except ImportError as e:
    raise ImportError(
        'numpy must be installed to use rest_base.utils.random. Try `pip install django-rest-base[random]`.'
    ) from e

from typing import Union

__all__ = ['seedrandom_int', 'seedrandom']

np.warnings.filterwarnings('ignore')


def _rshift(t: np.int32, n: int) -> np.int32:
    return np.int32((t % 0x100000000) >> n)


# Mulberry32
def seedrandom_int(seed: int) -> int:
    t = np.int32((seed + 0x6D2B79F5) % 2147483647)
    with np.errstate(over='ignore'):
        t = (t ^ _rshift(t, 15)) * (t | 1)
        t ^= t + (t ^ _rshift(t, 7)) * (t | 61)
    return int((t ^ _rshift(t, 14)) % 0x100000000)


def _seedrandom_str(seed: str) -> float:
    t = seedrandom_int(ord(seed[0]))
    for c in seed[1:]:
        t = seedrandom_int(t ^ seedrandom_int(ord(c)))
    return int(t) / 4294967296


def seedrandom(seed: Union[int, str]) -> float:
    if isinstance(seed, str):
        return _seedrandom_str(seed)
    return seedrandom_int(seed) / 4294967296
