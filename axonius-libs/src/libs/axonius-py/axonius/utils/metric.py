import binascii


def filter_ids(inp):
    if not inp:
        return inp
    try:
        binascii.unhexlify(inp)
        return '_id_'
    except Exception:
        return inp


def remove_ids(path):
    splitted = path.split('/')
    noids = [filter_ids(s) for s in splitted]
    cleanpath = '/'.join(noids)
    return cleanpath
