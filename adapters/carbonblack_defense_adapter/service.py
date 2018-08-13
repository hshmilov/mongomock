import logging
logger = logging.getLogger(f'axonius.{__name__}')
from axonius.adapter_base import AdapterBase, AdapterProperty
from axonius.adapter_exceptions import ClientConnectionException
from axonius.devices.device_adapter import DeviceAdapter
from axonius.utils.files import get_local_config_file
from axonius.fields import Field
from axonius.clients.rest.exception import RESTException
from carbonblack_defense_adapter.connection import CarbonblackDefenseConnection
import datetime


class CarbonblackDefenseAdapter(AdapterBase):

    class MyDeviceAdapter(DeviceAdapter):
        av_status = Field(str, 'AV Status')
        status = Field(str, 'Agent Status')
        sensor_version = Field(str, 'Sensor Version')
        policy_name = Field(str, 'Policy Name')
        public_ip = Field(str, 'Public IP')

    def __init__(self):
        super().__init__(get_local_config_file(__file__))

    def _get_client_id(self, client_config):
        return client_config['domain']

    def _connect_client(self, client_config):
        try:
            connection = CarbonblackDefenseConnection(domain=client_config["domain"],
                                                      verify_ssl=client_config["verify_ssl"],
                                                      https_proxy=client_config.get("https_proxy"),
                                                      headers={'Content-Type': 'application/json',
                                                               'Accept': 'application/json',
                                                               'X-Auth-Token': f"{client_config['apikey']}/"
                                                               f"{client_config['connector_id']}"},
                                                      url_base_prefix="integrationServices/v3/")
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
        Get all devices from a specific CarbonblackDefense domain

        :param str client_name: The name of the client
        :param obj client_data: The data that represent a Carbonblack connection

        :return: A json with all the attributes returned from the Carbonblack Server
        """
        try:
            client_data.connect()
            yield from client_data.get_device_list()
        finally:
            client_data.close()

    def _clients_schema(self):
        """
        The schema CarbonblackDefenseAdapter expects from configs

        :return: JSON scheme
        """
        return {
            "items": [
                {
                    "name": "domain",
                    "title": "Carbonblack Defense Domain",
                    "type": "string"
                },
                {
                    "name": "apikey",
                    "title": "API Key",
                    "type": "string",
                    "format": "password"
                },
                {
                    "name": "connector_id",
                    "title": "Connector ID",
                    "type": "string"
                },
                {
                    "name": "verify_ssl",
                    "title": "Verify SSL",
                    "type": "bool"
                },
                {
                    "name": "https_proxy",
                    "title": "Https Proxy",
                    "type": "string"
                }
            ],
            "required": [
                "domain",
                "apikey",
                "connector_id",
                "verify_ssl"
            ],
            "type": "array"
        }

    def _parse_raw_data(self, devices_raw_data):
        for device_raw in devices_raw_data:
            try:
                device = self._new_device_adapter()
                device.id = device_raw.get("deviceId")
                if device.id is None:
                    continue
                else:
                    device.id = str(device.id)
                device.hostname = device_raw.get("name")
                device.hostname = ".".join(device.hostname.split('\\')[::-1])
                try:
                    device.figure_os((device_raw.get("deviceType") or "") + " " + (device_raw.get("osVersion") or ""))
                except Exception:
                    logger.exception(f"Problem adding os to :{device_raw}")
                try:
                    if device_raw.get("lastInternalIpAddress"):
                        device.add_nic(None, (device_raw.get("lastInternalIpAddress") or "").split(","))
                except Exception:
                    logger.exception("Problem with adding nic to CarbonblackDefense device")
                try:
                    device.last_seen = datetime.datetime.fromtimestamp(max(device_raw.get("lastReportedTime", 0),
                                                                           device_raw.get("lastContact", 0)) / 1000)
                except Exception:
                    logger.exception("Problem getting Last seen in CarbonBlackDefense")
                device.av_status = str(device_raw.get("avStatus"))
                device.status = device_raw.get("status")
                device.sensor_version = device_raw.get("sensorVersion")
                device.policy_name = device_raw.get("policyName")
                device.public_ip = device_raw.get("lastExternalIpAddress")
                device.set_raw(device_raw)
                yield device
            except Exception:
                logger.exception("Problem with fetching CarbonblackDefense Device")

    @classmethod
    def adapter_properties(cls):
        return [AdapterProperty.Endpoint_Protection_Platform, AdapterProperty.Agent, AdapterProperty.Manager]
