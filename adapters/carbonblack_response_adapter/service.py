import logging
logger = logging.getLogger(f'axonius.{__name__}')
from axonius.adapter_base import AdapterBase, AdapterProperty
from axonius.adapter_exceptions import ClientConnectionException
from axonius.devices.device_adapter import DeviceAdapter
from axonius.utils.files import get_local_config_file
from axonius.fields import Field
from axonius.clients.rest.exception import RESTException
from carbonblack_response_adapter.connection import CarbonblackResponseConnection
from axonius.utils.parsing import parse_date
from axonius.clients.rest.connection import RESTConnection


class CarbonblackResponseAdapter(AdapterBase):

    class MyDeviceAdapter(DeviceAdapter):
        build_version_string = Field(str, 'Sensor Version')
        sensor_health_message = Field(str, 'Sensor Health Message')

    def __init__(self):
        super().__init__(get_local_config_file(__file__))

    def _get_client_id(self, client_config):
        return client_config['domain']

    def _test_reachability(self, client_config):
        return RESTConnection.test_reachability(client_config.get('domain'))

    def _connect_client(self, client_config):
        try:
            connection = CarbonblackResponseConnection(domain=client_config["domain"],
                                                       verify_ssl=client_config.get("verify_ssl", False),
                                                       username=client_config.get("username"),
                                                       password=client_config.get("password"),
                                                       apikey=client_config.get('apikey'),
                                                       headers={'Content-Type': 'application/json',
                                                                'Accept': 'application/json'},
                                                       url_base_prefix="api/",
                                                       https_proxy=client_config.get("https_proxy"))
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
        Get all devices from a specific CarbonblackResponse domain

        :param str client_name: The name of the client
        :param obj client_data: The data that represent a CarbonblackResponse connection

        :return: A json with all the attributes returned from the CarbonblackResponse Server
        """
        try:
            client_data.connect()
            yield from client_data.get_device_list()
        finally:
            client_data.close()

    def _clients_schema(self):
        """
        The schema CarbonblackAdapterResponse expects from configs

        :return: JSON scheme
        """
        return {
            "items": [
                {
                    "name": "domain",
                    "title": "Carbonblack Response Domain",
                    "type": "string"
                },
                {
                    "name": "username",
                    "title": "Username",
                    "type": "string"
                },
                {
                    "name": "password",
                    "title": "Password",
                    "type": "string",
                    "format": "password"
                },
                {
                    'name': 'apikey',
                    'title': 'API Token',
                    'type': 'string',
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
                "verify_ssl"
            ],
            "type": "array"
        }

    def _parse_raw_data(self, devices_raw_data):
        for device_raw in devices_raw_data:
            try:
                device = self._new_device_adapter()
                device.id = device_raw.get("id")
                if device.id is None:
                    continue
                else:
                    device.id = str(device.id)
                device.sensor_health_message = device_raw.get("sensor_health_message")
                device.build_version_string = device_raw.get("build_version_string")
                device.hostname = device_raw.get("computer_dns_name") or device_raw.get('computer_name')
                device.figure_os(device_raw.get("os_environment_display_string", ""))
                try:
                    if device_raw.get("network_adapters"):
                        for nic in device_raw.get("network_adapters").split('|'):
                            if nic != "":
                                ip_address, mac_address = nic.split(',')
                                device.add_nic(mac_address, [ip_address])
                except Exception:
                    logger.exception(f"Problem with adding nic to CarbonblackResponse device {device_raw}")
                try:
                    device.last_seen = parse_date(str(device_raw.get("last_checkin_time", "")))
                except Exception:
                    logger.exception("Problem getting Last seen in CarbonBlackResponse")
                device.set_raw(device_raw)
                yield device
            except Exception:
                logger.exception("Problem with fetching CarbonblackResponse Device")

    @classmethod
    def adapter_properties(cls):
        return [AdapterProperty.Endpoint_Protection_Platform, AdapterProperty.Agent, AdapterProperty.Manager]
