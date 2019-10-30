import logging
from collections import defaultdict
from datetime import datetime
from threading import Event, RLock
from typing import Callable, Iterable, Tuple, Dict, Hashable, List

from apscheduler.job import Job
from apscheduler.triggers.interval import IntervalTrigger
from cachetools import keys
from dataclasses import dataclass, field

from axonius.entities import EntityType
from axonius.utils.get_plugin_base_instance import plugin_base_instance

logger = logging.getLogger(f'axonius.{__name__}')


def hashkey(func: Callable, *args, **kwargs):
    """
    keys.hashkey by itself doesn't properly handle **kwargs

    This isn't slow:

    %timeit hashkey(blat, 1,5,c=5)
    3.6 µs ± 89 ns per loop (mean ± std. dev. of 7 runs, 100000 loops each)

    %timeit hashkey(blat, 1,5)
    920 ns ± 34.4 ns per loop (mean ± std. dev. of 7 runs, 1000000 loops each)

    """
    badobject = object()

    arglist = list(args)

    if kwargs:
        kwargs = dict(kwargs)

        if len(arglist) < func.__code__.co_argcount:
            arglist += [badobject] * (func.__code__.co_argcount - len(arglist))

        args_conversion = {arg_name: index
                           for index, arg_name
                           in enumerate(func.__code__.co_varnames)}

        to_remove_keys = []

        for k, v in kwargs.items():
            index_in_args = args_conversion.get(k)
            if index_in_args is None:
                continue

            if badobject != arglist[index_in_args]:
                raise TypeError(f'{func} got multiple values for argument {k}')

            arglist[index_in_args] = v
            to_remove_keys.append(k)

        for k in to_remove_keys:
            del kwargs[k]

        if badobject in arglist:
            raise TypeError(f'{func} is missing required arguments, arguments = {arglist}')

    return keys.hashkey(*arglist, **kwargs)


@dataclass()
class CachedEntry:
    """
    Represent a cache entry in RevCached
    """
    # Args to pass to the function
    args: Tuple
    kwargs: Dict
    # The last time this value was fetched
    last_accessed: datetime
    # Calculated key for this cached entry
    key: Hashable
    # The function to call
    func: Callable
    # The currently cached value
    calculated_value: object = None
    # If not none, this means an exception has been raised
    exception: Exception = None
    # Is the value ready?
    event: Event = field(default_factory=Event)
    # The job associated with this cache entry
    job: Job = None

    def get_cached_result(self):
        """
        helper for get_value
        """
        # pylint  mistakes this for a 'field'
        if not self.event.wait(900):
            logger.error(f'Timeout on {self}!')
            self.job.modify(next_run_time=datetime.now())
            plugin_base_instance().cached_operation_scheduler.wakeup()
            return self.func(*self.args, **self.kwargs)

        self.last_accessed = datetime.now()
        if self.exception:
            raise self.exception
        return self.calculated_value


ALL_CACHES: List['RevCached'] = []

# When using update_cache or clear_cache, use this as a wildcard arg to clean all matching caches
WILDCARD_ARG = object()


class RevCached:
    """
    An idling cache is a cache that doesn't do anything, and you have to fire it up to get it going.
    A revving cache is a like a car engine that is turned on: It can go off at will!

    This is a cache that will respond immediately, regardless of state.
    The only case it won't respond immediately is when it just started (you can't beat that)

    It will keep recalculating the results of the given func every TTL, but will keep the last result so
    you won't hang up.

    initial_values is the values to keep the cache hot for.
        This is a list of *args
        Any other value that might arrive will also be hot cached for, but only after they are first accessed
    """

    def __init__(self, ttl: int, func: Callable, initial_values: Iterable[Tuple], remove_from_cache_ttl: int,
                 key_func: Callable = None):
        """
        Creates a new revved cache
        :param ttl: How long until we should recalculate values
        :param func: Which function calculates the values
        :param initial_values: Initial values that have to stay fresh at the cache
                               these values are expected to be a tuple that will be passed, as *args,
                               into "func".
        :param remove_from_cache_ttl: If a key wasn't accessed for this long, we should remove it from the cache
                                      This also means it won't be recalculated
                                      Pass 0 if you want keys to stay forever
        :param key_func: If given, will use this as a hash function over the arguments to the function
        """
        self.__key_func = key_func

        # Used to protect __initial_values
        self.__initial_values_lock_dict = defaultdict(RLock)

        self.__remove_from_cache_ttl = remove_from_cache_ttl
        self.__ttl = ttl

        self.__func = func

        self.__initial_values: Dict[Hashable, CachedEntry] = \
            {self.__get_key_from_args(*value): CachedEntry(value, {}, datetime.now(),
                                                           self.__get_key_from_args(*value), self.__func)
             for value
             in initial_values}

        self.__initialized = False

    def delayed_initialization(self):
        """
        Must be called only once, and from PluginBase
        :return:
        """
        if self.__initialized:
            return

        for name, value in self.__initial_values.items():
            value.job = plugin_base_instance().cached_operation_scheduler.add_job(
                func=self.__warm_cache,
                args=[value],
                trigger=IntervalTrigger(
                    seconds=self.__ttl),
                name=f'{self.__func.__name__}_calc',
                max_instances=1)

        if self.__remove_from_cache_ttl:
            plugin_base_instance().cached_operation_scheduler.add_job(func=self.__clean_unused_values,
                                                                      trigger=IntervalTrigger(
                                                                          seconds=self.__remove_from_cache_ttl / 2),
                                                                      name=f'{self.__func.__name__}_clean',
                                                                      max_instances=1)

        self.__initialized = True

    def __get_key_from_args(self, *args, **kwargs):
        if self.__key_func:
            return self.__key_func(*args, **kwargs)
        return hashkey(self.__func, *args, **kwargs)

    def __warm_cache(self, cache_entry: CachedEntry):
        """
        Updates the value in the cache for the function with the given parameters
        """
        with self.__initial_values_lock_dict[cache_entry.key]:
            started_time = datetime.now()
            try:
                cache_entry.calculated_value = self.__func(*cache_entry.args, **cache_entry.kwargs)
                cache_entry.exception = None
            except Exception as e:
                cache_entry.exception = e
            logger.debug(f'Calculated {self.__func.__name__}({cache_entry.args}, {cache_entry.kwargs})'
                         f' in {(datetime.now() - started_time).total_seconds()}')

            cache_entry.event.set()

    def __clean_unused_values(self):
        """
        If a cached values hasn't been used for a while, we'll stop calculating it
        """
        to_delete_keys = []
        for k, v in dict(self.__initial_values).items():
            if (datetime.now() - v.last_accessed).total_seconds() > self.__remove_from_cache_ttl:
                to_delete_keys.append(k)

        for k in to_delete_keys:
            cached_entity = self.__initial_values.pop(k, None)
            cached_entity.job.remove()

    def get_value(self, *args, **kwargs):
        """
        Gets the value from the cache if it's a value that was present in "initial_values"
        If it's not, add it

        This deals with the case that a fetch request is made before the first value
        has been calculated to make sure we don't run the function more than necessary
        """
        key = self.__get_key_from_args(*args, **kwargs)

        cache_entry = self.__initial_values.get(key)
        if cache_entry:
            return cache_entry.get_cached_result()

        with self.__initial_values_lock_dict[key]:
            cache_entry = self.__initial_values.get(key)
            if cache_entry:
                return cache_entry.get_cached_result()

            cache_entry = CachedEntry(args, kwargs, datetime.now(), key, self.__func)
            self.__warm_cache(cache_entry)
            cache_entry.job = plugin_base_instance().cached_operation_scheduler.add_job(
                func=self.__warm_cache,
                args=[cache_entry],
                trigger=IntervalTrigger(
                    seconds=self.__ttl),
                name=f'{self.__func.__name__}_calc',
                max_instances=1)
            self.__initial_values[key] = cache_entry
            return cache_entry.get_cached_result()

    def get_all_values(self, args: List = None) -> Iterable[CachedEntry]:
        """
        Get all CachedEntries from the args list
        """
        initial_values = dict(self.__initial_values)
        if not args:
            yield from initial_values.values()
            return

        if WILDCARD_ARG not in args:
            yield initial_values.get(self.__get_key_from_args(*args))
            return

        for initial_value in initial_values.values():
            if all(v is WILDCARD_ARG or (len(initial_value.args) >= index and v == initial_value.args[index])
                   for index, v
                   in enumerate(args)):
                yield initial_value

    def trigger_cache_update_now(self, args: List = None) -> int:
        """
        Triggers a cache update right now, asynchronously
        :param args: If not none, only update that specific parameter set. Otherwise, updates all values
        :return: The amount of cache entries affected
        """
        counter = 0
        for cached_entry in self.get_all_values(args):
            if cached_entry:
                cached_entry.job.modify(next_run_time=datetime.now())
                counter += 1

        plugin_base_instance().cached_operation_scheduler.wakeup()
        return counter

    def sync_clean_cache(self, args: List = None) -> int:
        """
        Triggers a cache flush synchronously
        :param args: If not none, only update that specific parameter set. Otherwise, updates all values
        :return: The amount of cache entries affected
        """
        counter = 0
        for cached_entry in self.get_all_values(args):
            if cached_entry:
                cached_entry.event.clear()
                counter += 1

        self.trigger_cache_update_now(args)
        return counter

    def call_uncached(self, *args, **kwargs):
        """
        Please don't abuse this!
        """
        return self.__func(*args, **kwargs)


def rev_cached(ttl: int, initial_values: Iterable[Tuple] = None, remove_from_cache_ttl: int = 3600 * 48,
               key_func: Callable = None):
    """
    See RevCached documentation
    You can call .update_cache on the method this decorates to trigger a cache update asynchronously
    You can call .clean_cache on the method this decorates to trigger a cache flush that will guarantee
        that the old value is deleted
    You can call "call_uncached" on the method to force a recalculation. The value won't be saved for reference.
        Please don't abuse this!
    """

    def wrap(func):
        cache = RevCached(ttl, func, initial_values or [], remove_from_cache_ttl, key_func=key_func)
        ALL_CACHES.append(cache)

        def actual_wrapper(*args, **kwargs):
            return cache.get_value(*args, **kwargs)

        actual_wrapper.update_cache = cache.trigger_cache_update_now
        actual_wrapper.clean_cache = cache.sync_clean_cache
        actual_wrapper.call_uncached = cache.call_uncached

        return actual_wrapper

    return wrap


def rev_cached_entity_type(ttl: int, remove_from_cache_ttl: int = 0, key_func: Callable = None):
    """
    Same as rev_cached, but assumes the only parameter for the function is EntityType
    and cached over all entity types
    """
    return rev_cached(ttl, initial_values=[(x,) for x in EntityType], remove_from_cache_ttl=remove_from_cache_ttl,
                      key_func=key_func)
