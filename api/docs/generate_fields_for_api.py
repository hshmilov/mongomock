#!/usr/bin/env python3
import pprint

from axonius.devices.device_adapter import DeviceAdapter
from axonius.users.user_adapter import UserAdapter
from axonius.utils.gui_helpers import flatten_fields


def main():
    device_adapter_fields = flatten_fields(DeviceAdapter.get_fields_info(), 'specific_data.data', ['scanner'])
    user_adapter_fields = flatten_fields(UserAdapter.get_fields_info(), 'specific_data.data', ['scanner'])
    with open('/tmp/device_fields.py', 'w') as file_:
        file_.write(pprint.pformat(device_adapter_fields))

    with open('/tmp/user_fields.py', 'w') as file_:
        file_.write(pprint.pformat(user_adapter_fields))


if __name__ == '__main__':
    main()
