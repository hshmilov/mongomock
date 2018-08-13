import logging
logger = logging.getLogger(f'axonius.{__name__}')
from collections import defaultdict
from axonius.adapter_base import AdapterBase, AdapterProperty
from axonius.adapter_exceptions import ClientConnectionException
from axonius.scanner_adapter_base import ScannerAdapterBase
from axonius.utils.files import get_local_config_file
from axonius.fields import Field, ListField
from axonius.clients.rest.exception import RESTException
from tenable_io_adapter.connection import TenableIoConnection
from axonius.utils.parsing import parse_date
from axonius.devices.device_adapter import DeviceAdapter


class TenableIoAdapter(AdapterBase):
    DEFAULT_LAST_SEEN_THRESHOLD_HOURS = None

    class MyDeviceAdapter(DeviceAdapter):
        risk_and_name_list = ListField(str, "Vulnerability Details")

    def __init__(self, *args, **kwargs):
        super().__init__(config_file_path=get_local_config_file(__file__), *args, **kwargs)

    def _get_client_id(self, client_config):
        return client_config['domain']

    def _connect_client(self, client_config):
        try:
            connection = TenableIoConnection(domain=client_config["domain"], verify_ssl=client_config["verify_ssl"],
                                             url_base_prefix="/", headers={'Content-Type': 'application/json',
                                                                           'Accept': 'application/json'},
                                             access_key=client_config.get('access_key'),
                                             secret_key=client_config.get('secret_key'))

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
            return client_data.get_device_list()
        finally:
            client_data.close()

    def _clients_schema(self):
        """
        The schema TenableIOAdapter expects from configs

        :return: JSON scheme
        """
        return {
            "items": [
                {
                    "name": "domain",
                    "title": "TenableIO Domain",
                    "type": "string"
                },
                {
                    "name": "verify_ssl",
                    "title": "Verify SSL",
                    "type": "bool"
                },
                {
                    'name': 'access_key',
                    'title': 'Access API Key (instead of user/password)',
                    'type': 'string',
                    'format': 'password'
                },
                {
                    'name': 'secret_key',
                    'title': 'Secret API key (instead of user/password)',
                    'type': 'string',
                    'format': 'password'
                },

            ],
            "required": [
                "domain",
                "verify_ssl",
                "access_key",
                "secret_key"
            ],
            "type": "array"
        }

    def _parse_raw_data(self, devices_raw_data):
        assets_dict = defaultdict(list)

        def get_csv_value_filtered(d, n):
            try:
                value = d.get(n)
                if value is not None:
                    if str(value).strip().lower() not in ["", "none", "0"]:
                        return str(value).strip()
            except Exception:
                pass

            return None

        for device_raw in devices_raw_data:
            try:
                uuid = get_csv_value_filtered(device_raw, "Asset UUID")
                host = get_csv_value_filtered(device_raw, "Host")

                if uuid is None or host is None:
                    logger.warning(f"Bad asset {device_raw}, continuing")
                    continue
                assets_dict[uuid].append(device_raw)
            except Exception:
                logger.exception(f"Problem with fetching TenableIO Device {device_raw}")
        for asset_id, asset_id_values in assets_dict.items():
            try:
                device = self._new_device_adapter()
                device.id = asset_id

                first_asset = asset_id_values[0]
                try:
                    device.last_seen = parse_date(get_csv_value_filtered(first_asset, "Host End"))
                except Exception:
                    logger.exception(f"Problem getting last seen for {str(first_asset)}")
                ip_addresses = get_csv_value_filtered(first_asset, "IP Address")
                mac_addresses = get_csv_value_filtered(first_asset, "MAC Address")

                # Turn to lists
                ip_addresses = ip_addresses.split(",") if ip_addresses is not None else []
                mac_addresses = mac_addresses.split(",") if mac_addresses is not None else []

                if mac_addresses == [] and ip_addresses != []:
                    device.add_nic(None, ip_addresses)

                else:
                    for mac_address in mac_addresses:
                        device.add_nic(mac_address, ip_addresses)

                fqdn = get_csv_value_filtered(first_asset, "FQDN")
                netbios = get_csv_value_filtered(first_asset, "NetBios")

                if fqdn is not None:
                    device.hostname = fqdn
                else:
                    device.hostname = netbios

                os = get_csv_value_filtered(first_asset, "OS")
                device.figure_os(os)

                risk_and_name_list = []
                for vuln_i in asset_id_values:
                    vrisk = get_csv_value_filtered(vuln_i, "Risk")
                    vname = get_csv_value_filtered(vuln_i, "Name")
                    if vrisk and vname:
                        risk_and_name_list.append(f"{vrisk} - {vname}")

                if len(risk_and_name_list) > 0:
                    device.risk_and_name_list = risk_and_name_list
                first_asset["risk_and_name_list"] = risk_and_name_list
                device.set_raw(first_asset)
                yield device
            except Exception:
                logger.exception(f"Problem with asset id {asset_id} and values {asset_id_values}")

    @classmethod
    def adapter_properties(cls):
        return [AdapterProperty.Network, AdapterProperty.Vulnerability_Assessment]
