try:
    import channels
except ImportError as e:
    raise ImportError(
        'channels must be installed to use rest_base.consumers. Try `pip install django-rest-base[channels]`.'
    ) from e

from channels.generic.websocket import WebsocketConsumer, DenyConnection

__all__ = ['NullConsumer']


class NullConsumer(WebsocketConsumer):
    def connect(self):
        raise DenyConnection
