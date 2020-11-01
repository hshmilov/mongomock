import logging
from datetime import datetime
from typing import List
from bson import ObjectId

from axonius.consts.gui_consts import (PRIVATE_FIELD, USER_ID_FIELD)
from axonius.utils.gui_helpers import get_connected_user_id

logger = logging.getLogger(f'axonius.{__name__}')


def filter_archived(additional_filter=None):
    """
    Returns a filter that filters out archived values
    :param additional_filter: optional - allows another filter to be made
    """
    base_non_archived = {
        'archived': {
            '$ne': True
        }
    }
    if additional_filter and additional_filter != {}:
        return {'$and': [base_non_archived, additional_filter]}
    return base_non_archived


def filter_by_name(names, additional_filter=None):
    """
    Returns a filter that filters in objects by names
    :param names: the names to filter
    :param additional_filter: optional - allows another filter to be made
    """
    base_names = {'name': {'$in': names}}
    if additional_filter and additional_filter != {}:
        return {'$and': [base_names, additional_filter]}
    return base_names


def filter_by_date_range(from_date: datetime, to_date: datetime, additional_filter=None):
    """
    Returns a filter that filters in objects by date range
    :param from_date: the earliest date to filter
    :param to_date: the latest date to filter
    :param additional_filter: optional - allows another filter to be made
    """
    base_range = {'timestamp': {'$gte': from_date, '$lt': to_date}}
    if additional_filter and additional_filter != {}:
        return {'$and': [base_range, additional_filter]}
    return base_range


def filter_by_ids(ids: List[str]):
    return {
        '_id': {
            '$in': [ObjectId(uuid) for uuid in ids]
        }
    }


def filter_by_access_and_user():
    """
    Filters out all private queries that weren't created by the current user
    ( If the query is not private, it remains as well )
    :return:
    """
    return {
        '$or': [
            {
                PRIVATE_FIELD: {
                    '$ne': True
                }
            },
            {
                '$and': [
                    {
                        PRIVATE_FIELD: {
                            '$eq': True
                        }
                    },
                    {
                        USER_ID_FIELD: {
                            '$eq': get_connected_user_id()
                        }
                    }
                ]
            }
        ]
    }
