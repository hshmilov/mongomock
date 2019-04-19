def filter_archived(additional_filter=None):
    """
    Returns a filter that filters out archived values
    :param additional_filter: optional - allows another filter to be made
    """
    base_non_archived = {'$or': [{'archived': {'$exists': False}}, {'archived': False}]}
    if additional_filter and additional_filter != {}:
        return {'$and': [base_non_archived, additional_filter]}
    return base_non_archived
