import datetime
import logging
import re

import ipaddress
from dateutil.tz import tzutc
from dateutil.parser import parse as parse_date

from axonius.fields import Field, ListField, JsonStringFormat
from axonius.smart_json_class import SmartJsonClass
from axonius.utils.parsing import normalize_var_name, format_ip
from axonius.clients.tanium import consts

logger = logging.getLogger(f'axonius.{__name__}')


def get_item1(value):
    if isinstance(value, (list, tuple)):
        return value[0] if value else None
    return value


def listify(value, clean=False):
    if isinstance(value, tuple):
        value = list(value)

    if value in consts.VALUES_EMPTY:
        value = []

    if not isinstance(value, list):
        value = [value]

    if clean:
        clean_values = [None, [], {}, '']
        value = [x for x in value if x not in clean_values]

    return value


def check_attr(obj, attr):
    try:
        return getattr(obj, attr, None)
    except Exception:
        return None


def dt_now(utc=True):
    return datetime.datetime.now(tzutc()) if utc else datetime.datetime.now()


def dt_ago_mins(mins, inverse=False):
    now = dt_now()
    delta = datetime.timedelta(seconds=mins * 60)
    if inverse:
        return now + delta
    return now - delta


def dt_calc_mins(value, reverse=False):
    now = dt_now()
    try:
        if reverse:
            if value <= now:
                return 0.0
            calc_value = value - now
        else:
            if value >= now:
                return 0.0
            calc_value = now - value
        value = float('%.1f' % (calc_value.seconds / 60))
    except Exception:
        logger.exception(f'Failed to calculate mins {value} vs {now}')
        value = 0.0
    return 0.0 if value <= 0.0 else value


def dt_is_past(value):
    if not isinstance(value, datetime.datetime):
        value = parse_dt(value)

    return value <= dt_now()


def set_csv(device, device_raw, key, attr, callback=None):
    values = device_raw.get(key)
    pvalues = parse_csv(values)

    if callback:
        pvalues = callback(pvalues)

    try:
        dvc_attr = check_attr(device, attr) or []
        for value in pvalues:
            if value not in dvc_attr:
                dvc_attr.append(value)
    except Exception:
        logger.exception(f'Problem adding {attr!r} from {key!r} value {values!r} pvalue {pvalues!r} in {device_raw!r}')


def set_bool(device, device_raw, key, attr):
    value = device_raw.get(key)
    pvalue = parse_bool(value)

    try:
        setattr(device, attr, pvalue)
    except Exception:
        logger.exception(f'Problem setting {attr!r} from {key!r} value {value!r} pvalue {pvalue!r} in {device_raw!r}')


def set_int(device, device_raw, key, attr):
    value = device_raw.get(key)
    pvalue = parse_int(value)

    try:
        setattr(device, attr, pvalue)
    except Exception:
        logger.exception(f'Problem setting {attr!r} from {key!r} value {value!r} pvalue {pvalue!r} in {device_raw!r}')


def set_str(device, device_raw, key, attr):
    value = device_raw.get(key)
    pvalue = parse_str(value)

    try:
        setattr(device, attr, pvalue)
    except Exception:
        logger.exception(f'Problem setting {attr!r} from {key!r} value {value!r} pvalue {pvalue!r} in {device_raw!r}')


def set_ip(device, device_raw, key, attr):
    value = device_raw.get(key)
    pvalue = parse_ip(value)

    try:
        setattr(device, attr, pvalue)
    except Exception:
        logger.exception(f'Problem setting {attr!r} from {key!r} value {value!r} pvalue {pvalue!r} in {device_raw!r}')


def set_dt(device, device_raw, key, attr):
    value = device_raw.get(key)
    pvalue = parse_dt(value)

    try:
        setattr(device, attr, pvalue)
    except Exception:
        logger.exception(f'Problem setting {attr!r} from {key!r} value {value!r} pvalue {pvalue!r} in {device_raw!r}')


def set_metadata(device, metadata):
    try:
        device.server_name = metadata['server_name']
    except Exception:
        logger.exception(f'Problem setting server_name from {metadata}')

    try:
        device.server_version = metadata['server_version']
    except Exception:
        logger.exception(f'Problem setting server_version from {metadata}')


def set_module_ver(device, metadata, module):
    try:
        device.module_version = metadata['workbenches'][module]['version']
    except Exception:
        logger.exception(f'Problem parsing module version from metadata {metadata}')


def parse_empty(value):
    if isinstance(value, (list, tuple)):
        return [x for x in [parse_empty(v) for v in value] if x not in consts.VALUES_EMPTY]

    if value in consts.VALUES_EMPTY:
        value = None
    return value


def parse_int(value):
    if isinstance(value, (list, tuple)):
        return parse_empty([parse_int(v) for v in value])

    value = parse_skip(value)

    if value is not None:
        try:
            return int(value)
        except Exception:
            msg = f'unable to convert {value!r} to int'
            logger.exception(msg)
    return None


def parse_str(value):
    if isinstance(value, (list, tuple)):
        return parse_empty([parse_str(v) for v in value])

    value = parse_skip(value)

    if value is not None:
        return str(value)
    return None


def parse_csv(value):
    value = parse_empty(value)

    if value is not None:
        try:
            value = str(value).strip().split(',')
            value = [x.strip() for x in value]
            return parse_empty(value)
        except Exception:
            msg = f'unable to convert csv {value!r} to list of str'
            logger.exception(msg)
    return []


def parse_float(value):
    if isinstance(value, (list, tuple)):
        return parse_empty([parse_float(v) for v in value])

    if is_float(value):
        return float(value)

    value = parse_skip(value)

    if value is not None:
        try:
            return float(value)
        except Exception:
            msg = f'unable to convert {value!r} to float'
            logger.exception(msg)
    return None


def parse_dt(value):
    if isinstance(value, (list, tuple)):
        return parse_empty([parse_dt(v) for v in value])

    if isinstance(value, datetime.datetime):
        return value

    value = parse_skip(value)

    if value is not None:
        try:
            return parse_date(value)
        except Exception:
            msg = f'unable to convert {value!r} to datetime'
            logger.exception(msg)
    return None


def parse_ip_network(value):
    if isinstance(value, (list, tuple)):
        return parse_empty([parse_ip(v) for v in value])

    value = parse_skip(value)

    if value is None:
        return None

    value = str(value).strip()

    try:
        return str(ipaddress.ip_network(value))
    except Exception:
        msg = f'unable to convert {value!r} to ip network'
        logger.exception(msg)
    return None


def parse_ip(value):
    if isinstance(value, (list, tuple)):
        return parse_empty([parse_ip(v) for v in value])

    value = parse_skip(value)

    if value is None:
        return None

    value = str(value).strip()

    has_dots = len(value.split('.')) >= 2
    has_colons = len(value.split(':')) >= 2

    if not any([has_dots, has_colons]):
        msg = f'has_dots {has_dots!r} and has_colons {has_colons!r} in ipaddress {value!r}, nulling out'
        logger.error(msg)
        return None

    try:
        return str(ipaddress.ip_address(value))
    except Exception:
        msg = f'unable to convert {value!r} to ipaddress'
        logger.exception(msg)
    return None


def parse_bool(value):
    if isinstance(value, (list, tuple)):
        return parse_empty([parse_bool(v) for v in value])

    check_value = str(value).lower().strip()

    if value in consts.YES_VALS or check_value in consts.YES_VALS:
        return True

    if value in consts.NO_VALS or check_value in consts.NO_VALS:
        return False

    value = parse_empty(value)

    if value is not None:
        msg = f'invalid boolean in value {value!r}'
        logger.error(msg)
    return None


def parse_mac(value):
    if isinstance(value, (list, tuple)):
        return parse_empty([parse_mac(v) for v in value])

    value = parse_skip(value)

    if value is None:
        return None

    value = str(value).replace('-', ':').strip().upper()

    if ':' not in value:
        msg = f'No "." in ipaddress {value!r}, nulling out'
        logger.error(msg)
        return None

    if not re.match(consts.MAC_RE, value, re.IGNORECASE):
        msg = f'invalid mac address in value {value!r}'
        logger.error(msg)
        return None
    return value


def parse_skip(value):
    if isinstance(value, (tuple, list)):
        return parse_empty([parse_skip(v) for v in value])

    if isinstance(value, dict):
        return value

    value = parse_empty(value)

    if value is None:
        return None

    for value_skip in consts.VALUES_SKIP:
        if re.search(value_skip, str(value).strip(), re.IGNORECASE):
            msg = f'SKIPPING VALUE {value!r} DUE TO REGEX MATCH OF {value_skip!r}'
            logger.debug(msg)
            return None
    return value


def parse_selects(question):
    try:
        return parse_empty([x.get('sensor', {}).get('name') for x in question.get('selects', [])])
    except Exception:
        logger.exception(f'Problem with parsing sensors from selects in question {question}')


def is_float(value):
    if isinstance(value, (list, tuple)):
        return any([is_float(v) for v in value])

    return isinstance(value, float) or ('.' in str(value) and str(value).strip().replace('.', '').isdigit())


def map_tanium_sq_value_type(key, name, value, value_type: str):
    """Value type mappings from tanium.

    Value type maps:

    Version            str -> version (JsonStringFormat.version)
    BESDate            str -> datetime
    IPAddress          str -> ip address
    WMIDate            str -> datetime
    NumericInteger     str -> int
    Hash               str
    String             str
    Numeric            str (number-LIKE, not necessarily an integer)
    TimeDiff           str (numeric + "Y|MO|W|D|H|M|S" i.e. 2 years, 3 months, 18 days, 4 hours, 22 minutes)
    DataSize           str (numeric + B|K|M|G|T i.e. 125MB, 23K, 34.2Gig)
    VariousDate        str (?)
    RegexMatch         str (?)
    LastOperatorType   str (?)
    """
    # logger.debug(f'mapping key {key!r} name {name!r} value {value!r} value_type {value_type!r}')
    value = parse_skip(value)
    value_type = str(value_type).lower()

    field_args = {'field_type': str, 'converter': None, 'json_format': None}

    if value_type == 'numericinteger':
        if is_float(value):
            field_args['field_type'] = float
            value = parse_float(value)
        else:
            field_args['field_type'] = int
            value = parse_int(value)
    elif value_type == 'version':
        field_args['json_format'] = JsonStringFormat.version
    elif value_type in ['besdate', 'wmidate']:
        value = parse_dt(value)
        field_args['field_type'] = datetime.datetime
    elif value_type == 'ipaddress' and ':' not in str(value):
        value = parse_ip(value)
        field_args['converter'] = format_ip
        field_args['json_format'] = JsonStringFormat.ip

    # logger.debug(f'mapped key {key!r} name {name!r} value {value!r} value_type {value_type!r} args {field_args!r}')
    return value, field_args


# pylint: disable=R0912
def put_tanium_sq_dynamic_field(entity: SmartJsonClass, name: str, value_map: dict, is_sub_field: bool = False):
    value = value_map.get('value', None)
    value_type = value_map.get('type', None)

    # type is a string populated by connection.py, so it should never be empty
    # value should always be either a non-empty list of strings or a non-empty string
    if not value_type or not isinstance(value_type, (list, tuple, str)):
        msg = f'Bad value_type {value_type!r} in name {name!r} with value {value!r}'
        logger.error(msg)
        return

    if is_sub_field:
        key = normalize_var_name(name).lower()
        title = name
        field_type = Field
    else:
        key = normalize_var_name(f'sensor_{name}').lower()
        title = f'Sensor: {name}'
        field_type = ListField

    if value_type == 'object':
        if not entity.does_field_exist(field_name=key):

            class SmartJsonClassInstance(SmartJsonClass):
                pass

            field_value = field_type(field_type=SmartJsonClassInstance, title=title)
            entity.declare_new_field(field_name=key, field_value=field_value)

        for item in value:
            # pylint: disable=W0212
            smartjsonclass_instance = entity.get_field_type(key)._type()

            for d_key, d_map in item.items():
                put_tanium_sq_dynamic_field(
                    entity=smartjsonclass_instance, name=d_key, value_map=d_map, is_sub_field=True,
                )

            entity[key].append(smartjsonclass_instance)
    else:
        field_args = {'field_type': str, 'converter': None, 'json_format': None}

        try:
            value, field_args = map_tanium_sq_value_type(key=key, name=name, value=value, value_type=value_type)
        except Exception:
            msg = f'Failed to map name {name!r} key {key!r} with value {value!r} of type {value_type!r}'
            logger.exception(msg)

        if not entity.does_field_exist(field_name=key):
            field_value = field_type(title=title, **field_args)
            entity.declare_new_field(field_name=key, field_value=field_value)

        if isinstance(value, (list, tuple)):
            for item in value:
                try:
                    entity[key].append(item)
                    # msg = f'Appended {item!r} name {name!r} key {key!r} value {value!r} type {value_type!r}'
                    # logger.exception(msg)
                except Exception:
                    msg = (
                        f'Failed to append {item!r} name {name!r} key {key!r} value {value!r} type {value_type!r} '
                        f'field_args {field_args!r}'
                    )
                    logger.exception(msg)
        else:
            try:
                entity[key] = value
                # msg = f'Set name {name!r} key {key!r} value {value!r} type {value_type!r}'
                # logger.exception(msg)
            except Exception:
                msg = (
                    f'Failed to set name {name!r} key {key!r} value {value!r} type {value_type!r} '
                    f'field_args {field_args!r}'
                )
                logger.exception(msg)
