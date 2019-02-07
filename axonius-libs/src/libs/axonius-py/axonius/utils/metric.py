import binascii


def filter_ids(inp):
    if not inp:
        return inp
    try:
        binascii.unhexlify(inp)
        return '_id_'
    except Exception:
        return inp
