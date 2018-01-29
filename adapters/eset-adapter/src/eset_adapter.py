import threading
import os
import ctypes

from eset_client import EsetClient
from axonius.adapter_base import AdapterBase
from axonius.parsing_utils import format_mac, parse_date
from axonius.device import Device
import axonius.adapter_exceptions


PASSWORD = 'password'
USER = 'username'
ESET_HOST = 'host'
ESET_PORT = 'port'

BIN_LOCATION = '/home/axonius/bin/eset_connection.so'


class EsetAdapter(AdapterBase):
    """
    Connects axonius to Eset Remote Administrator (ERA)
    """

    class MyDevice(Device):
        pass

    def __init__(self, **kwargs):
        """Class initialization.

        Check AdapterBase documentation for additional params and exception details.

        """
        # Initialize the base plugin (will initialize http server)
        super().__init__(**kwargs)

        # Loading and setting up eset_connection shared library.
        # The responsibility for unloading the library is on the python interpreter garbage collection
        # as recommended by the ctypes documentation.
        self._load_eset_connection_library()

        # This lock will be passed to client connections to make sure only one client is in session at a time.
        self.eset_session_lock = threading.RLock()

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
            self.logger.exception("Failed to load eset_connection shared library.")
            raise axonius.adapter_exceptions.AdapterException("Failed to load eset_connection shared library.")

        # Setting up the arg and return types of the functions
        self.eset_connection_library.SendMessage.argtypes = [ctypes.c_char_p]
        self.eset_connection_library.SendMessage.restype = ctypes.c_void_p
        self.eset_connection_library.FreeResponse.argtypes = [ctypes.c_void_p]

    def _clients_schema(self):
        return {
            "properties": {
                ESET_HOST: {
                    "type": "string"
                },
                ESET_PORT: {
                    "type": "integer"
                },
                USER: {
                    "type": "string"
                },
                PASSWORD: {
                    "type": "password"
                }
            },
            "required": [
                USER,
                PASSWORD,
                ESET_HOST,
            ],
            "type": "object"
        }

    def _parse_raw_data(self, raw_data):
        for entry in raw_data:
            device = self._new_device()
            device.hostname = entry.get('Computer name', '')
            mac_address = format_mac(entry.get('MAC address', ''))
            device.id = mac_address
            device.figure_os(' '.join([entry.get('OS type', ''),
                                       entry.get('OS name', ''),
                                       entry.get('OS platform', ''),
                                       entry.get('OS version', '')]))
            device.add_nic(mac_address, [entry.get('Adapter IPv4 address', '')])

            last_seen = parse_date(entry.get('Last connected', ''))
            if last_seen:
                device.last_seen = last_seen

            device.set_raw(entry)

            yield device

    def _query_devices_by_client(self, client_name, client_data):
        assert isinstance(client_data, EsetClient)
        # client_data.connect()  # refresh connection
        return client_data.get_all_devices()

    def _get_client_id(self, client_config):
        return f"{client_config[ESET_HOST]}:{client_config.get(ESET_PORT, 2223)}"

    def _connect_client(self, client_config):
        return EsetClient(self.eset_session_lock, self.eset_connection_library, self.logger, host=client_config[ESET_HOST], username=client_config[USER],
                          password=client_config[PASSWORD], port=client_config.get(ESET_PORT, 2223))
