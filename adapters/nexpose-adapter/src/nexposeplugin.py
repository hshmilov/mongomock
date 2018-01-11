import time
from contextlib import contextmanager
import ssl

from axonius.adapter_base import AdapterBase
from axonius.parsing_utils import figure_out_os

import nexpose.nexpose as nexpose

PASSWORD = 'password'
USER = 'username'
NEXPOSE_HOST = 'host'
NEXPOSE_PORT = 'port'
VERIFY_SSL = 'verify_ssl'


class NexposePlugin(AdapterBase):
    """
    Connects axonius to Rapid7's nexpose.
    """

    def __init__(self, **kwargs):
        """Class initialization.

        Check AdapterBase documentation for additional params and exception details.

        """

        # Initialize the base plugin (will initialize http server)
        super().__init__(**kwargs)

    def _wait_for_status(self, session, expected_status, message):
        self.logger.info(message)
        while True:
            status = session.GetSecurityConsoleStatus()
            self.logger.info("Current status:{0}".format(status))
            if status == expected_status:
                break
            time.sleep(5)

    @contextmanager
    def _get_session(self, should_verify_ssl, client_data):
        """A context manager for session object, to be used only with."""
        if not should_verify_ssl:
            # Handle target environment that doesn't support HTTPS verification
            _create_unverified_https_context = ssl._create_unverified_context
            ssl._create_default_https_context = _create_unverified_https_context

        session = nexpose.NexposeSession.Create(**client_data)
        self._wait_for_status(session, nexpose.NexposeStatus.NORMAL_MODE, "Waiting for the console to be ready:")
        self.logger.info("The Security Console is ready...")
        session.Open()
        try:
            yield session
        except:
            self.logger.exception('An exception occurred while in session')
        finally:
            session.Close()

    def _clients_schema(self):
        return {
            "properties": {
                PASSWORD: {
                    "type": "password"
                },
                USER: {
                    "type": "string"
                },
                NEXPOSE_HOST: {
                    "type": "string"
                },
                NEXPOSE_PORT: {
                    "type": "integer"
                },
                VERIFY_SSL: {  # if false, it will allow for invalid SSL certificates (but still uses HTTPS)
                    "type": "bool"
                }

            },
            "required": [
                USER,
                PASSWORD,
                NEXPOSE_PORT,
                NEXPOSE_HOST,
            ],
            "type": "object"
        }

    def _parse_raw_data(self, raw_data):
        def _create_network_interface(addresses, mac_address):
            interfaces = []
            for current_address in addresses:
                current_interface = {'IP': current_address, 'MAC': mac_address}
                interfaces.append(current_interface)
            return interfaces

        for device_raw_data in raw_data:
            yield {
                'OS': figure_out_os(device_raw_data.get('os_name')),
                'id': str(device_raw_data['id']),
                'network_interfaces': _create_network_interface(device_raw_data.get('addresses', ''),
                                                                device_raw_data.get('mac_address', '')),
                'hostname': device_raw_data['host_names'][0] if len(device_raw_data.get('host_names', [])) > 0 else '',
                'raw': device_raw_data
            }

    def _query_devices_by_client(self, client_name, client_data):
        def _parse_nexpose_asset_details_to_dict(asset_details):
            """
            Goes over the attibutes of nexpose's AssetDetails and creates a viable dict from them.
            :param asset_details: The AssetDetails object to parse to dict.
            :return: a dict.
            """
            details = dict()
            # The reason for getting rid of 'unique_identifiers' is that it's a specialized class that I didn't see
            # a reason to parse because there isn't new data here but just data we already got.
            for current_detail in \
                    [attribute for attribute in dir(asset_details) if not attribute.startswith('__') and
                     not callable(getattr(asset_details,
                                          attribute)) and
                     attribute != 'unique_identifiers']:
                details[current_detail] = getattr(asset_details, current_detail)
            return details

        devices = []
        should_verify_ssl = client_data.pop(VERIFY_SSL)
        with self._get_session(should_verify_ssl, client_data) as session:
            for asset in session.GetAssetSummaries():
                devices.append(_parse_nexpose_asset_details_to_dict(session.GetAssetDetails(asset)))

        return devices

    def _get_client_id(self, client_config):
        return client_config[NEXPOSE_HOST]

    def _connect_client(self, client_config):
        return client_config
