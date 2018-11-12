#!/usr/bin/env python3
"""Simple script to create new adapter.
Some fields must be set by the user and will be set to "AUTOADAPTER" placeholder
you should use `grep -R "AUTOADAPTER . | grep -v create_adapter.py` in order to find all placeholders

Basically we do the following things:

-> add description to plugins/gui/frontend/src/constants/plugin_meta.js
    -> AUTOADAPTER - add description

-> create plugins/gui/frontend/src/assets/images/logos/<adapter_name>_adapter.png
    -> AUTOADAPTER - replace this line with logo

-> mkdir adapters/<adapter_name>_adapter
    -> create adapters/<adapter_name>_adapter/__init__.py
    -> create adapters/<adapter_name>_adapter/config.ini
    -> create adapters/<adapter_name>_adapter/service.py
        -> AUTOADAPTER - implement schema, fetch devices, etc
    -> create adapters/<adapter_name>_adapter/client_id.py
        -> AUTOADAPTER - implement get_client_id

-> create testing/test_credentials/test_<adapter_name>_credentials.py
    -> AUTOADAPTER - add client_details example
    -> AUTOADAPTER - set to device id that will be feteched using client_details

-> create testing/services/adapters/<adapter_name>_service.py

-> create testing/parallel_tests/test_<adapter_name>.py

-> add port to testing/services/ports.py
"""

import re
import os
import argparse
from collections import OrderedDict


class ValidateError(Exception):
    ''' Validation exception for validators '''
    pass


class ActionError(Exception):
    ''' Action failure exception '''
    pass


def get_cortex_dir() -> str:
    ''' Returns the relative path to cortex repo root directory'''
    return os.path.relpath(os.path.join(os.path.dirname(__file__), '..', '..', '..'))


def capitalize_adapter_name(adapter_name: str) -> str:
    ''' Returns captialize adapter_name '''
    return ''.join(map(str.capitalize, adapter_name.split('_')))


def get_action_table(adapter_name: str) -> OrderedDict:
    ''' returns table for each adapter file -> (validator, action) '''

    return OrderedDict({
        f'plugins/gui/frontend/src/constants/plugin_meta.js': (description_validator, description_action),
        f'axonius-libs/src/libs/axonius-py/axonius/assets/logos/{adapter_name}_adapter.png': (not_exists_validator, image_action),
        f'adapters/{adapter_name}_adapter': (not_exists_validator, adapter_dir_action),
        f'adapters/{adapter_name}_adapter/__init__.py': (not_exists_validator, adapter_init_action),
        f'adapters/{adapter_name}_adapter/config.ini': (not_exists_validator, config_ini_action),
        f'adapters/{adapter_name}_adapter/service.py': (not_exists_validator, service_action),
        f'adapters/{adapter_name}_adapter/client_id.py': (not_exists_validator, client_id_action),
        f'testing/test_credentials/test_{adapter_name}_credentials.py': (not_exists_validator, creds_action),
        f'testing/services/adapters/{adapter_name}_service.py': (not_exists_validator, test_service_action),
        f'testing/parallel_tests/test_{adapter_name}.py': (not_exists_validator, parallel_tests_action),
        f'testing/services/ports.py': (port_validator, ports_action),
    })

# Validators callbacks for table,  each one gets 2 arguments filename, and adapter_name


def not_exists_validator(filename: str, _):
    ''' validate that filename isn't exists in cortex dir
        :raise: ValidateError on failure'''

    if os.path.exists(filename):
        raise ValidateError(f'File {filename} already exists')


def description_validator(filename: str, adapter_name: str):
    ''' Validate that there is no description for the given adapter_name
        :raise: ValidateError on failure'''

    file_data = open(filename, 'r', encoding='utf-8').read()
    if f'{adapter_name}_adapter' in file_data:
        raise ValidateError(f'Description for "{adapter_name}" already defined in {filename}')


def port_validator(filename: str, adapter_name: str):
    ''' Validate that there is no port for the given adapter_name
        :raise: ValidateError on failure'''

    file_data = open(filename, 'r', encoding='utf-8').read()
    if f'{adapter_name}_adapter' in file_data:
        raise ValidateError(f'port for "{adapter_name}" already defined in {filename}')


# Actions callbacks for table,  each one gets 2 arguments filename, and adapter_name

def description_action(filename: str, adapter_name: str):
    ''' Appends description to the description file '''
    new_description = "    %s_adapter: {\n        title: 'AUTOADAPTER',\n        description: 'AUTOADAPTER'\n    },\n" % (
        adapter_name, )

    lines = open(filename, 'r', encoding='utf-8').readlines()

    for i, line in enumerate(lines):
        # Start of dict should be 'pluginMeta = {dict}'
        if 'pluginMeta =' in line:
            # Found dict, now insert AUTOADAPTER placeholder
            lines.insert(i + 1, new_description)
            data = ''.join(lines)

            with open(filename, 'w') as file_:
                file_.write(data)
            break
    else:
        raise ActionError('Unable to find PluginMeta')


def image_action(filename: str, adapter_name: str):
    ''' Add placeholder for image file '''

    placeholder = f"AUTOADAPTER - replace this file with logo for {adapter_name}"

    with open(filename, 'w') as file_:
        file_.write(placeholder)


def adapter_dir_action(filename: str, _):
    ''' Create the base directory for the adapter '''
    os.makedirs(filename)


def adapter_init_action(filename: str, _):
    ''' Create __init__.py file for the adapter '''
    open(filename, 'w').close()


def config_ini_action(filename: str, _):
    ''' Create config.ini file for the adapter '''
    template = \
        """[DEFAULT]
version = %%version%%

[DEBUG]
host = 0.0.0.0
port = 443
core_address = https://core.axonius.local"""

    with open(filename, 'w') as file_:
        file_.write(template)


def service_action(filename: str, adapter_name: str):
    ''' Create service.py file for the adapter '''
    template = \
        """
import logging

from %s_adapter.client_id import get_client_id
from axonius.adapter_base import AdapterBase, AdapterProperty
from axonius.adapter_exceptions import ClientConnectionException
from axonius.devices.device_adapter import DeviceAdapter
from axonius.utils.files import get_local_config_file

logger = logging.getLogger(f'axonius.{__name__}')


class %sAdapter(AdapterBase):
    class MyDeviceAdapter(DeviceAdapter):
        pass

    def __init__(self):
        super().__init__(get_local_config_file(__file__))

    @staticmethod
    def _get_client_id(client_config):
        return get_client_id(client_config)

    def _test_reachability(self, client_config):
        'AUTOADAPTER - add code that tests client reachability'
        raise NotImplementedError()

    def _connect_client(self, client_config):
        client_id = self._get_client_id(client_config)        
        try:
            'AUTOADAPTER - add code that returns client'
        except Exception as e:
            logger.error(f'Failed to connect to client {client_id}')
            raise ClientConnectionException(str(e))

    def _query_devices_by_client(self, client_name, client_data):
        'AUTOADAPTER - add code that returns (or yields) raw_data list'

    def _clients_schema(self):
        return {
            'items': [
                'AUTOADAPTER - add items'
            ],
            'required': [
            ],
            'type': 'array'
        }

    def create_device(self, raw_device_data):
        device = self._new_device_adapter()
        'AUTOADAPTER - create device'
        return device

    def _parse_raw_data(self, devices_raw_data):
        for raw_device_data in iter(devices_raw_data):
            try:
                device = self.create_device(raw_device_data)
                yield device
            except Exception:
                logger.exception(f'Got exception for raw_device_data: {raw_device_data}')

    @classmethod
    def adapter_properties(cls):
        'AUTOADAPTER - check if you need to add other properties'
        return [AdapterProperty.Assets]
""" % (adapter_name, capitalize_adapter_name(adapter_name))
    with open(filename, 'w') as file_:
        file_.write(template)


def client_id_action(filename: str, _):
    template = \
        """def get_client_id(client_config):
    return 'AUTOADAPTER - you should return the id (for example: client_config["hostname"])'
"""
    with open(filename, 'w') as file_:
        file_.write(template)


def creds_action(filename: str, _):
    ''' Create creds file'''
    template = \
        """client_details = {
} # AUTOADAPTER - insert client information to test

SOME_DEVICE_ID = 'AUTOADAPTER - give one device_id that should return from the above client'
"""
    with open(filename, 'w') as file_:
        file_.write(template)


def test_service_action(filename: str, adapter_name: str):
    ''' Create tests service.py file'''
    template = \
        f"""import pytest

from services.plugin_service import AdapterService
from services.simple_fixture import initialize_fixture


class {capitalize_adapter_name(adapter_name)}Service(AdapterService):
    def __init__(self):
        super().__init__('{adapter_name.replace('_', '-')}')


@pytest.fixture(scope='module', autouse=True)
def {adapter_name}_fixture(request):
    service = {capitalize_adapter_name(adapter_name)}Service()
    initialize_fixture(request, service)
    return service
"""
    with open(filename, 'w') as file_:
        file_.write(template)


def parallel_tests_action(filename: str, adapter_name: str):
    ''' Create parallel tests file'''
    template = \
        f"""# pylint: disable=unused-import
# pylint: disable=abstract-method
from services.adapters.{adapter_name}_service import {capitalize_adapter_name(adapter_name)}Service, {adapter_name}_fixture
from test_helpers.adapter_test_base import AdapterTestBase
from test_credentials.test_{adapter_name}_credentials import client_details, SOME_DEVICE_ID
from {adapter_name}_adapter.client_id import get_client_id


class Test{capitalize_adapter_name(adapter_name)}Adapter(AdapterTestBase):
    @property
    def adapter_service(self):
        return {capitalize_adapter_name(adapter_name)}Service()

    @property
    def some_client_id(self):
        return get_client_id(client_details)

    @property
    def some_client_details(self):
        return client_details

    @property
    def some_device_id(self):
        return SOME_DEVICE_ID
"""
    with open(filename, 'w') as file_:
        file_.write(template)


def ports_action(filename: str, adapter_name: str):
    ''' Appends port to the ports file '''
    regex = r".*'(.*?)':.*(\D.*?),.*"

    lines = open(filename, 'r', encoding='utf-8').readlines()
    mongoline = None
    highest_port = 0

    for i, line in enumerate(lines):
        match = re.match(regex, line)
        if not match:
            continue
        if match.groups()[0] == 'mongo':
            mongoline = i
        else:
            highest_port = max(highest_port, int(match.groups()[1]))

    if not mongoline:
        raise ActionError('Unable to find mongoline')
    if highest_port == 0:
        raise ActionError('Unable to find highst port')

    template = f"    '{adapter_name.replace('_', '-')}-adapter':".ljust(40) + f"{highest_port+1},\n"
    lines.insert(mongoline, template)
    data = ''.join(lines)

    with open(filename, 'w') as file_:
        file_.write(data)


class ArgumentParser(argparse.ArgumentParser):
    """ Argumentparser for the script """

    def __init__(self, *args, **kwargs):
        super().__init__(*args, **kwargs)
        self.formatter_class = argparse.RawDescriptionHelpFormatter
        self.description = """Example:
  %(prog)s github
  %(prog)s cisco_prime"""
        self.add_argument("name", help="The new adapter name")

    def parse_args(self, args=None, namespace=None):
        args = super().parse_args(args, namespace)

        # Adapter name must makes sense, we dont want ../../coolAdpter1337
        # as adapter name....
        if not (args.name.isidentifier() or args.name.isalnum()):
            self.error('Invalid adapter name given')

        return args


def validate_files(adapter_name: str):
    """ Validate that the filesystem doesn't contains any file that we
    are about to create. """

    for filename, (validator, _) in get_action_table(adapter_name).items():
        filename = os.path.join(get_cortex_dir(), filename)
        validator(filename, adapter_name)


def create_files(adapter_name: str):
    """ create needed files """

    for filename, (_, action) in get_action_table(adapter_name).items():
        filename = os.path.join(get_cortex_dir(), filename)
        action(filename, adapter_name)


def main():
    """ Main function for the script """

    args = ArgumentParser().parse_args()
    adapter_name = args.name

    validate_files(adapter_name)
    create_files(adapter_name)


if __name__ == "__main__":
    main()
