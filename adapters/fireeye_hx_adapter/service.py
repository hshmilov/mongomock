import logging
logger = logging.getLogger(f'axonius.{__name__}')
from axonius.adapter_base import AdapterBase, AdapterProperty
from axonius.adapter_exceptions import ClientConnectionException
from axonius.devices.device_adapter import DeviceAdapter, AGENT_NAMES
from axonius.utils.files import get_local_config_file
from axonius.clients.rest.exception import RESTException
from fireeye_hx_adapter.connection import FireeyeHxConnection
from fireeye_hx_adapter import consts
from axonius.utils.datetime import parse_date
from axonius.clients.rest.connection import RESTConnection


class FireeyeHxAdapter(AdapterBase):
    class MyDeviceAdapter(DeviceAdapter):
        pass

    def __init__(self, *args, **kwargs):
        super().__init__(config_file_path=get_local_config_file(__file__), *args, **kwargs)

    def _get_client_id(self, client_config):
        return client_config['domain']

    def _test_reachability(self, client_config):
        return RESTConnection.test_reachability(client_config.get("domain"), client_config.get("port"))

    def _connect_client(self, client_config):
        try:
            connection = FireeyeHxConnection(domain=client_config["domain"], verify_ssl=client_config["verify_ssl"],
                                             username=client_config["username"], password=client_config["password"],
                                             url_base_prefix="hx/api/v3",
                                             port=client_config.get("port", consts.DEFAULT_PORT),
                                             headers={'Content-Type': 'application/json', 'Accept': 'application/json'})
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
        Get all devices from a specific  domain

        :param str client_name: The name of the client
        :param obj client_data: The data that represent a connection

        :return: A json with all the attributes returned from the Server
        """
        try:
            client_data.connect()
            yield from client_data.get_device_list()
        finally:
            client_data.close()

    def _clients_schema(self):
        """
        The schema FireeyeHxAdapter expects from configs

        :return: JSON scheme
        """
        return {
            "items": [
                {
                    "name": "domain",
                    "title": "FireeyeHx Domain",
                    "type": "string"
                },
                {
                    "name": "port",
                    "title": "Port",
                    "type": "integer",
                    "format": "port"
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
                device.id = device_raw.get("_id", "")
                if device.id == "":
                    continue
                try:
                    ip_address = device_raw.get("primary_ip_address") or ""
                    mac_address = device_raw.get("primary_mac")
                    device.add_nic(mac_address, ip_address.split(","))
                except Exception:
                    logger.exception(f"Problem getting nic for {device_raw}")
                try:
                    device.last_seen = parse_date(str(device_raw.get("last_audit_timestamp")))
                except Exception:
                    logger.exception(f"Problem getting last seen for {device_raw}")
                try:
                    os_raw = device_raw.get("os")
                    device.figure_os((os_raw.get("product_name") or "") + " " + (os_raw.get("bitness") or ""))
                except Exception:
                    logger.exception(f"Problem getting os for {device_raw}")
                device.add_agent_version(agent=AGENT_NAMES.fireeye_hx, version=device_raw.get('agent_version'))
                try:
                    hostname = device_raw.get("hostname")
                    device.hostname = hostname
                    domain = device_raw.get("domain")
                    if domain is not None and domain != "" and str(domain).lower()\
                            not in ["workgroup", "local", "n/a"] and domain.lower() != hostname.lower():
                        device.domain = domain
                except Exception:
                    logger.exception(f"Problem getting hostname {device_raw}")
                device.time_zone = device_raw.get("timezone")
                device.set_raw(device_raw)
                yield device
            except Exception:
                logger.exception(f"Problem with fetching FireeyeHx Device {device_raw}")

    @classmethod
    def adapter_properties(cls):
        return [AdapterProperty.Endpoint_Protection_Platform, AdapterProperty.Agent, AdapterProperty.Manager]
