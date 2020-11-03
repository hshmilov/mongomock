from axonius.consts.adapter_consts import VAULT_PROVIDER
from axonius.consts.gui_consts import (LOGGED_IN_MARKER_PATH, UNCHANGED_MAGIC_FOR_GUI, PREDEFINED_FIELD,
                                       IS_AXONIUS_ROLE, IS_API_USER, LAST_UPDATED_FIELD)
from gui.logic.db_helpers import encode_datetime


def has_customer_login_happened():
    return LOGGED_IN_MARKER_PATH.is_file()


# this is a magic that means that the value shouldn't be changed, i.e. when used by passwords
# that aren't sent to the client from the server and if they aren't modified we need to not change them

def clear_passwords_fields(data, schema):
    """
    Assumes "data" is organized according to schema and nullifies all password fields
    """
    if not data:
        return data
    if schema.get('format') == 'password' and not (isinstance(data, dict) and data.get('type') == VAULT_PROVIDER):
        return UNCHANGED_MAGIC_FOR_GUI
    if schema['type'] == 'array':
        items = schema['items']
        if isinstance(items, list):
            for item in items:
                if item['name'] in data:
                    data[item['name']] = clear_passwords_fields(data[item['name']], item)
        elif isinstance(items, dict) and isinstance(data, list):
            for index, data_item in enumerate(data):
                data[index] = clear_passwords_fields(data_item, items)
        else:
            raise TypeError(f'Schema array expects {type(items)} but data is {type(data)}')
        return data
    return data


def refill_passwords_fields(data, data_from_db):
    """
    Uses `data_from_db` to fill out "incomplete" (i.e. "unchanged") data in `data`
    """
    if data == UNCHANGED_MAGIC_FOR_GUI:
        return data_from_db
    if data_from_db is None:
        return data
    if isinstance(data, dict):
        for key in data.keys():
            if key in data_from_db:
                data[key] = refill_passwords_fields(data[key], data_from_db[key])
        return data

    return data


def has_unchanged_password_value(value: object) -> bool:
    """
    Check if the current field value has an unchanged password or contains an inner unchanged password
    :param value: the value of the checked field or the dict to check inside of
    :return: True if the data contains an unchanged password
    """
    if value == UNCHANGED_MAGIC_FOR_GUI:
        return True
    if isinstance(value, dict):
        for key in value.keys():
            if has_unchanged_password_value(value[key]):
                return True
    return False


def remove_password_fields(schema, data: dict):
    """
    :param schema: schema used to look for password field type
    :param data: data from which password field will be removed
    :return: data object
    """
    if not isinstance(data, dict):
        raise ValueError('data type must be a dict ')

    if schema['type'] == 'array':
        for schema_item in schema.get('items'):
            if isinstance(schema_item, dict):
                if schema_item.get('type') == 'array' and data.get(schema_item['name']):
                    remove_password_fields(schema_item, data.get(schema_item['name']))
                if schema_item.get('format') == 'password':
                    data.pop(schema_item['name'], None)
    else:
        if schema.get('format') == 'password':
            data.pop(schema['name'], None)


def get_user_for_session(user_from_db, role_from_db, is_api_user: bool = False):
    user = dict()
    user['_id'] = str(user_from_db['_id'])
    user['user_name'] = user_from_db['user_name']
    user['source'] = user_from_db['source']
    user['role_id'] = str(user_from_db['role_id'])
    user['role_name'] = role_from_db['name']
    user[PREDEFINED_FIELD] = role_from_db.get(PREDEFINED_FIELD)
    user[IS_AXONIUS_ROLE] = role_from_db.get(IS_AXONIUS_ROLE)
    user[IS_API_USER] = is_api_user
    user[LAST_UPDATED_FIELD] = encode_datetime(max([user_from_db.get(LAST_UPDATED_FIELD),
                                                    role_from_db.get(LAST_UPDATED_FIELD)]))
    return user
