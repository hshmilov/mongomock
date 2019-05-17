import logging

from axonius.entities import EntityType

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


def find_filter_by_name(self, entity_type: EntityType, name):
    """
    From collection of views for given entity_type, fetch that with given name.
    Return it's filter, or None if no filter.
    """
    if not name:
        return None
    view_doc = self.gui_dbs.entity_query_views_db_map[entity_type].find_one({'name': name})
    if not view_doc:
        logger.info(f'No record found for view {name}')
        return None
    return view_doc['view']
