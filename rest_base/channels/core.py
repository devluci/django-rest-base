import asyncio
from queue import SimpleQueue

import aioredis
from channels_redis.core import RedisChannelLayer, ConnectionPool, _wrap_close

__all__ = ['QueueConnectionPool', 'AutoReconnectRedisChannelLayer']


class QueueConnectionPool(ConnectionPool):
    def _ensure_loop(self, loop):
        if loop is None:
            loop = asyncio.get_event_loop()

        if loop not in self.conn_map:
            _wrap_close(loop, self)
            self.conn_map[loop] = SimpleQueue()

        return self.conn_map[loop], loop

    async def pop(self, loop=None):
        conns, loop = self._ensure_loop(loop)
        while not conns.empty():
            conn = conns.get()
            try:
                if not conn.closed:
                    break
            except Exception:
                conns.put(conn)
                raise
        else:
            conn = await aioredis.create_redis(**self.host, loop=loop)
        self.in_use[conn] = loop
        return conn

    def push(self, conn):
        loop = self.in_use[conn]
        del self.in_use[conn]
        if loop is not None:
            conns, _ = self._ensure_loop(loop)
            conns.put(conn)

    async def close_loop(self, loop):
        if loop in self.conn_map:
            conns = self.conn_map[loop]
            while not conns.empty():
                conn = conns.get()
                try:
                    conn.close()
                    await conn.wait_closed()
                except Exception:
                    conns.put(conn)
                    raise
            del self.conn_map[loop]

        for k, v in self.in_use.items():
            if v is loop:
                self.in_use[k] = None
                break

    async def close(self):
        conn_map = self.conn_map
        in_use = self.in_use
        self.reset()
        for conns in conn_map.values():
            while not conns.empty():
                conn = conns.get()
                try:
                    conn.close()
                    await conn.wait_closed()
                except Exception:
                    conns.put(conn)
                    raise
        for conn in in_use:
            conn.close()
            await conn.wait_closed()


class AutoReconnectRedisChannelLayer(RedisChannelLayer):
    def __init__(
        self,
        hosts=None,
        prefix="asgi:",
        expiry=60,
        group_expiry=86400,
        capacity=100,
        channel_capacity=None,
        symmetric_encryption_keys=None,
    ):
        super().__init__(hosts, prefix, expiry, group_expiry, capacity, channel_capacity, symmetric_encryption_keys)
        self.pools = [QueueConnectionPool(host) for host in self.hosts]
