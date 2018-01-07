BAD_KEY = '.'
FILLER = '#'
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


def escape_dict(adict: dict):
    """
    Remove illegal character '.' for mongo
    :param adict:
    :return escaped dict
    :note The function modifies the dict
    """
    keys = list(adict)
    for key in keys:
        value = adict[key]

        if isinstance(value, dict):
            escape_dict(value)

        if isinstance(key, str) and BAD_KEY in key:
            escaped = escape_key(key)
            adict[escaped] = value
            del adict[key]
    return adict
