"""
This module allows access to the bandicoot (graphql) API
"""
# pylint: disable=invalid-string-quote, invalid-triple-quote
import functools
import time
import typing
import logging
import socket
import re
import requests
from flask import request

from axonius.entities import EntityType
from axonius.utils.parsing import is_valid_ip
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

    query($where: device_bool_exp!, $limit: Int = 0, $offset: Int = 0) {
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
            logger.info(f'Using experimental API')
            try:
                aql = content.get('filter')
                if not aql:
                    raise ValueError('Missing AQL')
                time1 = time.time()
                resp = execute_query(translators[self.entity_type], self.entity_type,
                                     aql=aql, offset=content.get('offset', 0), limit=content.get('limit', 0),
                                     fields_query=content.get('fields'),
                                     count=count)
                time2 = time.time()
                logger.info('GraphQL Request function took {:.3f} ms'.format((time2 - time1) * 1000.0))
                if resp.status_code != 200:
                    raise ValueError(f'Query failed. Response: {resp.json()}')
                return resp.text
            except (ValueError, NotImplementedError, Exception) as err:
                logger.warning('failed to use GraphQL using Mongo. Reason: %s', err)
                return func(self, *args, **kwargs)
        return actual_wrapper

    return wrap


def execute_query(translator, entity_type, aql: typing.AnyStr, limit: int, offset: int,
                  fields_query: str = None, count: bool = False) -> typing.Optional[requests.Response]:
    vars_ = {
        "where": translator.translate(aql) if aql else {},
        "limit": limit,
        "offset": offset
    }
    logger.debug(f'Translating AQL {aql} -> {vars_["where"]}')

    if fields_query:
        query = translator.build_gql(fields_query)
        logger.debug(f'built GraphQL project query {query}')
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
