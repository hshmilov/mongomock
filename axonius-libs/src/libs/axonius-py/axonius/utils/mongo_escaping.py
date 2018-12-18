TABLE = {
    '.': '_DOT_',
    '$': '_DOL_',
}

HELPER = ';'


def escape_key(key):
    """
    :param key: key
    :return: escaped key
    """
    for bad_key, filler in TABLE.items():
        key = key.replace(filler, filler + HELPER).replace(bad_key, filler * 2)
    return key


def unescape_key(key):
    """
    :param key: escaped key
    :return: unescaped key
    """
    for bad_key, filler in TABLE.items():
        key = key.replace(filler * 2, bad_key).replace(filler + HELPER, filler)
    return key


def escape_dict(to_escape: object):
    """
    Remove illegal character '.' for mongo from dictionaries
    :param to_escape: escape this object. if it's not a dict, returned as-s
    :return escaped dict
    """
    if isinstance(to_escape, dict):
        return {escape_key(str(k)): escape_dict(v) for k, v in to_escape.items()}
    if isinstance(to_escape, list):
        return [escape_dict(x) for x in to_escape]
    return to_escape


def unescape_dict(to_unescape: object):
    if isinstance(to_unescape, dict):
        return {unescape_key(str(k)): unescape_dict(v) for k, v in to_unescape.items()}
    if isinstance(to_unescape, list):
        return [unescape_dict(x) for x in to_unescape]
    return to_unescape
