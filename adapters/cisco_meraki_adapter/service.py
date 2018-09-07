import logging
logger = logging.getLogger(f'axonius.{__name__}')
from axonius.adapter_base import AdapterBase, AdapterProperty
from axonius.adapter_exceptions import ClientConnectionException
from axonius.devices.device_adapter import DeviceAdapter, SmartJsonClass
from axonius.utils.files import get_local_config_file
from axonius.fields import Field, ListField
from collections import defaultdict
from cisco_meraki_adapter.connection import CiscoMerakiConnection
from cisco_meraki_adapter.exceptions import CiscoMerakiException
from axonius.utils.parsing import parse_date
from axonius.clients.rest.connection import RESTConnection


class AssociatedDeviceAdapter(SmartJsonClass):
    switch_port = Field(str, "Switch Port")
    associated_device = Field(str, "Associated Device")
    address = Field(str, "Address")
    network_name = Field(str, "Network Name")
    vlan = Field(str, "Vlan")


class CiscoMerakiAdapter(AdapterBase):

    class MyDeviceAdapter(DeviceAdapter):
        device_type = Field(str, "Device Type", enum=["Client Device", "Cisco Device"])
        network_id = Field(str, "Network Name")
        lng = Field(str, "Lng")
        lat = Field(str, "Lat")
        address = Field(str, "Address")
        dns_name = Field(str, "DNS Name")
        associated_devices = ListField(AssociatedDeviceAdapter, "Associated Devices")

    def __init__(self, *args, **kwargs):
        super().__init__(config_file_path=get_local_config_file(__file__), *args, **kwargs)

    def _get_client_id(self, client_config):
        return client_config['CiscoMeraki_Domain']

    def _test_reachability(self, client_config):
        return RESTConnection.test_reachability(client_config.get('CiscoMeraki_Domain'))

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
                if (device_raw.get("lanIp") or "") != "":
                    ip_addresses.append(device_raw.get("lanIp"))
                if (device_raw.get("wan1Ip") or "") != "":
                    ip_addresses.append(device_raw.get("wan1Ip"))
                if (device_raw.get("wan12p") or "") != "":
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

        clients_id_dict = dict()
        for client_raw in clients_raw_date:
            try:
                for key in client_raw:
                    if client_raw[key] is not None:
                        client_raw[key] = str(client_raw[key])
                device_id = client_raw.get("id") or ""
                if device_id == "":
                    logger.info(f"No ID for device: {client_raw}")
                    continue

                # fix ips
                if 'ip' in client_raw and client_raw['ip']:
                    client_raw['ip'] = set(client_raw['ip'].split(","))
                else:
                    client_raw['ip'] = set()

                if device_id not in clients_id_dict:
                    clients_id_dict[device_id] = client_raw
                    clients_id_dict[device_id]['associated_devices'] = set()
                clients_id_dict[device_id]['ip'].union(client_raw['ip'])
                clients_id_dict[device_id]['associated_devices'].add(
                    (client_raw.get('associated_device'), client_raw.get('switchport'),
                     client_raw.get('address'), client_raw.get('network_name'),
                     client_raw.get('vlan')))

            except Exception:
                logger.exception(f"Problem with fetching CiscoMeraki Client {client_raw}")
        for client_id, client_raw in clients_id_dict.items():
            try:
                client_raw["associated_devices"] = list(client_raw["associated_devices"])
                client_raw["ip"] = list(filter(lambda ip: isinstance(ip, str), client_raw["ip"]))
                device = self._new_device_adapter()
                device.id = client_id
                device.device_type = "Client Device"
                mac_address = client_raw.get('mac') or ""
                device.hostname = client_raw.get('dhcpHostname')
                try:
                    ip_addresses = list(client_raw.get("ip"))
                    if ip_addresses != [] or mac_address != "":
                        device.add_nic(mac_address, ip_addresses)
                except Exception:
                    logger.exception(f"Problem with fetching NIC in CiscoMeraki Client {client_raw}")
                device.description = client_raw.get("description")
                device.dns_name = client_raw.get("mdnsName")
                device.associated_devices = []
                for associated_device, switch_port, address, network_name, vlan in client_raw["associated_devices"]:
                    try:
                        associated_device_object = AssociatedDeviceAdapter()
                        associated_device_object.switch_port = switch_port
                        associated_device_object.associated_device = associated_device
                        associated_device_object.address = address
                        associated_device_object.network_name = network_name
                        associated_device_object.vlan = vlan
                        device.associated_devices.append(associated_device_object)
                    except Exception:
                        logger.exception(f"Problem adding associated device"
                                         f" {str(associated_device)} with port {str(switch_port)}")
                device.set_raw(client_raw)
                yield device
            except Exception:
                logger.exception(f"Problem with fetching CiscoMeraki Client {str(client_raw)}")

    @classmethod
    def adapter_properties(cls):
        return [AdapterProperty.Network]
