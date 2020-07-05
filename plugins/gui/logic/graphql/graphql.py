"""
This module allows access to the bandicoot (graphql) API
"""
# pylint: disable=invalid-string-quote, invalid-triple-quote, C0103, W0611, R0911
import functools
import time
import typing
import logging
import socket
import re

import cachetools
import requests
from flask import request

from axonius.consts.gui_consts import FeatureFlagsNames
from axonius.consts.metric_consts import Query
from axonius.entities import EntityType
from axonius.logging.metric_helper import log_metric
from axonius.utils.parsing import is_valid_ip
from gui.logic.graphql.differ import Differ, logger as diff_logger
from gui.logic.graphql.translator import Translator

MAC_REGEX = re.compile("[0-9a-f]{2}([-:]?)[0-9a-f]{2}(\\1[0-9a-f]{2}){4}$", re.IGNORECASE)


SEARCH_DEVICES_API = """
        query($where: device_bool_exp!, $limit: Int = 20, $offset: Int = 0) {
          devices(
            limit: $limit,
            offset: $offset
            where: $where,
            orderBy: [adapterCount_DESC]
          ) {
            adapterCount
            adapterNames
            id
            adapterDevices {
              hostname
              name
              lastUsedUsers
              lastSeen
              interfaces {
                macAddr
                ipAddrs
              }
            }
            tags {
              name
            }
            _compatibilityAPI
          }
        }
"""

SEARCH_DEVICES_API_COUNT = """

    query($where: device_bool_exp!, $limit: Int, $offset: Int) {
        devices_aggregate(where: $where, limit: $limit, offset: $offset) {
            count
        }
    }

"""

SEARCH_USERS_API = """
        query($where: user_bool_exp!, $limit: Int = 20, $offset: Int = 0) {
          users(
            limit: $limit,
            offset: $offset
            where: $where,
            orderBy: [adapterCount_DESC]
            ){
                adapterCount
                adapterNames
                id
                adapterUsers {
                  username
                  firstName
                  lastName
                  mail
                 }
                _compatibilityAPI
             }
        }
"""

SEARCH_USERS_API_COUNT = """

    query($where: user_bool_exp!, $limit: Int = 0, $offset: Int = 0) {
        users_aggregate(where: $where, limit: $limit, offset: $offset) {
            count
        }
    }

"""

logger = logging.getLogger(f'axonius.{__name__}')


API_QUERY = {
    EntityType.Devices: {
        True: SEARCH_DEVICES_API_COUNT,
        False: SEARCH_DEVICES_API
    },
    EntityType.Users: {
        True: SEARCH_USERS_API_COUNT,
        False: SEARCH_USERS_API
    }
}

_diff_cache = cachetools.TTLCache(maxsize=32, ttl=10800)
_diff_count_cache = cachetools.TTLCache(maxsize=32, ttl=10800)


def compare_counts(entity_type: EntityType, request_data, mongo_count):
    """
    Compare count received from mongo with bandicoot
    """
    aql = request_data.get('filter')
    if not aql:
        logger.debug(f'aql filter missing, skipping..')
        return
    diff_logger.info(f'executing compare on {aql}')

    if aql in _diff_count_cache:
        diff_logger.debug(f'query {aql} already executed recently, skipping..')
        return
    # add to cache
    _diff_count_cache[aql] = 1
    # build a translator and query for results
    resp = execute_query(Translator(entity_type), entity_type,
                         aql=aql, offset=request_data.get('offset', 0), limit=request_data.get('limit', 0),
                         fields_query=request_data.get('fields'))
    if resp.status_code != 200:
        diff_logger.info(f'Query failed. Response: {resp.json()}')

    bandicoot_result = str(resp.json()['data'][f'{entity_type.value}_aggregate'])
    if not bandicoot_result == mongo_count:
        log_metric(diff_logger, Query.QUERY_DIFF, aql)
        diff_logger.warning(f'Count diff found on {aql}. Bandicoot: {bandicoot_result} Mongo: {mongo_count}')
    else:
        diff_logger.info(f'Count same on {aql}. Bandicoot: {bandicoot_result} Mongo: {mongo_count}')


def compare_results(entity_type, request_data, mongo_result):
    """
    Compare result of mongo to bandicoot
    """
    aql = request_data.get('filter')
    if not aql:
        logger.debug(f'aql filter missing, skipping..')
        return

    diff_logger.info(f'executing compare on {aql}')
    if aql in _diff_cache:
        diff_logger.debug(f'query {aql} already executed recently, skipping..')
        return

    mongo_result = list(mongo_result)
    limit = request_data.get('limit', 0)
    # if mongo result is bigger than limit we will skip compare
    if int(limit) < len(mongo_result):
        diff_logger.debug(f"Result set higher than limit {limit} < {len(mongo_result)} skipping..")
        return
    # add to cache
    _diff_cache[aql] = 1
    # build a translator and query for results
    resp = execute_query(Translator(entity_type), entity_type,
                         aql=aql, offset=request_data.get('offset', 0), limit=request_data.get('limit', 0),
                         fields_query=request_data.get('fields'))
    if resp.status_code != 200:
        diff_logger.warning(f'Query failed. Response: {resp.json()}')

    diff_logger.debug(f'Starting compare on results {aql}')
    if Differ().query_difference(resp.json(), mongo_result):
        diff_logger.info(f'Query result same on {aql}.')
    else:
        log_metric(diff_logger, Query.QUERY_DIFF, aql)
        diff_logger.warning(f'Query diff found on {aql}.')


def allow_experimental(count=False):
    """
    Decorator stating that we allow to run get experimental field
    """

    def wrap(func):
        # Create translator
        translators = {
            EntityType.Users: Translator(EntityType.Users),
            EntityType.Devices: Translator(EntityType.Devices)
        }

        @functools.wraps(func)
        def actual_wrapper(self, *args, **kwargs):
            content = self.get_request_data_as_object() if request.method == 'POST' else request.args
            if not content.get('experimental', False):
                return func(self, *args, **kwargs)
            if not self.feature_flags_config().get(FeatureFlagsNames.Bandicoot, False):
                logger.debug('bandicoot not turned on, feature flag must be turned on')
                return func(self, *args, **kwargs)
            if not self.feature_flags_config().get(FeatureFlagsNames.ExperimentalAPI, False):
                logger.debug('experimental API not turned on backend, feature flag must be turned on')
                return func(self, *args, **kwargs)
            # fallback... fallback to mongodb...
            if content.get('sort') is not None:
                return func(self, *args, **kwargs)
            # don't execute quick on experimental
            quick = content.get('quick') or request.args.get('quick')
            if quick:
                return func(self, *args, **kwargs)
            logger.info(f'Using experimental API count={count}')
            try:
                aql = content.get('filter')
                if not aql:
                    raise ValueError('Missing AQL')
                time1 = time.time()
                resp = execute_query(translators[self.entity_type], self.entity_type,
                                     aql=aql, offset=content.get('offset', None), limit=content.get('limit', None),
                                     fields_query=content.get('fields'),
                                     count=count)
                if resp.status_code != 200:
                    raise ValueError(f'Query failed. Response: {resp.json()}')
                time2 = time.time()
                logger.info('GraphQL Request count={} function took {:.3f} ms'.format(count, (time2 - time1) * 1000.0))
                return resp.text
            except (ValueError, NotImplementedError, Exception) as err:
                logger.warning('failed to use GraphQL using Mongo. Reason: %s', err)
                return func(self, *args, **kwargs)
        return actual_wrapper

    return wrap


def execute_query(translator, entity_type, aql: typing.AnyStr, limit: int = None, offset: int = None,
                  fields_query: str = None, count: bool = False) -> typing.Optional[requests.Response]:
    vars_ = {
        "where": translator.translate(aql) if aql else {},
        "limit": limit,
        "offset": offset,
        "orderBy": ['adapterCount_DESC'],
    }
    logger.debug(f'Translating AQL {aql} -> {vars_["where"]}')

    if not count and fields_query:
        query = translator.build_gql(fields_query)
        logger.debug(f'built GraphQL project query {fields_query} -> {query}')
    else:
        query = API_QUERY[entity_type][count]
    return requests.post("https://bandicoot.axonius.local:9090/query",
                         json={'query': query, 'variables': vars_})


def search_users(term: typing.AnyStr, limit: int, offset: int, count: bool = False) \
        -> typing.Optional[requests.Response]:
    vars_ = {
        "limit": limit,
        "offset": offset,
        "where": {
            "adapterUsers": {
                "OR": [
                    {"username": {"ilike": f"%{term}%"}},
                    {"firstName": {"ilike": f"%{term}%"}},
                    {"lastName": {"ilike": f"%{term}%"}},
                    {"mail": {"ilike": f"%{term}%"}}
                ]
            }
        }}
    query = SEARCH_USERS_API
    if count:
        query = SEARCH_USERS_API_COUNT
    return requests.post("https://bandicoot.axonius.local:9090/query", json={'query': query, 'variables': vars_})


def search_devices(term: typing.AnyStr, limit: int, offset: int,  count: bool = False) \
        -> typing.Optional[requests.Response]:
    """
    Executes graphql search query
    """
    query = SEARCH_DEVICES_API
    if count:
        query = SEARCH_DEVICES_API_COUNT
    if is_valid_ip(term):
        return _search_ip(term, limit, offset, query)
    if MAC_REGEX.search(term):
        return _search_mac(term, limit, offset, query)
    return _search_regex(term, limit, offset, query)


def _search_regex(term, limit, offset, query):
    vars_ = {
        "limit": limit,
        "offset": offset,
        "where": {
            "OR": [
                {"adapterNames": {"contains_regex": f"%{term}%"}},
                {"adapterDevices": {
                    "OR": [
                        {"hostname": {"ilike": f"%{term}%"}},
                        {"name": {"ilike": f"%{term}%"}},
                        {"lastUsedUsers": {"contains_regex": f"%{term}%"}},
                        {"os": {"type": {"ilike": f"%{term}%"}}}
                    ]
                }}]
        }}

    return requests.post("https://bandicoot.axonius.local:9090/query", json={'query': query, 'variables': vars_})


def _search_mac(term, limit, offset, query):
    vars_ = {
        "limit": limit,
        "offset": offset,
        "where": {"adapterDevices": {"interfaces": {"macAddr": {term}}}}
    }
    return requests.post("https://bandicoot.axonius.local:9090/query", json={'query': query, 'variables': vars_})


def _search_ip(term, limit, offset, query):
    try:
        socket.inet_pton(socket.AF_INET, term)
    except socket.error:
        term = f"::ffff:{term}"
    vars_ = {
        "limit": limit,
        "offset": offset,
        "where": {"adapterDevices": {"interfaces": {"ipAddrs": {"contains": [term]}}}}
    }
    return requests.post("https://bandicoot.axonius.local:9090/query", json={'query': query, 'variables': vars_})
