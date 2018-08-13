import logging

logger = logging.getLogger(f'axonius.{__name__}')
"""
Utils for ldap parsing.
"""


def ldap_get(ldap_dict, ldap_key, expected_type, default_value=None):
    return _ldap_get(ldap_dict, ldap_key, expected_type, default_value)


def ldap_must_get_str(ldap_dict, ldap_key):
    return ldap_must_get(ldap_dict, ldap_key, str)


def ldap_must_get(ldap_dict, ldap_key, expected_type):
    return _ldap_get(ldap_dict, ldap_key, expected_type, raise_on_error=True)


def _ldap_get(ldap_dict, ldap_key, expected_type, default_value=None, raise_on_error=False):
    """
    An improved dict.get function for ldap results. Ldap might return different types than expected (the most popular
    is returning a list with a single element when that element is expected).
    :param ldap_dict: the ldap result dict
    :param ldap_key: the key to get
    :param expected_type: the expected result, if its convertable to this, it will be converted.
    :param default_value: what to return if something failed.
    :param raise_on_error: should we raise an exception upon an unrecoverable error.
    :return:
    """

    # Imitate the regular get
    if ldap_dict.get(ldap_key) is None:
        if raise_on_error is True:
            raise ValueError(f"requested mendatory key {ldap_key} but it doesn't exist!")
        else:
            return default_value

    # Try to fix list issues
    try:
        val = _ldap_fix(ldap_dict, ldap_key, expected_type)
    except ValueError:
        if raise_on_error is True:
            raise
        else:
            return default_value

    # if we need int but its str try to convert it:
    if type(val) == str and expected_type == int:
        try:
            val = int(val)
        except Exception:
            logger.error(f"ldap can't convert key {ldap_key} which is {val} to int")

    # Conversion succeeded but we might still not have what we wanted
    if type(val) != expected_type:
        err_msg = f"ldap key {ldap_key} after conversion was expected to be {expected_type} but its {type(val)}"
        logger.error(err_msg)
        if raise_on_error is True:
            raise ValueError(err_msg)
        else:
            return default_value

    return val


def _ldap_fix(ldap_dict, ldap_key, expected_type):
    """
    An improved dict.get function for ldap results. Ldap might return different types than expected (the most popular
    is returning a list with a single element when that element is expected).
    :param ldap_dict: the ldap result dict
    :param ldap_key: the key to get
    :param expected_type: the expected result, if its convertable to this, it will be converted.
    :return:
    """
    assert "dict" in str(type(ldap_dict)).lower()   # ldap3 uses caseinsensitive dict
    assert type(ldap_key) == str
    assert type(expected_type) == type

    val = ldap_dict.get(ldap_key)

    # The most expected scenario
    if type(val) == list and expected_type != list:
        # expected not a list, but got a list.
        if len(val) == 1:
            return val[0]

        if len(val) == 0:
            # Happens a lot..
            raise ValueError(f"failed getting key {ldap_key}, expected {expected_type}, got {val}")

        else:
            logger.warning(f"ldap key {ldap_key} was expected to be {expected_type} "
                           f"but returned a list of length {len(val)}, which is {val}")
            return val[0]

    # The second most expected one
    elif type(val) != list and expected_type == list:
        return [val]

    # Its all good, no change needed.
    return val
