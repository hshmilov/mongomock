import logging
logger = logging.getLogger(f'axonius.{__name__}')

from bson.json_util import JSONOptions, JSONMode, DatetimeRepresentation, default, object_hook
from collections.abc import KeysView, ValuesView, ItemsView
import json
from types import GeneratorType


# we use special JSONOptions with ISO8601 to fix serializing of datetime.datetime(9999, 12, 31, 23, 59, 59, 999999)
json_options = JSONOptions(json_mode=JSONMode.LEGACY, datetime_representation=DatetimeRepresentation.ISO8601)


def default_with_generators(obj):
    if isinstance(obj, (GeneratorType, KeysView, ValuesView, ItemsView)):
        return [to_json(item) for item in obj]
    return default(obj, json_options)


def to_json(value, **kwargs):
    return json.dumps(value, default=default_with_generators, **kwargs)


def from_json(json_string):
    return json.loads(json_string, object_hook=lambda dct: object_hook(dct, json_options))


def _is_valid(json, fields) -> bool:
    ''' Given a structure named field validate that you can reach each field in the json.
    json field represnt the json that we want to validate.
    fields represent the fields that are required to be in the json.
    fields may be single string, or complex dict with sublist.
    :return: is the json valid
    example:
        _is_valid(json, 'asdf') - will validate that json contains the field 'asdf'.
        _is_valid(json, {'asdf' : 'qwer'}) - will validate that json['asdf']['qwer'] is valid.
        _is_valid(json, {'asdf' : ['qwer']}) - will validate that json['asdf'] contains list of dicts, 
        and that for each dict the key 'qwer' is valid.
    '''

    if isinstance(fields, dict):
        if not isinstance(json, dict):
            return False

        for key, value in fields.items():
            if key not in json:
                return False
            return _is_valid(json[key], value)

    if isinstance(fields, list):
        if not isinstance(json, list):
            return False

        for subdict in json:
            for item in fields:
                return _is_valid(subdict, item)

    if not isinstance(json, dict):
        return False

    if fields not in json.keys():
        return False
    return True


def is_valid(json, *fields):
    ''' high level wrapper for _is_valid '''
    try:
        return all(map(lambda field: _is_valid(json, field), fields))
    except Exception:
        logger.warning('Exception while validating json')
        return False
