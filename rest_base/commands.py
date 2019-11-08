from abc import ABC

from django.core.management import BaseCommand as DjangoBaseCommand
from django.utils import timezone

__all__ = ['BaseCommand']


class BaseCommand(DjangoBaseCommand, ABC):
    def log(self, *args):
        _args = [str(s) for s in args]
        self.stdout.write(f"[{timezone.now().strftime('%Y-%m-%d %H:%M:%S.%f')}] {' '.join(_args)}")
