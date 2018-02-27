def dict_filter(d: dict, remove_predicate: callable) -> dict:
    """
    :param remove_predicate: filtering predicate (removes if true)
    :param d: dict to filter
    :return: recursively removes values from dict based on predicate
    :note: modifies the original dict as well
    """
    if isinstance(d, dict):
        for k, v in d.copy().items():
            if isinstance(v, dict):
                dict_filter(v, remove_predicate)
            elif isinstance(v, list):
                for item in v:
                    dict_filter(item, remove_predicate)
            elif remove_predicate(v):
                del d[k]

    return d
