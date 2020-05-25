# pylint: disable=protected-access
import datetime
import logging

from axonius.fields import ListField, Field
from axonius.smart_json_class import SmartJsonClass
from axonius.utils.parsing import normalize_var_name

EMPTY_VARS = (None, [], {}, '')  # for handling non-null "Falsey" data

logger = logging.getLogger(f'axonius.{__name__}')


# pylint: disable=consider-merging-isinstance
def get_entity_new_field(title: str, value, allow_empty=False):
    if value in EMPTY_VARS:
        if not allow_empty:
            return None
        field_type = type(value)
        # fallthrough all the way to Field creation

    elif isinstance(value, list):
        field_type = get_entity_new_field(title, value[0])._type
        return ListField(field_type, title)

    elif isinstance(value, dict):
        class SmartJsonClassInstance(SmartJsonClass):
            pass
        field_type = SmartJsonClassInstance
    elif isinstance(value, bool):
        field_type = bool
    elif isinstance(value, datetime.datetime) or isinstance(value, datetime.date):
        field_type = datetime.datetime
    elif isinstance(value, float):
        field_type = float
    elif isinstance(value, int):
        field_type = int
    else:
        field_type = str

    return Field(field_type, title)


# pylint: disable=too-many-branches
def put_dynamic_field(entity: SmartJsonClass, key: str, value, title: str, allow_empty=False):
    # don't just `if not value` in case value is a false boolean, for example!
    if (not allow_empty) and (value in EMPTY_VARS):
        return
    key = normalize_var_name(key)
    if not entity.does_field_exist(key):
        entity.declare_new_field(key, get_entity_new_field(title, value, allow_empty=allow_empty))

    if value in EMPTY_VARS:
        # If we reached here it means we allow empty values
        entity[key] = value
        return

    if isinstance(value, dict):
        smartjsonclass_instance = entity.get_field_type(key)._type()
        for d_key, d_value in value.items():
            put_dynamic_field(smartjsonclass_instance, d_key, d_value, d_key)

        entity[key] = smartjsonclass_instance

    elif isinstance(value, list):
        smartjsonclass_class = entity.get_field_type(key)._type
        for item in value:
            if isinstance(item, dict):
                smartjsonclass_instance = smartjsonclass_class()
                for d_key, d_value in item.items():
                    put_dynamic_field(smartjsonclass_instance, d_key, d_value, d_key.title())

                entity[key].append(smartjsonclass_instance)
            else:
                entity[key].append(item)

    elif isinstance(value, (int, float, bool, datetime.datetime)):
        entity[key] = value
    elif isinstance(value, datetime.date):
        entity[key] = datetime.datetime.combine(value, datetime.datetime.min.time())
    else:
        entity[key] = str(value)
