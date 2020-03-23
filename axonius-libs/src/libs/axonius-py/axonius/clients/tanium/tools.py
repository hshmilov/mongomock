import datetime
import logging
import re

import ipaddress
from dateutil.tz import tzutc
from dateutil.parser import parse as parse_date
from axonius.devices.device_adapter import DeviceAdapterOS

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


def dt_now(utc=True):
    return datetime.datetime.now(tzutc()) if utc else datetime.datetime.now()


def dt_ago_mins(mins, inverse=False):
    now = dt_now()
    delta = datetime.timedelta(seconds=mins * 60)
    if inverse:
        return now + delta
    return now - delta


def dt_calc_mins(value, reverse=False, src=None):
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
        logger.exception(f'Failed to calculate mins {value} vs {now} src={src!r}')
        value = 0.0
    return 0.0 if value <= 0.0 else value


def dt_is_past(value, src=None):
    if not isinstance(value, datetime.datetime):
        value = parse_dt(value=value, src=src)

    if not is_empty(value=value):
        return value <= dt_now()
    return False


def set_csv(device, device_raw, key, attr, callback=None):
    value = device_raw.get(key)
    src = {'value': value, 'key': key, 'attr': attr}
    pvalues = parse_csv(value=value, src=src)

    if not is_empty_list(value=pvalues):
        try:
            try:
                if callback and callable(callback):
                    pvalues = callback(value=pvalues, src=src)
            except Exception:
                logger.exception(f'Error in callback {callback} pvalues={pvalues!r} src={src!r}')

            attr_values = getattr(device, attr)
            # attr_values = device.get_field_safe(attr=attr) or []
            # pvalues = [x for x in pvalues if x not in attr_values]
            for pvalue in pvalues:
                if pvalue not in attr_values:
                    try:
                        attr_values.append(pvalue)
                    except Exception:
                        logger.exception(f'Problem adding pvalue={pvalue!r} src={src!r}')
        except Exception:
            logger.exception(f'Problem adding pvalues={pvalues!r} src={src!r}')


def set_bool(device, device_raw, key, attr):
    value = device_raw.get(key)
    src = {'value': value, 'key': key, 'attr': attr}
    pvalue = parse_bool(value=value, src=src)

    if not is_empty(value=pvalue):
        try:
            setattr(device, attr, pvalue)
        except Exception:
            logger.exception(f'Problem setting pvalue={pvalue!r} src={src!r}')


def set_int(device, device_raw, key, attr):
    value = device_raw.get(key)
    src = {'value': value, 'key': key, 'attr': attr}
    pvalue = parse_int(value=value, src=src)

    if not is_empty(value=pvalue):
        try:
            setattr(device, attr, pvalue)
        except Exception:
            logger.exception(f'Problem setting pvalue={pvalue!r} src={src!r}')


def joiner(*value, join='_'):
    return join.join([str(x) for x in value])


def set_str(device, device_raw, key, attr):
    value = device_raw.get(key)
    src = {'value': value, 'key': key, 'attr': attr}
    pvalue = parse_str(value=value, src=src)

    if not is_empty(value=pvalue):
        try:
            setattr(device, attr, pvalue)
        except Exception:
            logger.exception(f'Problem setting pvalue={pvalue!r} src={src!r}')


def set_ip(device, device_raw, key, attr):
    value = device_raw.get(key)
    src = {'value': value, 'key': key, 'attr': attr}
    pvalue = parse_ip(value=value, src=src)

    if not is_empty(value=pvalue):
        try:
            setattr(device, attr, pvalue)
        except Exception:
            logger.exception(f'Problem setting pvalue={pvalue!r} src={src!r}')


def set_dt(device, device_raw, key, attr):
    value = device_raw.get(key)
    src = {'value': value, 'key': key, 'attr': attr}
    pvalue = parse_dt(value=value, src=src)

    if not is_empty(value=value):
        try:
            setattr(device, attr, pvalue)
        except Exception:
            logger.exception(f'Problem setting pvalue={pvalue!r} src={src!r}')


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


def is_empty_vals(value):
    return all([is_empty(value=x) for x in value.values()])


def is_empty_list(value):
    return all([is_empty(value=x) for x in value])


def is_empty(value):
    return value in consts.VALUES_EMPTY


def parse_empty(value):
    if isinstance(value, (list, tuple)):
        return [x for x in [parse_empty(value=v) for v in value] if x not in consts.VALUES_EMPTY]

    if is_empty(value=value):
        value = None
    return value


def parse_int(value, src=None):
    if isinstance(value, (list, tuple)):
        return parse_empty(value=[parse_int(value=v, src=src) for v in value])

    value = parse_skip(value=value, src=src)

    if value is not None:
        try:
            return int(value)
        except Exception:
            msg = f'unable to convert {value!r} to int src={src!r}'
            logger.exception(msg)
    return None


def parse_str(value, src=None):
    if isinstance(value, (list, tuple)):
        return parse_empty(value=[parse_str(value=v, src=src) for v in value])

    value = parse_skip(value=value, src=src)

    if value is not None:
        return str(value)
    return None


def parse_csv(value, split=',', src=None):
    value = parse_str(value=value, src=src)

    if value is not None:
        try:
            value = str(value).strip().split(split)
            value = [x.strip() for x in value]
            return parse_empty(value=value)
        except Exception:
            msg = f'unable to convert csv {value!r} to list of str src={src!r}'
            logger.exception(msg)
    return []


def parse_float(value, src=None):
    if isinstance(value, (list, tuple)):
        return parse_empty(value=[parse_float(value=v, src=src) for v in value])

    if is_float(value=value):
        return float(value)

    value = parse_skip(value=value, src=src)

    if value is not None:
        try:
            return float(value)
        except Exception:
            msg = f'unable to convert {value!r} to float src={src!r}'
            logger.exception(msg)
    return None


def parse_dt(value, src=None):
    if isinstance(value, (list, tuple)):
        return parse_empty(value=[parse_dt(value=v, src=src) for v in value])

    if isinstance(value, datetime.datetime):
        return value

    value = parse_skip(value=value, src=src)

    if value is not None:
        try:
            return parse_date(value)
        except Exception:
            msg = f'unable to convert {value!r} to datetime src={src!r}'
            logger.exception(msg)
    return None


def parse_ip_network(value, src=None):
    if isinstance(value, (list, tuple)):
        return parse_empty(value=[parse_ip(value=v, src=src) for v in value])

    value = parse_skip(value=value, src=src)

    if value is None:
        return None

    value = str(value).strip()

    try:
        return str(ipaddress.ip_network(value))
    except Exception:
        msg = f'unable to convert {value!r} to ip network src={src!r}'
        logger.exception(msg)
    return None


def parse_ip(value, src=None):
    if isinstance(value, (list, tuple)):
        return parse_empty(value=[parse_ip(value=v, src=src) for v in value])

    value = parse_skip(value=value, src=src)

    if value is None:
        return None

    value = str(value).strip()
    value = value.split('%')[0].strip()
    value = value.split('/')[0].strip()

    has_dots = len(value.split('.')) >= 2
    has_colons = len(value.split(':')) >= 2

    if not any([has_dots, has_colons]):
        msg = f'has_dots {has_dots!r} and has_colons {has_colons!r} in ipaddress {value!r}, nulling out src={src!r}'
        logger.error(msg)
        return None

    try:
        return str(ipaddress.ip_address(value))
    except Exception:
        msg = f'unable to convert {value!r} to ipaddress, src={src!r}'
        logger.exception(msg)
    return None


def parse_bool(value, src=None):
    if isinstance(value, (list, tuple)):
        return parse_empty(value=[parse_bool(value=v, src=src) for v in value])

    check_value = str(value).lower().strip()

    if value in consts.YES_VALS or check_value in consts.YES_VALS:
        return True

    if value in consts.NO_VALS or check_value in consts.NO_VALS:
        return False

    value = parse_empty(value=value)

    if value is not None:
        msg = f'invalid boolean in value {value!r} src={src!r}'
        logger.error(msg)
    return None


def parse_mac(value, src=None):
    if isinstance(value, (list, tuple)):
        return parse_empty(value=[parse_mac(value=v, src=src) for v in value])

    value = parse_skip(value=value, src=src)

    if value is None:
        return None

    value = str(value).replace('-', ':').strip().upper()

    if ':' not in value:
        msg = f'No "." in ipaddress {value!r}, nulling out src={src!r}'
        logger.error(msg)
        return None

    if not re.match(consts.MAC_RE, value, re.IGNORECASE):
        msg = f'invalid mac address in value {value!r} src={src!r}'
        logger.error(msg)
        return None
    return value


def parse_skip(value, src=None):
    if isinstance(value, (tuple, list)):
        return parse_empty(value=[parse_skip(value=v, src=src) for v in value])

    if isinstance(value, dict):
        return value

    value = parse_empty(value=value)

    if value is None:
        return None

    for value_skip in consts.VALUES_SKIP:
        if value_skip.search(str(value).strip()):
            if consts.DEBUG_SKIP:
                msg = f'SKIPPING VALUE {value!r} DUE TO REGEX MATCH OF {value_skip} src={src!r}'
                logger.debug(msg)
            return None
    return value


def parse_selects(question):
    try:
        return parse_empty(value=[x.get('sensor', {}).get('name') for x in question.get('selects', [])])
    except Exception:
        logger.exception(f'Problem with parsing sensors from selects in question {question}')


def is_float(value):
    if isinstance(value, (list, tuple)):
        return any([is_float(v) for v in value])

    return isinstance(value, float) or ('.' in str(value) and str(value).strip().replace('.', '').isdigit())


def handle_key_attr_map(self, device, device_raw):
    for key, attr, method in self.key_attr_map:
        if not key or key in device_raw:
            try:
                method(device=device, device_raw=device_raw, key=key, attr=attr)
            except Exception:
                logger.exception(f'ERROR key {key!r} attr {attr!r} method {method!r} in {device_raw!r}')
        else:
            self.missing_keys = getattr(self, 'missing_keys', [])
            if key not in self.missing_keys:
                logger.error(f'Key {key!r} for device attr {attr!r} not found in raw device {list(device_raw)}')
                self.missing_keys.append(key)
            continue


def ensure_os(device):
    if device.get_field_safe(attr='os') is None:
        device.os = DeviceAdapterOS()


def calc_gb(value, src=None):
    value = parse_int(value=value, src=src)
    if value is not None:
        try:
            return value / (1024 ** 3)
        except Exception:
            logger.exception(f'unable to convert bytes {value!r} to gb src={src!r}')
    return None
