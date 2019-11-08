import os

__all__ = ['load']


def load(filename: str):
    with open(filename, 'r', encoding='utf8') as f:
        for line in f:
            if '=' not in line:
                continue

            try:
                line = line[:line.index('#')]
            except ValueError:
                pass
            line = line.strip()
            key, value = line.split('=', 1)
            if '{' in value:
                try:
                    value = value.format(**os.environ)
                except KeyError:
                    pass
            os.environ[key] = value
