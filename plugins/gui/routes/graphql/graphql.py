"""
This module allows access to the bandicoot (graphql) API
"""
# pylint: disable=invalid-string-quote, invalid-triple-quote
import typing
import socket
import re
import requests

from axonius.utils.parsing import is_valid_ip

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


def search_users(term: typing.AnyStr, limit: int, offset: int, count: bool = False) \
        -> typing.Optional[requests.Response]:
    vars_ = {
        "limit": limit,
        "offset": offset,
        "where": {
            "adapterUsers": {
                "OR": [
                    {"username_ilike": f"%{term}%"},
                    {"firstName_ilike": f"%{term}%"},
                    {"lastName_ilike": f"%{term}%"},
                    {"mail_ilike": f"%{term}%"}
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
                {"adapterNames_contains_regex": f"%{term}%"},
                {"adapterDevices": {
                    "OR": [
                        {"hostname_ilike": f"%{term}%"},
                        {"name_ilike": f"%{term}%"},
                        {"lastUsedUsers_contains_regex": f"%{term}%"},
                        {"os": {"type_ilike": f"%{term}%"}}
                    ]
                }}]
        }}

    return requests.post("https://bandicoot.axonius.local:9090/query", json={'query': query, 'variables': vars_})


def _search_mac(term, limit, offset, query):
    vars_ = {
        "limit": limit,
        "offset": offset,
        "where": {"adapterDevices": {"interfaces": {"macAddr_eq": term}}}
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
        "where": {"adapterDevices": {"interfaces": {"ipAddrs_contains": [term]}}}
    }
    return requests.post("https://bandicoot.axonius.local:9090/query", json={'query': query, 'variables': vars_})
