import logging

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
