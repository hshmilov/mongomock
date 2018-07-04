import logging
logger = logging.getLogger(f"axonius.{__name__}")
import re

from axonius.adapter_base import AdapterBase, AdapterProperty
from axonius.adapter_exceptions import ClientConnectionException
from axonius.devices.device_adapter import DeviceAdapter
from axonius.utils.files import get_local_config_file
from sentinelone_adapter.connection import SentinelOneConnection
from axonius.clients.rest.exception import RESTException
from axonius.fields import Field
from axonius.utils.parsing import parse_date


class SentineloneAdapter(AdapterBase):

    class MyDeviceAdapter(DeviceAdapter):
        agent_version = Field(str, 'Agent Version')
        active_state = Field(str, 'Active State')
        public_ip = Field(str, "Public IP")

    def __init__(self, *args, **kwargs):
        super().__init__(config_file_path=get_local_config_file(__file__), *args, **kwargs)

    def _get_client_id(self, client_config):
        return client_config['domain']

    def _connect_client(self, client_config):
        has_token = bool(client_config.get('token'))
        maybe_has_user = bool(client_config.get('username')) or bool(client_config.get('password'))
        has_user = bool(client_config.get('username')) and bool(client_config.get('password'))
        if has_token and maybe_has_user:
            msg = f"Different logins for SentinelOne domain " \
                  f"{client_config.get('domain')}, user: {client_config.get('username', '')}"
            logger.error(msg)
            raise ClientConnectionException(msg)
        elif maybe_has_user and not has_user:
            msg = f"Missing credentials for SentinelOne domain " \
                  f"{client_config.get('domain')}, user: {client_config.get('username', '')}"
            logger.error(msg)
            raise ClientConnectionException(msg)
        try:
            connection = SentinelOneConnection(domain=client_config["domain"],
                                               https_proxy=client_config.get("https_proxy"),
                                               username=client_config.get("username"),
                                               password=client_config.get("password"),
                                               url_base_prefix="web/api/v2.0/",
                                               headers={'Content-Type': 'application/json',
                                                        'Accept': 'application/json'},
                                               verify_ssl=client_config["verify_ssl"])
            if has_token:
                connection.set_token(client_config['token'])
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
        Get all devices from a specific SentinelOne domain

        :param str client_name: The name of the client
        :param obj client_data: The data that represent a SentinelOne connection

        :return: A json with all the attributes returned from the SentinelOne Server
        """
        with client_data:
            yield from client_data.get_device_list()

    def _clients_schema(self):
        """
        The schema SentinelOneAdapter expects from configs

        :return: JSON scheme
        """
        return {
            "items": [
                {
                    "name": "domain",
                    "title": "Sentinel One Domain",
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
                    "name": "token",
                    "title": "API token",
                    "type": "string",
                    "format": "password"
                },
                {
                    "name": "https_proxy",
                    "title": "HTTPS Proxy",
                    "type": "string"
                },
                {
                    "name": "verify_ssl",
                    "title": "Verify SSL",
                    "type": "bool"
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
                device.id = device_raw['id']
                device.agent_version = device_raw.get('agentVersion')
                device.last_seen = parse_date(str(device_raw.get('lastActiveDate', '')))
                device.public_ip = device_raw.get("externalIp")
                device.domain = device_raw.get("domain")
                try:
                    ad_domain = ""
                    ad_nodes_names = device_raw.get("activeDirectory", {}).\
                        get("computerDistinguishedName", "").split(',')
                    for ad_node in ad_nodes_names:
                        ad_node_split = ad_node.split('=')
                        if len(ad_node_split) != 2:
                            continue
                        if ad_node_split[0].upper() != "DC":
                            continue
                        ad_domain += "." + ad_node_split[1]
                except Exception:
                    logger.exception(f"Problem getting SentinelOne AD info {device_raw}")
                computer_name = device_raw.get('computerName')
                if computer_name is not None:
                    hostname = computer_name
                    if ad_domain is not None and ad_domain != "" and ad_domain.upper() != "N/A":
                        hostname = f"{hostname}{ad_domain}"
                    device.hostname = hostname
                device.figure_os(device_raw.get("osType", "") + " " + device_raw.get("osName"))
                interfaces = device_raw.get("networkInterfaces", [])
                for interface in interfaces:
                    try:
                        device.add_nic(interface.get('physical'),
                                       interface.get('inet6', []) + interface.get('inet', []),
                                       name=interface.get('name'))
                    except Exception:
                        logger.exception(f"Problem adding nic {str(interface)} to SentinelOne")
                try:
                    device.last_used_users = device_raw.get("lastLoggedInUserName", "").split(',')
                except Exception:
                    logger.exception(f"Problem with adding users to {device_raw}")
                try:
                    device.total_physical_memory = int(device_raw.get("totalMemory", 0)) / 1024.0
                except Exception:
                    logger.exception(f"Problem with adding memory to {device_raw}")
                device.set_raw(device_raw)
                yield device
            except Exception:
                logger.exception(f"Got problems with device {device_raw}")

    @classmethod
    def adapter_properties(cls):
        return [AdapterProperty.Endpoint_Protection_Platform, AdapterProperty.Agent, AdapterProperty.Manager]
