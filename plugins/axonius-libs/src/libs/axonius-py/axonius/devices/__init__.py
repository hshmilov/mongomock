def deep_merge_only_dict(new_data, final_data):
    """
    Merge two dict objects recursively. good for merging to axonius.device.to_dict() objects to have one final.

    >>> a = { 'first' : { 'all_rows' : { 'pass' : 'dog', 'number' : '1' } } }
    >>> b = { 'first' : { 'all_rows' : { 'fail' : 'cat', 'number' : '5' } } }
    >>> deep_merge_only_dict(b, a) == { 'first' : { 'all_rows' : { 'pass' : 'dog', 'fail' : 'cat', 'number' : '5' } } }
    True
    """
    for key, value in new_data.items():
        if isinstance(value, dict):
            # get node or create one
            node = final_data.setdefault(key, {})
            deep_merge_only_dict(value, node)
        else:
            final_data[key] = value

    return final_data
