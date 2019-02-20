import logging
logger = logging.getLogger(f'axonius.{__name__}')
from axonius.adapter_base import AdapterBase, AdapterProperty
from axonius.adapter_exceptions import ClientConnectionException
from axonius.devices.device_adapter import DeviceAdapter
from axonius.utils.files import get_local_config_file
from axonius.fields import Field
from axonius.utils.datetime import parse_date
from ensilo_adapter.connection import EnsiloConnection
from axonius.clients.rest.exception import RESTException
from axonius.clients.rest.connection import RESTConnection


class EnsiloAdapter(AdapterBase):

    class MyDeviceAdapter(DeviceAdapter):
        agent_version = Field(str, 'Agent Version')
        state = Field(str, "Device running state")

    def __init__(self, *args, **kwargs):
        super().__init__(config_file_path=get_local_config_file(__file__), *args, **kwargs)

    def _get_client_id(self, client_config):
        return client_config['domain']

    def _test_reachability(self, client_config):
        return RESTConnection.test_reachability(client_config.get('domain'))

    def _connect_client(self, client_config):
        try:

            connection = EnsiloConnection(domain=client_config["domain"],
                                          verify_ssl=client_config["verify_ssl"],
                                          username=client_config["username"],
                                          password=client_config["password"],
                                          https_proxy=client_config.get("https_proxy"),
                                          url_base_prefix="management-rest/",
                                          headers={'Content-Type': 'application/json',
                                                   'Accept': 'application/json'})
            with connection:
                pass  # check that the connection credentials are valid
            return connection
        except RESTException as e:
            message = "Error connecting to client with domain {0}, reason: {1}".format(
                client_config['domain'], str(e))
            logger.exception(message)
            raise ClientConnectionException(message)

    def _query_devices_by_client(self, client_name, client_data):
        """
        Get all devices from a specific Ensilo domain

        :param str client_name: The name of the client
        :param obj client_data: The data that represent a Ensilo connection

        :return: A json with all the attributes returned from the Ensilo Server
        """
        with client_data:
            yield from client_data.get_device_list()

    def _clients_schema(self):
        """
        The schema EnsiloAdapter expects from configs

        :return: JSON scheme
        """
        return {
            "items": [
                {
                    "name": "domain",
                    "title": "Ensilo Domain",
                    "type": "string"
                },
                {
                    "name": "username",
                    "title": "User Name",
                    "type": "string"
                },
                {
                    "name": "password",
                    "title": "Password",
                    "type": "string",
                    "format": "password"
                },
                {
                    "name": "verify_ssl",
                    "title": "Verify SSL",
                    "type": "bool"
                },
                {
                    "name": "https_proxy",
                    "title": "HTTPS Proxy",
                    "type": "string"
                }

            ],
            "required": [
                "domain",
                "username",
                "password",
                "verify_ssl"
            ],
            "type": "array"
        }

    def _parse_raw_data(self, devices_raw_data):
        for device_raw in devices_raw_data:
            try:
                device = self._new_device_adapter()
                host_name = device_raw.get("name")
                if host_name is None or host_name == "":
                    logger.error(f"Bad device with no Id {device_raw}")
                    continue
                device.id = str(device_raw.get("name")) + str(device_raw.get("operatingSystem", "")) + \
                    str(device_raw.get("version", ""))
                device.state = device_raw.get("state")
                device.hostname = host_name
                device.figure_os(device_raw.get("operatingSystem", ""))
                try:
                    mac_addresses = list(device_raw.get("macAddresses", []))
                    ip_addresses = device_raw.get("ipAddress")
                    if ip_addresses is not None:
                        ip_addresses = str(ip_addresses).split(",")
                    device.add_ips_and_macs(mac_addresses, ip_addresses)
                except Exception:
                    logger.exception("Problem with adding nic to ensilo device")
                device.agent_version = device_raw.get("version", "")
                device.last_seen = parse_date(str(device_raw.get("lastSeenTime", "")))
                device.set_raw(device_raw)
                yield device
            except Exception:
                logger.exception("Problem with fetching Ensilo Device")

    @classmethod
    def adapter_properties(cls):
        return [AdapterProperty.Endpoint_Protection_Platform, AdapterProperty.Agent, AdapterProperty.Manager]
