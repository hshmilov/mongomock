import abc
import dateutil.parser

from axonius.adapter_exceptions import ClientConnectionException, ParseDevicesError


class NexposeClient(abc.ABC):

    def __init__(self, num_of_simultaneous_devices, host, port, username, password, verify_ssl):
        self.host = host
        self.port = port
        self.username = username
        self.password = password
        self.num_of_simultaneous_devices = num_of_simultaneous_devices
        self.verify_ssl = verify_ssl
        if not self._does_api_exist():
            raise ClientConnectionException("API Does not Exist.")
        super().__init__()

    @abc.abstractmethod
    def get_all_devices(self):
        """ Get all the raw devices from the client.

        :return: dict containing the api version and the devices.
        """
        pass

    @abc.abstractmethod
    def _does_api_exist(self):
        """ Test if the config setup has this client's api.

        :param client_config: The client configuration (host, port, username, password).
        :return: bool signifies if this client is able to connect to it.

        """
        pass

    @staticmethod
    @abc.abstractmethod
    def parse_raw_device(device_raw, device_class):
        """ Used to parse a single raw device that this client class returned.

        :param device_raw: The raw device data returned by this client class.
        :param device_class: The axonius device class to generate and return.
        :return: A filled axonius device_class.
        """

    @staticmethod
    def parse_raw_device_last_seen(last_seen):
        try:
            if last_seen is None:
                # No data on the last timestamp of the device. Not inserting this device.
                raise ParseDevicesError("An Exception was raised while getting and parsing the last_seen field.")

            # Parsing the timestamp and setting the tz to None.
            last_seen = dateutil.parser.parse(last_seen)
        except Exception as err:
            raise

        return last_seen
