import logging
import hashlib
from datetime import datetime
from typing import Callable, Dict, Iterator, Tuple, List
from bson import ObjectId
from pymongo.collection import Collection

from axonius.redis.redis_client import get_db_client
from axonius.utils.cache.redis_cache import RedisCache, RedisCacheEntryKey
from axonius.plugin_base import EntityType

logger = logging.getLogger(f'axonius.{__name__}')


# pylint: disable=arguments-differ

class EntitiesCacheEntryKey(RedisCacheEntryKey):

    def generate_key(self, entity_type: EntityType, mongo_filter: Dict, *args, **kwargs) -> str:
        """
        For entities cache, only entitiy_type and mongo_filter is explicitly needed for generating the key.
        :param entity_type:
        :param mongo_filter:
        :param args:
        :param kwargs:
        :return: the generated key
        """
        _args = [str(arg) for arg in args]
        _kwargs = [str(value) for key, value in kwargs.items()]
        params = '_'.join(_args + _kwargs)
        hash_key = self.generate_mongo_filter_hash(mongo_filter)
        return self.key_structure.format(ENTITY=entity_type.value, QUERY=hash_key, PARAMS=params)

    @staticmethod
    def generate_mongo_filter_hash(mongo_filter: Dict) -> str:
        """
        Aql could be very long so we need to hash it.
        :param mongo_filter:
        :return:
        """
        return hashlib.md5(str(mongo_filter).encode('utf-8')).hexdigest()

    def get_query_only_key(self, entity_type: EntityType, mongo_filter: Dict) -> str:
        """
        This method returns a key filtered only by it's mongo filter (aql).
        for example ENTITIES_CACHE_devices_{AQL_HASH}_P-*
        :param mongo_filter:
        :param entity_type:
        :return:
        """
        hash_key = EntitiesCacheEntryKey.generate_mongo_filter_hash(mongo_filter)
        return self.key_structure.format(ENTITY=entity_type.value, QUERY=hash_key, PARAMS='*')

    def get_generic_key(self, entity_type: EntityType) -> str:
        """
        This method returns a key filtered only by entity.
        for example ENTITIES_CACHE_devices_Q-*_P-*
        :param mongo_filter:
        :param entity_type:
        :return:
        """
        return self.key_structure.format(ENTITY=entity_type.value, QUERY='*', PARAMS='*')

    @staticmethod
    def get_entities_time_key(key):
        return f'{key}:TIME'


class EntitiesCache(RedisCache):
    """
    default ttl is 1 hour.
    """

    def __init__(self, func: Callable, key_generator: EntitiesCacheEntryKey, ttl=60 * 60):
        """
        :param func:
        :param key_generator:
        :param use_parsers: used as indication for _insert_parser and _fetch_parser methods. if False,
        the results will be inserted as returned from _func, and fetched as saved in redis, without
        parsing it. see _fetch_parser and _insert_parser.
        :param ttl:
        """
        redis_client = get_db_client(db=0)
        super().__init__(func, key_generator, ttl, redis_client=redis_client)

    def insert_new_entity_cache_entry(self, value, ttl, is_cache_enabled, entity_type, mongo_filter,
                                      *args, **kwargs) -> datetime:
        """
        In Entities Cache, we use a dedicated method to insert into cache, because this is cache, is always "on".
        When the user disables the cache option, we still save one single record for each entity type in
        Redis, in order to make sure page transition is fast.
        :param value: value to insert
        :param ttl:
        :param is_cache_enabled: if gui entities cache is enabled or not.
        :param entity_type:
        :param mongo_filter:
        :param args:
        :param kwargs:
        :return:
        """
        if not is_cache_enabled:
            logger.debug(f'Cached is disabled, so removing all current keys, and saving only the last one.')
            # When entities cache disabled, we keep only the latest request cached.
            key = self._key_generator.get_generic_key(entity_type)
            self.remove_matching_cache_entries(key)

        key_inserted_at = datetime.now()
        key = self.set_value(entity_type, mongo_filter, *args, **kwargs, value=value, ttl=ttl)
        self.set_key_insertion_time(key, key_inserted_at, ttl)

        return key_inserted_at

    def _fetch_parser(self, cached_entry, entities_collection, *args, **kwargs):
        ids = []
        for entity_id in cached_entry:
            ids.append(ObjectId(entity_id))

        result = entities_collection.aggregate([
            {'$match': {'_id': {'$in': ids}}},
            {'$addFields': {'__order': {'$indexOfArray': [ids, '$_id']}}},
            {'$sort': {'__order': 1}}
        ])
        return result

    def _insert_parser(self, entities_collection, entity_type, mongo_filter,
                       *args, **kwargs) -> Tuple[Iterator[Dict], List[Dict]]:
        result = self._func(entities_collection, entity_type, mongo_filter, *args, **kwargs)

        results_to_cache = []
        if result:
            for item in result:
                results_to_cache.append(str(item['_id']))
        return result, results_to_cache

    def get_value(self, entities_collection: Collection, entity_type: EntityType,
                  mongo_filter, *args, **kwargs) -> Tuple[Iterator[dict], datetime]:
        """
        Trying to get the value from cache, if doesn't exists, triggering the function and saving the results
        to redis.
        :param entities_collection:
        :param entity_type:
        :param mongo_filter:
        :param args:
        :param kwargs:
        :return:
        """
        ttl = kwargs.pop('cache_ttl', self._ttl)
        is_cache_enabled = kwargs.pop('is_cache_enabled', False)
        use_cache_entry = kwargs.pop('use_cache_entry', True)

        key = self._key_generator.generate_key(entity_type, mongo_filter, *args, **kwargs)
        with self._keys_lock[key]:

            # Try to fetch cached value.
            if use_cache_entry:
                entry, key_ttl = self.get_cache_entry(key)

                if entry:
                    key_inserted_at = self.get_key_insertion_time(key)
                    parsed = self._fetch_parser(entry, entities_collection)
                    return parsed, key_inserted_at

            # Run actual function and cache the results.
            result, results_to_cache = self._insert_parser(entities_collection, entity_type, mongo_filter,
                                                           *args, **kwargs)
            key_inserted_at = self.insert_new_entity_cache_entry(results_to_cache or result, ttl, is_cache_enabled,
                                                                 entity_type, mongo_filter, *args, **kwargs)
            return result, key_inserted_at

    def get_key_insertion_time(self, key) -> datetime:
        entry, _ = self.get_cache_entry(self._key_generator.get_entities_time_key(key))
        if entry:
            return datetime.fromtimestamp(float(entry))
        return None

    def set_key_insertion_time(self, key: str, key_inserted_at: datetime, ttl: int) -> datetime:
        """
        Setting a new key representing the insertion key time.
        :param key:
        :param key_inserted_at:
        :param ttl:
        :return:
        """
        key_inserted_at_timestamp = str(datetime.timestamp(key_inserted_at))
        self.set_value_with_key(self._key_generator.get_entities_time_key(key), key_inserted_at_timestamp, ttl)

    def remove_aql_from_cache(self, entity_type: EntityType, mongo_filter: Dict):
        """
        Remove all keys associated with a specific AQL.
        :param mongo_filter:
        :param entity_type:
        :return:
        """
        key = self._key_generator.get_query_only_key(entity_type, mongo_filter)
        self.remove_matching_cache_entries(key)

    def remove_matching_cache_entries(self, key):
        for found_key in self._client.scan_iter(key):
            self._client.delete(found_key)


class EntitiesCountCache(EntitiesCache):
    """
    Overriding EntitiesCache, because Count API's, act almost the same as entities cache, but the
    only thing that differ, are the insert/fetch parsers.
    """

    def _fetch_parser(self, cached_entry, *args, **kwargs):
        return cached_entry

    def _insert_parser(self, entities_collection, entity_type, mongo_filter,
                       *args, **kwargs) -> Tuple[Iterator[Dict], List[Dict]]:
        result = self._func(entities_collection, entity_type, mongo_filter, *args, **kwargs)
        return result, None


def entities_redis_cached():
    """
    Decorator for cached entities requests. e.g /api/devices
    """
    def wrap(func):
        key_structure = 'ENTITIES_CACHE_{ENTITY}_Q-{QUERY}_P-{PARAMS}'
        cache = EntitiesCache(func, EntitiesCacheEntryKey(key_structure))

        def actual_wrapper(*args, **kwargs):
            return cache.get_value(*args, **kwargs)

        actual_wrapper.remove_from_cache = cache.remove_aql_from_cache

        return actual_wrapper

    return wrap


def entities_count_redis_cached():
    """
    Decorator for cached entities count requests. e.g /devices/count
    """

    def wrap(func):
        key_structure = 'ENTITIES_COUNT_CACHE_{ENTITY}_Q-{QUERY}_P-{PARAMS}'
        cache = EntitiesCountCache(func, EntitiesCacheEntryKey(key_structure))

        def actual_wrapper(*args, **kwargs):
            return cache.get_value(*args, **kwargs)

        actual_wrapper.remove_from_cache = cache.remove_aql_from_cache

        return actual_wrapper

    return wrap
