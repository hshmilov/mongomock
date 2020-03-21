import logging
from itertools import tee, filterfalse

from digicert_certcentral_adapter import consts

logger = logging.getLogger(f'axonius.{__name__}')

# copied from itertools reciepe - https://docs.python.org/3.6/library/itertools.html


def partition(pred, iterable):
    'Use a predicate to partition entries into false entries and true entries'
    # partition(is_odd, range(10)) --> 0 2 4 6 8   and  1 3 5 7 9
    t1, t2 = tee(iterable)
    return filterfalse(pred, t1), filter(pred, t2)


def parse_enum(device_raw: dict, field_name: str, whitelist: list):
    values_list = device_raw.get(field_name)
    # remove empty values
    if not values_list:
        return None

    # split and strip comma separated string (implicitly non empty) values
    if isinstance(values_list, str):
        values_list = list(map(str.strip, values_list.split(',')))

    # log invalid values and remove
    if not isinstance(values_list, list):
        logger.warning(f'{consts.ENUM_UNKNOWN_VALUE_LOG_PREFIX}'
                       f' Unexpected values retrieved for field "{field_name}" in raw: {device_raw}')
        return None

    # filter out blacklisted values
    blacklisted, whitelisted = list(map(list, partition(whitelist.__contains__, values_list)))
    if blacklisted:
        logger.warning(f'{consts.ENUM_BLACKLISTED_VALUE_LOG_PREFIX}'
                       f' Unknown "{field_name}" value encountered "{",".join(blacklisted)}"'
                       f' for whitelist {whitelist} in raw: {device_raw}.')
    return whitelisted or None
