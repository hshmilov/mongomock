BAD_KEY = '.'
FILLER = '_DOT_'
HELPER = ';'


def escape_key(key):
    """
    :param key: key
    :return: escaped key
    """
    return key.replace(FILLER, FILLER + HELPER).replace(BAD_KEY, FILLER * 2)


def unescape_key(key):
    """
    :param key: escaped key
    :return: unescaped key
    """
    return key.replace(FILLER * 2, BAD_KEY).replace(FILLER + HELPER, FILLER)


def escape_dict(to_escape: object):
    """
    Remove illegal character '.' for mongo from dictionaries
    :param to_escape: escape this object. if it's not a dict, returned as-s
    :return escaped dict
    """
    if not isinstance(to_escape, dict):
        return to_escape

    return {escape_key(str(k)): escape_dict(v) for k, v in to_escape.items()}
