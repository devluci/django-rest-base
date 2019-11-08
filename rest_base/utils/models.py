import random
from typing import Type, Union, Optional

from django.db.models import Model, QuerySet

__all__ = ['random_instance']


def random_instance(query_set: Union[Type[Model], QuerySet])->Optional[Model]:
    if type(query_set) is not QuerySet:
        query_set = query_set.objects.all()

    cnt = query_set.count()
    if not cnt:
        return None

    return query_set[random.randrange(cnt)]
