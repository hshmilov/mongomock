import threading
import ctypes
import logging
from urllib3.util.url import parse_url


logger = logging.getLogger(f'axonius.{__name__}')
from axonius.adapter_base import AdapterBase, AdapterProperty
from axonius.utils.datetime import parse_date
from axonius.utils.parsing import format_mac
from axonius.clients.rest.connection import RESTConnection
from axonius.devices.device_adapter import DeviceAdapter
import axonius.adapter_exceptions
from axonius.utils.files import get_local_config_file
from eset_adapter.client import EsetClient


PASSWORD = 'password'
USER = 'username'
ESET_HOST = 'host'
ESET_PORT = 'port'

BIN_LOCATION = '/home/axonius/bin/eset_connection.so'


class EsetAdapter(AdapterBase):
    """
    Connects axonius to Eset Remote Administrator (ERA)
    """

    class MyDeviceAdapter(DeviceAdapter):
        pass

    def __init__(self, **kwargs):
        super().__init__(get_local_config_file(__file__))

        # This lock will be passed to client connections to make sure only one client is in session at a time.
        self.eset_session_lock = threading.RLock()

        # Loading and setting up eset_connection shared library.
        # The responsibility for unloading the library is on the python interpreter garbage collection
        # as recommended by the ctypes documentation.
        self._load_eset_connection_library()

    def _load_eset_connection_library(self):
        """Shared library loading and setting up.

        Loads the shared library located in ./ERAApi/eset_connection.cpp
        And sets up all the function args and ret types.

        """
        try:
            # Loading the cpp wrapper.
            self.eset_connection_library = ctypes.cdll.LoadLibrary(BIN_LOCATION)

            # Check cpp wrapper load
            self.eset_connection_library.GetState.restype = ctypes.c_char_p

            load_state = self.eset_connection_library.GetState()

            if load_state != b"Ready":
                raise RuntimeError("The eset_connection.so failed to init. The state was: {0}.".format(load_state))
        except Exception:
            raise axonius.adapter_exceptions.AdapterException("Failed to load eset_connection shared library.")

        # Setting up the arg and return types of the functions
        self.eset_connection_library.SendMessage.argtypes = [ctypes.c_char_p]
        self.eset_connection_library.SendMessage.restype = ctypes.c_void_p
        self.eset_connection_library.FreeResponse.argtypes = [ctypes.c_void_p]

    def _clients_schema(self):
        return {
            "items": [
                {
                    "name": ESET_HOST,
                    "title": "Host Name",
                    "type": "string"
                },
                {
                    "name": ESET_PORT,
                    "title": "Port",
                    "type": "integer",
                    'default': 2223
                },
                {
                    "name": USER,
                    "title": "User Name",
                    "type": "string"
                },
                {
                    "name": PASSWORD,
                    "title": "Password",
                    "type": "string",
                    "format": "password"
                },
                {
                    'name': 'is_domain_user',
                    'title': 'Is Domain User',
                    'type': 'bool'
                }
            ],
            "required": [
                USER,
                PASSWORD,
                ESET_HOST,
                'is_domain_user'
            ],
            "type": "array"
        }

    def _parse_raw_data(self, raw_data):
        for entry in raw_data:
            try:
                device = self._new_device_adapter()
                hostname = entry.get('Computer name', '')
                mac_address = format_mac(entry.get('MAC address', ''))
                if mac_address is None and hostname == "":
                    logger.warning(f"No id for entry: {entry}")
                    continue
                device.hostname = hostname
                device.id = f"{str(mac_address)}{str(hostname)}"
                device.figure_os(' '.join([entry.get('OS type', ''),
                                           entry.get('OS name', ''),
                                           entry.get('OS platform', ''),
                                           entry.get('OS version', '')]))
                device.add_nic(mac_address, [entry.get('Adapter IPv4 address', '')])
                try:
                    last_seen = parse_date(entry.get('Last connected', ''))
                    if last_seen:
                        device.last_seen = last_seen
                except Exception:
                    logger.exception(f"Problem adding last seen to entry {entry}")

                device.set_raw(entry)

                yield device
            except Exception:
                logger.exception(f"Got problem with entry: {entry}")

    def _query_devices_by_client(self, client_name, client_data):
        assert isinstance(client_data, EsetClient)
        # client_data.connect()  # refresh connection
        return client_data.get_all_devices()

    def _get_client_id(self, client_config):
        return f"{client_config[ESET_HOST]}:{client_config.get(ESET_PORT, 2223)}"

    def _test_reachability(self, client_config):
        return RESTConnection.test_reachability(client_config.get(ESET_HOST),
                                                port=client_config.get(ESET_PORT))

    def _connect_client(self, client_config):
        eset_host = parse_url(client_config[ESET_HOST]).host
        return EsetClient(self.eset_session_lock, self.eset_connection_library,
                          host=eset_host, username=client_config[USER],
                          password=client_config[PASSWORD], port=client_config.get(ESET_PORT) or 2223,
                          is_domain_user='true' if client_config.get('is_domain_user') else 'false')

    @classmethod
    def adapter_properties(cls):
        return [AdapterProperty.Endpoint_Protection_Platform, AdapterProperty.Agent, AdapterProperty.Manager]
