from json import loads

from axonius.entities import EntityType
from json_file_adapter.service import USERS_DATA, DEVICES_DATA
from test_helpers.file_mock_credentials import FileForCredentialsMock


class FileMockHelper:

    @classmethod
    def _get_data_type_by_mock_type(cls, mock_data_type):
        if mock_data_type == DEVICES_DATA:
            return EntityType.Devices.value
        if mock_data_type == USERS_DATA:
            return EntityType.Users.value
        raise ValueError(f'unsupported mock data type {mock_data_type}')

    @classmethod
    def get_mock_devices_count(cls, file_credentials_mock: FileForCredentialsMock):
        return cls._get_mock_data_count(file_credentials_mock, DEVICES_DATA)

    @classmethod
    def get_mock_users_count(cls, file_credentials_mock: FileForCredentialsMock):
        return cls._get_mock_data_count(file_credentials_mock, USERS_DATA)

    @classmethod
    def _get_mock_data_count(cls, file_credentials_mock: FileForCredentialsMock, mock_data_type) -> int:
        if file_credentials_mock.filename == mock_data_type and file_credentials_mock.file_contents:
            return len(loads(file_credentials_mock.file_contents).get(cls._get_data_type_by_mock_type(mock_data_type)))
        raise ValueError(f'FileForCredentialsMock is not {mock_data_type} type')
