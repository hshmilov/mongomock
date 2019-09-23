from typing import Tuple
import time
from datetime import datetime
import random
import pymongo

from axonius.utils.axonius_query_language import parse_filter

from pymongo import MongoClient

# This file is WIP.
# TLDR - It's a sloppy framework for establishing performance measurements on a DB

c = MongoClient('127.0.0.1:27017', username='ax_user', password='ax_pass')
db = c['aggregator']

col = db['devices_db']
col2 = db['materialized_devices_db']

devices_views_col = c['gui']['device_views']
devices_queries = set([x['view']['query']['filter'] for x in devices_views_col.find()])
devices_queries = [x for x in devices_queries if x and len(x) < 1500]


def fix_for_materialized(f):
    if isinstance(f, dict):
        if len(f) == 1 and list(f)[0] in ('tags', 'data._old', 'pending_delete'):
            return '!!!'
        else:
            return {
                k: fix_for_materialized(v)
                for k, v
                in f.items()
                if fix_for_materialized(v) != '!!!'
            }
    elif isinstance(f, list):
        return [fix_for_materialized(x) for x in f if fix_for_materialized(x) != '!!!']
    return f


def perform(q: str, c=col, materialize: bool=True, natural_hint=False) -> Tuple[int, int]:
    f = parse_filter(q)
    if materialize:
        f = fix_for_materialized(f)

    if natural_hint:
        started = datetime.now()
        res = c.count_documents(f, hint=[('$natural', 1)])
        ended = datetime.now()
    else:
        started = datetime.now()
        res = c.count_documents(f)
        ended = datetime.now()

    result_time = (ended - started).total_seconds()
    print(f'Took {result_time} - res len {(res)} on {c.name}')
    return res, result_time


def perform_mongo_query(q: dict, c=col, natural_hint=False) -> Tuple[int, int]:
    if natural_hint:
        started = datetime.now()
        res = c.count_documents(q, hint=[('$natural', 1)])
        ended = datetime.now()
    else:
        started = datetime.now()
        res = c.count_documents(q)
        ended = datetime.now()

    result_time = (ended - started).total_seconds()
    # print(f'Took {result_time} - res len {(res)} on {c.name}')
    return res, result_time


def heuristic_hint(query: str) -> bool:
    return 'specific_data.data.name == regex(' in query or '[plugin_name not in [' in query or 'data.hostname == regex(' in query


def materialize(date=None):
    if not date:
        date = datetime.min
    started = datetime.now()
    print(f'started at {started}')
    res = col.aggregate([
        {
            '$match': {
                'accurate_for_datetime': {
                    '$gte': date
                }
            }
        },
        {
            '$project': {
                'adapters.data.raw': 0,
            }
        },
        {
            '$merge': {
                'into': 'materialized_devices_db',
                'whenMatched': 'replace',
            }
        }
    ])
    ended = datetime.now()
    print(f'Took {(ended-started).total_seconds()} - len {(res)}')


def materialize_old(date=None):
    if not date:
        date = datetime.min
    started = datetime.now()
    print(f'started at {started}')
    res = col.aggregate([
        {
            '$match': {
                'accurate_for_datetime': {
                    '$gte': date
                }
            }
        },
        {
            '$project': {
                'adapters.data.raw': 0,
            }
        },
        {
            '$out': 'materialized_devices_db',
        }
    ])
    ended = datetime.now()
    print(f'Took {(ended-started).total_seconds()} - len {(res)}')


def loop_materialize():
    while True:
        with col.watch(batch_size=1) as stream:
            for change in stream:
                print(change)
                break
        time.sleep(0.3)


def race_query(query):
    reg_res, reg_time = perform(query, col)
    materialized_res, materialized_time = perform(query, col2, True, natural_hint=heuristic_hint(query))
    return reg_res, reg_time, materialized_res, materialized_time


def perform_race(counter=15):
    sum_reg = 0
    sum_materialized = 0
    random.shuffle(devices_queries)

    terrible_queries = []
    for query in devices_queries[:counter]:
        try:
            reg_res, reg_time, materialized_res, materialized_time = race_query(query)
            if materialized_res != reg_res:
                print(f'ERROR Conflict, {materialized_res} vs {reg_res}')
            print(f'{reg_time} vs {materialized_time} for: "{query}"')
            sum_reg += reg_time
            sum_materialized += materialized_time

            if reg_time > 1.5 or materialized_time > 1.5:
                reg_res, nhreg_time = perform(query, col, natural_hint=True)
                materialized_res, nhmaterialized_time = perform(query, col2, True, natural_hint=True)
                print(f'Above was a terrible query, with natural hint: {nhreg_time} vs {nhmaterialized_time}')

                terrible_queries.append((reg_time, materialized_time, nhreg_time, nhmaterialized_time, query))

            print('-----------------------------')

        except Exception as e:
            print(f'exception in {query}, {e}')

    print(f'Regular time: {sum_reg}')
    print(f'Materialized time: {sum_materialized}')

    if sum_materialized < sum_reg:
        print(f'MATERIALIZED WON :) And saved {int((1-(sum_materialized/sum_reg))*100)}%')
    if sum_reg < sum_materialized:
        print(f'REGULAR WON :( And saved {int((1-(sum_reg/sum_materialized))*100)}%')
    for reg_time, materialized_time, nhreg_time, nhmaterialized_time, query in terrible_queries:
        print(
            f'Terrible query: {reg_time}, {materialized_time} VS natural: {nhreg_time}, {nhmaterialized_time}')
        print(query)
        print('---------------------------')


PLUGIN_NAME = 'plugin_name'
PLUGIN_UNIQUE_NAME = 'plugin_unique_name'


def common_db_indexes(db):
    db.create_index(
        [(f'adapters.{PLUGIN_UNIQUE_NAME}', pymongo.ASCENDING), ('adapters.data.id', pymongo.ASCENDING)
         ], unique=True, background=True)
    db.create_index(
        [(f'adapters.{PLUGIN_NAME}', pymongo.ASCENDING), ('adapters.data.id', pymongo.ASCENDING)
         ], unique=True, background=True)
    db.create_index([(f'adapters.{PLUGIN_NAME}', pymongo.ASCENDING)], background=True)
    db.create_index([(f'adapters.{PLUGIN_UNIQUE_NAME}', pymongo.ASCENDING)], background=True)
    db.create_index([('adapters.client_used', pymongo.DESCENDING)], background=True)

    # this is commonly filtered by the GUI
    db.create_index([('adapters.data.id', pymongo.ASCENDING)], background=True)
    db.create_index([('adapters.pending_delete', pymongo.ASCENDING)], background=True)
    db.create_index([(f'adapters.data.adapter_properties', pymongo.ASCENDING)], background=True)
    db.create_index([(f'adapters.data.os.type', pymongo.ASCENDING)], background=True)
    db.create_index([(f'adapters.data.os.distribution', pymongo.ASCENDING)], background=True)
    db.create_index([(f'adapters.data.last_seen', pymongo.ASCENDING)], background=True)
    db.create_index([(f'adapters.data.hostname', pymongo.ASCENDING)], background=True)
    db.create_index([(f'adapters.data.name', pymongo.ASCENDING)], background=True)
    db.create_index([(f'adapters.data.network_interfaces.mac', pymongo.ASCENDING)], background=True)
    db.create_index([(f'adapters.data.network_interfaces.ips', pymongo.ASCENDING)], background=True)
    db.create_index([(f'adapters.data.network_interfaces.ips_raw', pymongo.ASCENDING)], background=True)
    db.create_index([(f'adapters.data.last_used_users', pymongo.ASCENDING)], background=True)
    db.create_index([(f'adapters.data.username', pymongo.ASCENDING)], background=True)
    db.create_index([(f'adapters.data.installed_software.name', pymongo.ASCENDING)], background=True)
    db.create_index([(f'adapters.data.fetch_time', pymongo.ASCENDING)], background=True)
