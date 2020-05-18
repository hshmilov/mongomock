from axonius.consts.adapter_consts import VAULT_PROVIDER
from axonius.consts.gui_consts import (LOGGED_IN_MARKER_PATH, UNCHANGED_MAGIC_FOR_GUI)


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
            for item in schema['items']:
                if item['name'] in data:
                    data[item['name']] = clear_passwords_fields(data[item['name']], item)
        elif isinstance(items, dict):
            for index, date_item in enumerate(data):
                data[index] = clear_passwords_fields(data[index], items)
        else:
            raise TypeError('Weird schema')
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
