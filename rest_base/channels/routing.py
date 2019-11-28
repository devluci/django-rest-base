from typing import List, Union

from channels.routing import URLRouter
from django.urls import URLPattern, URLResolver, re_path

from .consumers import NullConsumer

__all__ = ['NullURLRouter']


class NullURLRouter(URLRouter):
    def __init__(self, routes: List[Union[URLPattern, URLResolver]]):
        routes.append(re_path(r'', NullConsumer))
        super().__init__(routes)
