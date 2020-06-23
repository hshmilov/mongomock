import logging
from io import StringIO

import paramiko
from scp import SCPClient

from axonius.adapter_exceptions import ClientConnectionException
from axonius.consts.plugin_consts import DEVICE_CONTROL_PLUGIN_NAME
from axonius.utils import gui_helpers
from axonius.types.enforcement_classes import AlertActionResult
from axonius.utils.memfiles import temp_memfd
from axonius.clients.linux_ssh.consts import UPLOAD_PATH_NAME, HOSTNAME, PORT, USERNAME, PASSWORD, PRIVATE_KEY, \
    PASSPHRASE
from reports.action_types.action_type_alert import ActionTypeAlert


logger = logging.getLogger(f'axonius.{__name__}')


class SSHConnection:
    def __init__(self,
                 hostname,
                 port,
                 username=None,
                 password=None,
                 key_file=None,
                 pkey=None,
                 passphrase=None):
        if not (password or (pkey or key_file)):
            raise ClientConnectionException('Password/Key is required')
        if pkey and key_file:
            raise ClientConnectionException('Please specify only pkey or key_file, not both')
        self._port = port
        self._hostname = hostname
        self._username = username
        self._password = password
        self._key = None
        if pkey:
            if isinstance(pkey, bytes):
                pkey = pkey.decode()
            with StringIO(pkey) as file_obj:
                self._key = paramiko.RSAKey.from_private_key(file_obj)
        self._key_file = key_file
        self._passphrase = passphrase

        self._client = None

    def connect(self):
        self._client = paramiko.SSHClient()
        self._client.set_missing_host_key_policy(paramiko.AutoAddPolicy())
        self._client.connect(hostname=self._hostname,
                             port=self._port,
                             username=self._username,
                             password=self._password,
                             key_filename=self._key_file,
                             pkey=self._key,
                             look_for_keys=False,
                             passphrase=self._passphrase)

    def close(self):
        if self._client:
            self._client.close()
            self._client = None

    def __enter__(self):
        try:
            self.connect()
        except Exception as e:
            message = f'Failed connection to host: {str(e)}'
            logger.exception(message)
            raise
        return self

    def __exit__(self, exc_type, exc_val, exc_tb):
        if exc_type:
            message = f'Error with ssh connection: {str(exc_val)}'
            logger.exception(message, exc_info=(exc_type, exc_val, exc_tb))
        self.close()

    def upload_file(self, source_path, remote_path):
        """
        Upload file to remote server via scp
        :param source_path: source file path
        :param remote_path: remote file path
        :return: true on success, otherwise false.
        :notes: file will be overridden if exists on server.
        """
        try:
            logger.debug(f'Trying to upload {source_path} to {remote_path}')
            with SCPClient(self._client.get_transport()) as scp:
                scp.put(source_path, remote_path)
            return True
        except Exception:
            logger.exception('Upload Error')
            return False


# pylint: disable=invalid-triple-quote
class SendCsvToScp(ActionTypeAlert):
    """
    Send CSV results to defined scp
    """

    @staticmethod
    def config_schema() -> dict:
        return {
            'items': [
                {
                    'name': HOSTNAME,
                    'title': 'Hostname',
                    'type': 'string'
                },
                {
                    'name': USERNAME,
                    'title': 'User Name',
                    'type': 'string'
                },
                {
                    'name': PASSWORD,
                    'title': 'Password',
                    'type': 'string',
                    'format': 'password'
                },
                {
                    'name': PRIVATE_KEY,
                    'title': 'Private key',
                    'description': 'SSH private key for authentication',
                    'type': 'file',
                },
                {
                    'name': PASSPHRASE,
                    'title': 'Private key passphrase',
                    'description': 'SSH private key passphrase',
                    'type': 'string',
                    'format': 'password',
                },
                {
                    'name': PORT,
                    'title': 'SSH port',
                    'type': 'integer',
                    'description': 'Protocol port'
                },
                {
                    'name': UPLOAD_PATH_NAME,
                    'title': 'CSV target path',
                    'type': 'string'
                }
            ],
            'required': [HOSTNAME, PORT, UPLOAD_PATH_NAME],
            'type': 'array'
        }

    @staticmethod
    def default_config() -> dict:
        return {
            HOSTNAME: None,
            USERNAME: None,
            PASSWORD: None,
            PORT: 22,
            UPLOAD_PATH_NAME: None,
            PRIVATE_KEY: None,
            PASSPHRASE: None,
        }

    # pylint: disable=W0212
    def _load_file(self, file_name):
        dc_pun = DEVICE_CONTROL_PLUGIN_NAME
        raw_data = self._plugin_base._grab_file_contents(
            file_name,
            alternative_db_name=dc_pun)
        return raw_data

    # pylint:disable=too-many-return-statements
    def _run(self) -> AlertActionResult:
        try:
            if not self._internal_axon_ids:
                return AlertActionResult(False, 'No Data')

            sort = gui_helpers.get_sort(self.trigger_view_config)
            field_list = self.trigger_view_config.get('fields', [
                'specific_data.data.name', 'specific_data.data.hostname', 'specific_data.data.os.type',
                'specific_data.data.last_used_users', 'labels'
            ])
            field_filters = self.trigger_view_config.get('colFilters', {})
            csv_string = gui_helpers.get_csv(self.trigger_view_parsed_filter,
                                             sort,
                                             {field: 1 for field in field_list},
                                             self._entity_type,
                                             field_filters=field_filters)

            binary_arr = csv_string.getvalue().encode('utf-8')
            dst_path = self._config.get(UPLOAD_PATH_NAME)
            # verify auth config
            passphrase = self._config.get(PASSPHRASE)
            username = self._config.get(USERNAME)
            password = self._config.get(PASSWORD)
            key_file = self._config.get(PRIVATE_KEY)
            private_key = None
            if key_file:
                try:
                    private_key = self._load_file(key_file)
                except Exception:
                    message = f'Failed to load private key from {key_file}'
                    logger.exception(message)
                    return AlertActionResult(False, message)
            if passphrase and not private_key:
                message = f'Please specify private key to use with passphrase, or omit the passphrase.'
                logger.exception(message)
                return AlertActionResult(False, message)
            if (username and password) and private_key:
                message = f'Please specify either username and password, or private key and optional passphrase, ' \
                          f'but not both.'
                logger.exception(message)
                return AlertActionResult(False, message)
            logger.debug(f'XXX: {key_file}')
            connection = SSHConnection(
                hostname=self._config[HOSTNAME],
                port=self._config[PORT],
                username=username or None,
                password=password or None,
                passphrase=passphrase or None,
                pkey=private_key or None,
            )
            with connection:
                with temp_memfd('upload_file', binary_arr) as filepath:
                    # upload file to the server
                    result = connection.upload_file(filepath, str(dst_path))
                    if not result:
                        return AlertActionResult(False, 'Failed to write SCP')
            return AlertActionResult(True, 'Wrote to SCP')
        except Exception as e:
            logger.exception(f'Problem sending CSV to SCP: {str(e)}')
            return AlertActionResult(False, f'Failed writing to SCP. Error was: {str(e)}')
