import abc
import logging
import dateutil.parser

from axonius.adapter_exceptions import ClientConnectionException, ParseDevicesError


logger = logging.getLogger(f'axonius.{__name__}')


class NexposeClient(abc.ABC):

    def __init__(self, num_of_simultaneous_devices, host, port, username, password, verify_ssl, token=None,
                 https_proxy=None,
                 proxy_username=None,
                 proxy_password=None,
                 ):
        self.host = host
        self.port = port
        self.username = username
        self.password = password
        self.num_of_simultaneous_devices = num_of_simultaneous_devices
        self.verify_ssl = verify_ssl
        self._token = token
        self._proxies = None
        if https_proxy is not None:
            self._proxies = {}
            https_proxy = https_proxy.strip()
            try:
                if proxy_username and proxy_password:
                    https_proxy = f'{proxy_username}:{proxy_password}@{https_proxy}'
            except Exception:
                logger.exception(f'Problem with username password for proxy')
            self._proxies['https'] = https_proxy
        if not self._does_api_exist():
            raise ClientConnectionException("API Does not Exist.")
        super().__init__()

    @abc.abstractmethod
    def get_all_devices(self, fetch_tags=False, fetch_vulnerabilities=False,
                        fetch_policies=False, fetch_ports=False, fetch_sw=False,
                        ):
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
    def parse_raw_device(device_raw, device_class, drop_only_ip_devices=False, fetch_vulnerabilities=False,
                         site_name_exclude_list=None, fetch_users=True):
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
            return None

        return last_seen
