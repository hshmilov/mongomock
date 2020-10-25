import json
import logging
from collections import defaultdict
from threading import RLock
from typing import Callable, Tuple, Dict, Optional

from axonius.redis.redis_client import get_db_client

logger = logging.getLogger(f'axonius.{__name__}')


class RedisCacheEntryKey:
    # key_structure = 'REDIS_CACHE_P-{PARAMS}'

    def __init__(self, key_structure: str):
        """
        :param key_structure: for exmaple  '{ENTITY}_Q-{QUERY}_P-{PARAMS}'
        """
        self.key_structure = key_structure
        self.key = None

    def generate_key(self, *args, **kwargs):
        _args = [str(arg) for arg in args]
        _kwargs = [str(value) for key, value in kwargs.items()]
        params = '_'.join(_args + _kwargs)
        return self.key_structure.format(PARAMS=params)


class RedisCache:
    """
    default ttl is 1 hour.
    """

    def __init__(self, func: Callable, key_generator: RedisCacheEntryKey,
                 ttl=60 * 60, redis_client=None):
        """
        :param func:
        :param ttl:
        :param key_generator:
        :param insert_parser This method used to parse result returned from _func before inserting them into redis.
        :param fetch_parser This method used to parse results after fetching them from redis. The result,
        will be returned to the get_value callee
        """
        self._func = func
        self._ttl = ttl
        self._client = redis_client or get_db_client(db=0)
        self._key_generator = key_generator
        self._keys_lock = defaultdict(RLock)

    def set_value(self, *args, **kwargs):
        value = kwargs.pop('value', None)
        ttl = kwargs.pop('ttl', None)
        key = self._key_generator.generate_key(*args, **kwargs)
        if not value:
            logger.debug(f'Trying to set null value for key: {key}')

        if isinstance(value, (dict, list, tuple)):
            value = json.dumps(value)

        self._client.setex(key, ttl or self._ttl, value)
        return key

    def set_value_with_key(self, key, value, ttl):
        if not value:
            logger.debug(f'Trying to set null value for key: {key}')

        if isinstance(value, (dict, list, tuple)):
            value = json.dumps(value)

        self._client.setex(key, ttl or self._ttl, value)

    def get_cache_entry(self, key) -> Tuple[Optional[Dict], Optional[int]]:
        value = self._client.get(key)
        if value:
            key_ttl = self._client.ttl(key)
            return json.loads(value), key_ttl
        return None, None

    # pylint: disable=no-self-use
    def _fetch_parser(self, cached_entry, *args, **kwargs):
        return cached_entry

    def _insert_parser(self, *args, **kwargs):
        return self._func(*args, **kwargs)

    def get_value(self, *args, **kwargs):
        key = self._key_generator.generate_key(*args, **kwargs)
        with self._keys_lock[key]:
            entry, _ = self.get_cache_entry(key)
            if entry:
                return self._fetch_parser(entry, *args, **kwargs)

            # Run actual function and cache the results.
            value = self._insert_parser(*args, **kwargs)
            self.set_value(*args, value=value, ttl=self._ttl)
            return value

    def remove_from_cache(self, *args, **kwargs) -> int:
        """
        :param mongo_filter:
        :param entity_type:
        :return:
        """
        key = self._key_generator.generate_key(*args, **kwargs)
        # using scan in order to support wildcard/patterns keys.
        for found_key in self._client.scan_iter(key):
            logger.debug(f'removing {key} from cache')
            self._client.delete(found_key)

    def update_cache(self, *args, **kwargs):
        self.set_value(*args, **kwargs)
