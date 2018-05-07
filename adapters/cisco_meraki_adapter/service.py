import logging
logger = logging.getLogger(f"axonius.{__name__}")
from axonius.adapter_base import AdapterBase, AdapterProperty
from axonius.adapter_exceptions import ClientConnectionException
from axonius.devices.device_adapter import DeviceAdapter
from axonius.utils.files import get_local_config_file
from axonius.fields import Field

from cisco_meraki_adapter.connection import CiscoMerakiConnection
from cisco_meraki_adapter.exceptions import CiscoMerakiException
from axonius.utils.parsing import parse_date


class CiscoMerakiAdapter(AdapterBase):

    class MyDeviceAdapter(DeviceAdapter):
        device_type = Field(str, "Device Type")
        network_id = Field(str, "Network Name")
        lng = Field(str, "Lng")
        lat = Field(str, "Lat")
        address = Field(str, "Address")
        description = Field(str, "Description")
        switch_port = Field(str, "Switch Port")
        dns_name = Field(str, "DNS Name")
        associated_device = Field(str, "Associated Device")

    def __init__(self, *args, **kwargs):
        super().__init__(config_file_path=get_local_config_file(__file__), *args, **kwargs)

    def _get_client_id(self, client_config):
        return client_config['CiscoMeraki_Domain']

    def _connect_client(self, client_config):
        try:
            connection = CiscoMerakiConnection(domain=client_config["CiscoMeraki_Domain"], apikey=client_config["apikey"],
                                               verify_ssl=client_config["verify_ssl"])
            with connection:
                pass  # check that the connection credentials are valid
            return connection
        except CiscoMerakiException as e:
            message = "Error connecting to client with domain {0}, reason: {1}".format(
                client_config['CiscoMeraki_Domain'], str(e))
            logger.exception(message)
            raise ClientConnectionException(message)

    def _query_devices_by_client(self, client_name, client_data):
        """
        Get all devices from a specific CiscoMeraki domain

        :param str client_name: The name of the client
        :param obj client_data: The data that represent a CiscoMeraki connection

        :return: A json with all the attributes returned from the CiscoMeraki Server
        """
        with client_data:
            return client_data.get_device_list()

    def _clients_schema(self):
        """
        The schema CiscoMerakiAdapter expects from configs

        :return: JSON scheme
        """
        return {
            "items": [
                {
                    "name": "CiscoMeraki_Domain",
                    "title": "CiscoMeraki Domain",
                    "type": "string"
                },
                {
                    "name": "apikey",
                    "title": "Apikey",
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
                "CiscoMeraki_Domain",
                "apikey",
                "verify_ssl"
            ],
            "type": "array"
        }

    def _parse_raw_data(self, devices_clients_raw_data):
        devices_raw_data = devices_clients_raw_data.get('devices', [])
        clients_raw_date = devices_clients_raw_data.get('clients', [])
        for device_raw in devices_raw_data:
            try:
                for key in device_raw:
                    if device_raw[key] is not None:
                        device_raw[key] = str(device_raw[key])
                device = self._new_device_adapter()
                device.device_serial = device_raw.get('serial', "")
                if device.device_serial == "":
                    continue
                mac_address = device_raw.get('mac', "")
                device.id = device.device_serial
                device.device_type = "Cisco Device"
                device.device_model = device_raw.get("model")
                device.name = device_raw.get('name')
                ip_addresses = []
                if device_raw.get("lanIp", "") != "":
                    ip_addresses.append(device_raw.get("lanIp", ""))
                if device_raw.get("wan1Ip", "") != "":
                    ip_addresses.append(device_raw.get("wan1Ip", ""))
                if device_raw.get("wan12p", "") != "":
                    ip_addresses.append(device_raw.get("wan12p", ""))
                if ip_addresses == []:
                    ip_addresses = None
                device.add_nic(mac_address, ip_addresses)
                # These values are the geo location of the Cisco Meraki device
                device.lat = device_raw.get("lat")
                device.lng = device_raw.get("lng")
                device.address = device_raw.get("address")
                device.network_id = device_raw.get("network_name")
                device.set_raw(device_raw)
                yield device
            except Exception:
                logger.exception("Problem with fetching CiscoMeraki Device")

        for client_raw in clients_raw_date:
            try:
                for key in client_raw:
                    if client_raw[key] is not None:
                        client_raw[key] = str(client_raw[key])
                device = self._new_device_adapter()
                mac_address = client_raw.get('mac', "")
                device.id = client_raw.get("id", "")
                if device.id == "":
                    logger.info(f"No ID for device: {client_raw}")
                    continue
                device.device_type = "Client Device"
                device.hostname = client_raw.get('dhcpHostname')
                ip_address = client_raw.get("ip", "")
                if ip_address != "" or mac_address != "":
                    device.add_nic(mac_address, ip_address.split(","))
                device.description = client_raw.get("description")
                device.switch_port = client_raw.get("switchport")
                device.dns_name = client_raw.get("mdnsName")
                device.associated_device = client_raw.get("associated_device")
                device.set_raw(client_raw)
                yield device
            except Exception:
                logger.exception("Problem with fetching CiscoMeraki Device")

    @classmethod
    def adapter_properties(cls):
        return [AdapterProperty.Network]
