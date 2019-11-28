from channels.generic.websocket import WebsocketConsumer, DenyConnection

__all__ = ['NullConsumer']


class NullConsumer(WebsocketConsumer):
    def connect(self):
        raise DenyConnection
