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


def to_json(value):
    return json.dumps(value, default=default_with_generators)


def from_json(json_string):
    return json.loads(json_string, object_hook=lambda dct: object_hook(dct, json_options))


class JsonFieldError(Exception):
    ''' Exception for json validation errors '''
    pass


def validate(fields, json):
    ''' Given a structure named field validate that you can reach each field in the json.
    :raise: JsonFieldError if it fields isn't reachable '''
    if isinstance(fields, dict):
        if not isinstance(json, dict):
            raise JsonFieldError(f"Json dosen't conatin {fields}")

        for key, value in fields.items():
            if key not in json:
                raise JsonFieldError(f'Json is missing {key}')
            return validate(value, json[key])

    if isinstance(fields, list):
        if not isinstance(json, list):
            raise JsonFieldError(f'Json is not iterable')

        for subdict in json:
            for item in fields:
                return validate(item, subdict)

    if not isinstance(json, dict):
        raise JsonFieldError(f"Json dosen't conatin {fields}")

    if fields not in json.keys():
        raise JsonFieldError(f'Json missing is missing {fields}')
