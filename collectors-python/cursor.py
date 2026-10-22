"""Typed monotonic Redis cursors shared by collectors.

Runner sessions stage checkpoints until the backend confirms persistence. Standalone
collector calls commit directly. Corrupt/unavailable Redis fails closed, not full scan.
"""
from contextlib import contextmanager
from contextvars import ContextVar
from datetime import date
import os
import re

import redis

_pending = ContextVar('collector_cursor_updates', default=None)
_CAS = """
local current = redis.call('GET', KEYS[1])
if ARGV[1] == '0' then
  if current then return 0 end
else
  if current ~= ARGV[2] then return 0 end
end
redis.call('SET', KEYS[1], ARGV[3])
return 1
"""


@contextmanager
def deferred_cursors():
    pending = {}
    token = _pending.set(pending)
    try:
        yield pending
    finally:
        _pending.reset(token)


class CursorManager:
    def __init__(self, namespace, kind='int', *, redis_client=None, redis_url=None, key=None):
        if not re.fullmatch(r'[a-z][a-z0-9_]*', namespace) or kind not in ('int', 'date'):
            raise ValueError('Invalid cursor namespace or kind')
        self.namespace, self.kind = namespace, kind
        suffix = 'last_article_id' if kind == 'int' else 'last_date'
        self.key = key or f'collector:{namespace}:{suffix}'
        self.client = redis_client if redis_client is not None else redis.Redis.from_url(
            redis_url or os.getenv('REDIS_URL', 'redis://localhost:16380/0'),
            decode_responses=True, socket_connect_timeout=5, socket_timeout=5,
        )

    def _validate(self, value):
        if isinstance(value, bytes):
            value = value.decode('utf-8')
        if self.kind == 'int':
            if isinstance(value, bool) or not re.fullmatch(r'[1-9][0-9]*', str(value)):
                raise ValueError(f'Invalid integer cursor at {self.key}: {value!r}')
            return int(value)
        if not isinstance(value, str) or not re.fullmatch(r'\d{4}-\d{2}-\d{2}', value):
            raise ValueError(f'Invalid date cursor at {self.key}: {value!r}')
        return date.fromisoformat(value).isoformat()

    def get(self):
        pending = _pending.get()
        if pending is not None and self.key in pending:
            return self._validate(pending[self.key]['value'])
        value = self.client.get(self.key)
        return None if value is None else self._validate(value)

    def advance(self, value):
        value = self._validate(value)
        pending = _pending.get()
        if pending is not None:
            previous = self.get()
            if previous is None or value > previous:
                pending[self.key] = {'namespace': self.namespace, 'kind': self.kind,
                                     'key': self.key, 'value': str(value)}
            return value if previous is None else max(value, previous)
        for _ in range(16):
            current = self.client.get(self.key)
            previous = None if current is None else self._validate(current)
            if previous is not None and previous >= value:
                return previous
            expected = current.decode() if isinstance(current, bytes) else current
            if self.client.eval(_CAS, 1, self.key, '0' if current is None else '1',
                                expected or '', str(value)):
                return value
        raise RuntimeError(f'Cursor contention exceeded retry budget: {self.key}')

    def lock(self, timeout):
        return self.client.lock(self.key + ':lock', timeout=timeout)
