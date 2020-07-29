#!/usr/bin/env python3
"""Simple script to create new adapter.
Some fields must be set by the user and will be set to "AUTOADAPTER" placeholder
you should use `grep -R "AUTOADAPTER . | grep -v create_adapter.py` in order to find all placeholders

Basically we do the following things

-> add description to plugins/gui/frontend/src/constants/plugin_meta.js
    -> AUTOADAPTER - add description

-> create axonius-libs/src/libs/axonius-py/axonius/assets/logos/adapters/<adapter_name>_adapter.png
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
# pylint:disable=invalid-string-quote,invalid-name
import json
import re
import os
import shutil
import argparse
from enum import Enum
from collections import OrderedDict


class AdapterTypes(Enum):
    SQL = 'sql'
    FILE = 'file'
    REST = 'rest'


# pylint:disable=unnecessary-pass
class ValidateError(Exception):
    """ Validation exception for validators """
    pass


# pylint:disable=unnecessary-pass
class ActionError(Exception):
    """ Action failure exception """
    pass


def get_cortex_dir() -> str:
    """ Returns the relative path to cortex repo root directory """

    return os.path.relpath(os.path.join(os.path.dirname(__file__), '..', '..', '..'))


def capitalize_adapter_name(adapter_name: str) -> str:
    """ Returns capitalize adapter_name """

    return ''.join(map(str.capitalize, adapter_name.split('_')))


def get_action_table(adapter_name: str) -> OrderedDict:
    """ returns table for each adapter file -> (validator, action) """

    return OrderedDict({
        f'plugins/gui/frontend/src/constants/plugin_meta.json': (description_validator, description_action),
        f'axonius-libs/src/libs/axonius-py/axonius/assets/logos/adapters/{adapter_name}_adapter.png':
            (not_exists_validator, image_action),
        f'adapters/{adapter_name}_adapter': (not_exists_validator, adapter_dir_action),
        f'adapters/{adapter_name}_adapter/__init__.py': (not_exists_validator, adapter_init_action),
        f'adapters/{adapter_name}_adapter/config.ini': (not_exists_validator, config_ini_action),
        f'adapters/{adapter_name}_adapter/service.py': (not_exists_validator, service_action),
        f'adapters/{adapter_name}_adapter/client_id.py': (not_exists_validator, client_id_action),
        f'adapters/{adapter_name}_adapter/consts.py': (not_exists_validator, consts_action),
        f'adapters/{adapter_name}_adapter/connection.py': (not_exists_validator, connection_action),
        f'adapters/{adapter_name}_adapter/structures.py': (not_exists_validator, structures_action),
        f'testing/test_credentials/test_{adapter_name}_credentials.py': (not_exists_validator, creds_action),
        f'testing/services/adapters/{adapter_name}_service.py': (not_exists_validator, test_service_action),
        f'testing/parallel_tests/test_{adapter_name}.py': (not_exists_validator, parallel_tests_action),
        f'testing/services/ports.py': (port_validator, ports_action),
    })


# Validators callbacks for table,  each one gets 2 arguments filename, adapter_name


def not_exists_validator(filename: str, *args):
    """ validate that filename isn't exists in cortex dir
        :raise: ValidateError on failure """

    if os.path.exists(filename):
        raise ValidateError(f'File {filename} already exists')


def description_validator(filename: str, adapter_name: str):
    """ Validate that there is no description for the given adapter_name
        :raise: ValidateError on failure """

    description_dict = json.loads(open(filename, 'r', encoding='utf-8').read())
    if f'{adapter_name}_adapter' in description_dict:
        raise ValidateError(f'Description for "{adapter_name}" already defined in {filename}')


def port_validator(filename: str, adapter_name: str):
    """ Validate that there is no port for the given adapter_name
        :raise: ValidateError on failure """

    file_data = open(filename, 'r', encoding='utf-8').read()
    if f'{adapter_name}_adapter' in file_data:
        raise ValidateError(f'port for "{adapter_name}" already defined in {filename}')


# Actions callbacks for table,  each one gets 3 arguments filename, adapter_name, adapter_type

def description_action(filename: str, adapter_name: str, *args):
    """ Appends description to the description file """

    description_dict = json.loads(open(filename, 'r', encoding='utf-8').read())
    adapter_key = f'{adapter_name}_adapter'
    # description_validator assures adapter_key is not present in description_dict beforehand
    description_dict[adapter_key] = {
        'title': 'AUTOADAPTER',
        'link': 'AUTOADAPTER',
        'description': 'AUTOADAPTER'
    }
    with open(filename, 'w', encoding='utf-8') as file_:
        file_.write(json.dumps(description_dict, indent=2, ensure_ascii=False))


def image_action(filename: str, adapter_name: str, *args):
    """ Add placeholder for image file """

    placeholder = f"AUTOADAPTER - replace this file with logo for {adapter_name}"

    with open(filename, 'w') as file_:
        file_.write(placeholder)


def adapter_dir_action(filename: str, *args):
    """ Create the base directory for the adapter """

    os.makedirs(filename)


def adapter_init_action(filename: str, *args):
    """ Create __init__.py file for the adapter """

    open(filename, 'w').close()


def config_ini_action(filename: str, *args):
    """ Create config.ini file for the adapter """

    template = \
        '''[DEFAULT]
version = %%version%%

[DEBUG]
host = 0.0.0.0
port = 443
core_address = https://core.axonius.local'''

    with open(filename, 'w') as file_:
        file_.write(template)


def service_action(filename: str, adapter_name: str, adapter_type: str):
    """ Create service.py file for the adapter """

    template = open(os.path.join(get_cortex_dir(), f'devops/scripts/automate_dev/{adapter_type}_service.py.template'),
                    'r', encoding='utf-8').read()
    capital_seperated = ' '.join(map(str.capitalize, adapter_name.split('_')))
    template = template.format(adapter_name=adapter_name, capital_adapter_name=capitalize_adapter_name(adapter_name),
                               only_capital_adapter_name=adapter_name.upper(), seperated_capital_adapter_name=capital_seperated)
    with open(filename, 'w') as file_:
        file_.write(template)


def connection_action(filename: str, adapter_name: str, *args):
    """ Create service.py file for the adapter """

    template = open(os.path.join(get_cortex_dir(), 'devops/scripts/automate_dev/connection.py.template'),
                    'r', encoding='utf-8').read()
    template = template.format(capital_adapter_name=capitalize_adapter_name(adapter_name))
    with open(filename, 'w') as file_:
        file_.write(template)


def structures_action(filename: str, adapter_name: str, *args):
    """ Create structure.py file for the adapter """

    capital_adapter_name = capitalize_adapter_name(adapter_name)
    template = f'''import datetime

from axonius.fields import Field, ListField
from axonius.users.user_adapter import UserAdapter
from axonius.devices.device_adapter import DeviceAdapter

# TODO: implement
class {capital_adapter_name}DeviceInstance(DeviceAdapter):
    # AUTOADAPTER
    pass

# TODO: implement
class {capital_adapter_name}UserInstance(UserAdapter):
    # AUTOADAPTER
    pass
'''
    with open(filename, 'w') as file_:
        file_.write(template)


def client_id_action(filename: str, *args):
    template = \
        '''# TODO: implement
def get_client_id(client_config):
    # AUTOADAPTER
    return client_config['domain']
'''
    with open(filename, 'w') as file_:
        file_.write(template)


def consts_action(filename: str, adapter_name: str, adapter_type: str):
    capital_adapter_name = adapter_name.upper()
    if adapter_type == AdapterTypes.SQL.value:
        template = \
            f'''USER = 'username'
PASSWORD = 'password'
{capital_adapter_name}_HOST = 'server'
{capital_adapter_name}_PORT = 'port'
DEFAULT_{capital_adapter_name}_PORT = 1433
{capital_adapter_name}_DATABASE = 'database'
DEFAULT_{capital_adapter_name}_DATABASE = 'CIS_CMDB'
DRIVER = 'driver'
DEVICES_FETECHED_AT_A_TIME = 'devices_fetched_at_a_time'
{capital_adapter_name}_QUERY = 'Select * from Computers'
'''
    else:
        template = \
            '''DEVICE_PER_PAGE = 200
MAX_NUMBER_OF_DEVICES = 20000000
'''

    with open(filename, 'w') as file_:
        file_.write(template)


def creds_action(filename: str, *args):
    """ Create creds file """

    template = \
        '''CLIENT_DETAILS = {
}  # AUTOADAPTER - insert client information to test

SOME_DEVICE_ID = 'AUTOADAPTER - give one device_id that should return from the above client'
'''
    with open(filename, 'w') as file_:
        file_.write(template)


def test_service_action(filename: str, adapter_name: str, *args):
    """ Create tests service.py file """

    template = \
        f'''import pytest

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
'''
    with open(filename, 'w') as file_:
        file_.write(template)


def parallel_tests_action(filename: str, adapter_name: str, *args):
    """ Create parallel tests file """

    template = \
        f'''import pytest

# pylint: disable=unused-import
from services.adapters.{adapter_name}_service import {capitalize_adapter_name(adapter_name)}Service, \
{adapter_name}_fixture
from test_helpers.adapter_test_base import AdapterTestBase
from test_credentials.test_{adapter_name}_credentials import CLIENT_DETAILS, SOME_DEVICE_ID
from {adapter_name}_adapter.client_id import get_client_id


class Test{capitalize_adapter_name(adapter_name)}Adapter(AdapterTestBase):
    @property
    def adapter_service(self):
        return {capitalize_adapter_name(adapter_name)}Service()

    @property
    def adapter_name(self):
        return '{adapter_name}_adapter'

    @property
    def some_client_id(self):
        return get_client_id(CLIENT_DETAILS)

    @property
    def some_client_details(self):
        return CLIENT_DETAILS

    @property
    def some_device_id(self):
        return SOME_DEVICE_ID

    @property
    def some_user_id(self):
        raise NotImplementedError()

    @pytest.mark.skip('No test environment')
    def test_fetch_devices(self):
        pass

    @pytest.mark.skip('No test environment')
    def test_removing_adapter_creds_with_devices(self):
        pass

    @pytest.mark.skip('No test environment')
    def test_removing_adapter_creds_with_users(self):
        pass

    @pytest.mark.skip('No test environment')
    def test_check_reachability(self):
        pass
'''
    with open(filename, 'w') as file_:
        file_.write(template)


def ports_action(filename: str, adapter_name: str, *args):
    """ Appends port to the ports file """

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

    template = f"    '{adapter_name.replace('_', '-')}-adapter':".ljust(40) + f"{highest_port + 1},\n"
    lines.insert(mongoline, template)
    data = ''.join(lines)

    with open(filename, 'w') as file_:
        file_.write(data)


class ArgumentParser(argparse.ArgumentParser):
    """ Argumentparser for the script """

    def __init__(self, *args, **kwargs):
        super().__init__(*args, **kwargs)
        self.formatter_class = argparse.RawDescriptionHelpFormatter
        self.description = '''Example:
  %(prog)s github rest
  %(prog)s cisco_prime file'''
        self.add_argument("name", help="The new adapter name")
        self.add_argument("type_", help="The new adapter type", choices=[type_.value for type_ in AdapterTypes])
        self.add_argument('--delete', help="Delete all adapter files and information",
                          action="store_true", default=False)

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


def create_files(adapter_name: str, adapter_type: str):
    """ create needed files """

    for filename, (_, action) in get_action_table(adapter_name).items():
        filename = os.path.join(get_cortex_dir(), filename)
        action(filename, adapter_name, adapter_type)


def delete_port(filename: str, adapter_name: str):
    """ Deletes the port created for the adapter in ports.py """

    adapter_name = adapter_name.replace('_', '-')
    data = ''
    with open(filename, 'r', encoding='utf-8') as f:
        for line in f:
            if adapter_name in line:
                continue

            data += line

    with open(filename, 'w') as f:
        f.write(data)


def delete_description(filename: str, adapter_name: str):
    """ Deletes the description made for the adapter in plugin_meta.js
        Should be used for testing """
    description_dict = json.loads(open(filename, 'r', encoding='utf-8').read())
    adapter_key = f'{adapter_name}_adapter'
    if adapter_key in description_dict:
        del description_dict[adapter_key]

    with open(filename, 'w', encoding='utf-8') as file_:
        file_.write(json.dumps(description_dict, indent=2, ensure_ascii=False))


def delete_files(adapter_name: str, adapter_type: str):
    """ Delete all files that were created
        should be used for testing  """

    for filename in get_action_table(adapter_name).keys():
        filename = os.path.join(get_cortex_dir(), filename)

        if 'plugin_meta.js' in filename:
            print(f'Edit file {filename}')
            delete_description(filename, adapter_name)
            continue

        if os.path.isdir(filename):
            print(f'removing directory {filename}')
            shutil.rmtree(filename)
            continue

        if 'ports' in filename:
            print(f'Edit port {filename}')
            delete_port(filename, adapter_name)
            continue

        try:
            os.remove(filename)
            print(f'removing file {filename}')
        except Exception as err:
            print(f'File: {filename}, raised {str(err)}')
            pass


def main():
    """ Main function for the script """

    args = ArgumentParser().parse_args()
    adapter_name = args.name
    adapter_type = args.type_

    if args.delete:
        delete_files(adapter_name, adapter_type)
        return

    validate_files(adapter_name)
    create_files(adapter_name, adapter_type)


if __name__ == "__main__":
    main()
