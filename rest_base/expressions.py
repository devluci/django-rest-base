from django.db.models import F

__all__ = ['StrF']


class StrF(F):
    ADD = '||'
