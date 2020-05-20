import logging

from typing import List
from bson import ObjectId

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


def filter_by_ids(ids: List[str]):
    return {
        '_id': {
            '$in': [ObjectId(uuid) for uuid in ids]
        }
    }
