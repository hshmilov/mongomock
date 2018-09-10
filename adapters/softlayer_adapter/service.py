import logging

import ipaddress

from axonius.mixins.configurable import Configurable
from axonius.smart_json_class import SmartJsonClass
from axonius.utils.parsing import parse_date

logger = logging.getLogger(f'axonius.{__name__}')
from datetime import datetime

from axonius.adapter_base import AdapterBase, AdapterProperty
from axonius.adapter_exceptions import ClientConnectionException
from axonius.devices.device_adapter import DeviceAdapter
from axonius.utils.files import get_local_config_file
from softlayer_adapter.exceptions import SoftlayerException
from softlayer_adapter.connection import SoftlayerConnection
from axonius.fields import Field, ListField
from axonius.clients.rest.connection import RESTConnection

USERNAME = 'username'
API_KEY = 'api_key'
ENDPOINT_URL = 'endpoint_url'
PROXY = 'proxy'
SSL_VERIFY = 'verify'


class SoftlayerVlan(SmartJsonClass):
    """ A definition for a vlan field"""
    id = Field(str, "vLAN ID")
    network_space = Field(str, "vLAN Space")
    number = Field(str, "vLAN Number")


class SoftlayerAdapter(AdapterBase, Configurable):

    class MyDeviceAdapter(DeviceAdapter):
        global_identifier = Field(str, "Global Identifier")
        datacenter = Field(str, "Datacenter")
        status = Field(str, 'Status')
        vlans = ListField(SoftlayerVlan, "SoftLayer vLANs")
        provision_date = Field(datetime, "Provision Date")
        # this could have included the password but we decided not to save them
        remote_management_accounts = ListField(str, "Remote Management Users")
        softlayer_tags = ListField(str, "Tags")
        notes = Field(str, "Notes")

    def __init__(self):
        super().__init__(get_local_config_file(__file__))

    def _get_client_id(self, client_config):
        return client_config[USERNAME]

    def _test_reachability(self, client_config):
        return RESTConnection.test_reachability('https://api.softlayer.com/xmlrpc/v3/')

    def _connect_client(self, client_config):
        try:
            connection = SoftlayerConnection(client_config[USERNAME], client_config[API_KEY],
                                             client_config.get(ENDPOINT_URL), client_config.get(PROXY),
                                             client_config.get(SSL_VERIFY),
                                             self.num_of_simultaneous_devices)
            with connection:
                pass
            return connection
        except SoftlayerException as e:
            message = "Error connecting to client with username {0}, reason: {1}".format(
                client_config[USERNAME], str(e))
            logger.exception(message)
            raise ClientConnectionException(message)

    def _query_devices_by_client(self, client_name, client_data):
        """
        Get all devices from a specific SoftLayer domain

        :param str client_name: The name of the client
        :param obj client_data: The data that represent a SoftLayer connection

        :return: A json with all the attributes returned from the SoftLayer Server
        """
        return client_data.get_devices()

    def _clients_schema(self):
        """
        The schema SoftLayerAdapter expects from configs

        :return: JSON scheme
        """
        return {
            "items": [
                {
                    "name": USERNAME,
                    "title": "Username (Default SLXXXXXXX)",
                    "type": "string"
                },
                {
                    "name": API_KEY,
                    "title": "API Key",
                    "type": "string",
                    "format": "password"
                },
                {
                    "name": ENDPOINT_URL,
                    "title": "Endpoint URL",
                    "type": "string",
                    "default": 'https://api.service.softlayer.com/rest/v3.1/'
                },
                {
                    "name": PROXY,
                    "title": "Proxy",
                    "type": "string"
                },
                {  # if false, it will allow for invalid SSL certificates (but still uses HTTPS)
                    "name": SSL_VERIFY,
                    "title": "Verify SSL Certificate",
                    "type": "bool",
                    "default": True
                }
            ],
            "required": [
                USERNAME,
                API_KEY
            ],
            "type": "array"
        }

    def _parse_raw_data(self, devices_raw_data):
        """
        Here we parse both of the types of devices returned from ibm cloud
        1. BareMetal device
        2. Virtual device
        They have different fields hence you might see device_raw.get(x) or device_raw.get(y)
        for example
            device.total_physical_memory = device_raw.get('memoryCapacity') or \
                (device_raw.get('maxMemory') or 0) / 1024.0
        the first is the baremetal field returned in GB and the latter is the virtual one returned in MB
        """
        for device_raw in devices_raw_data:
            device = self._new_device_adapter()
            device.id = device_raw.get('id')
            device.cloud_id = device_raw.get('id')
            device.cloud_provider = 'Softlayer'
            if device.id is None:
                logger.error(f"Softlayer device without an id {device_raw}")
                continue
            device.name = device_raw.get('fullyQualifiedDomainName')
            device.hostname = device_raw.get('fullyQualifiedDomainName')
            operating_system = (((device_raw.get('operatingSystem') or {}).get('softwareLicense') or {}).get(
                'softwareDescription') or {})
            device.figure_os(' '.join([(operating_system.get('manufacturer') or ''),
                                       (operating_system.get('name') or ''),
                                       (operating_system.get('referenceCode') or ''),
                                       (operating_system.get('version') or '')]))

            device.global_identifier = device_raw.get('globalIdentifier')
            # domain assign won't work for cloud clients (but hostname will contain the domain)
            device.domain = device_raw.get('domain')

            device.total_number_of_cores = device_raw.get('processorPhysicalCoreAmount') or device_raw.get('maxCpu')

            device.total_physical_memory = device_raw.get(
                'memoryCapacity') or (device_raw.get('maxMemory') or 0) / 1024.0
            try:
                for iface in (device_raw.get('networkComponents') or []):
                    try:
                        netmask = (iface.get('primarySubnet') or {}).get('netmask')
                        ip_address = iface.get('ipmiIpAddress') or iface.get('primaryIpAddress')
                        ips = None
                        interfaces = None
                        if ip_address:
                            ips = [ip_address]
                        try:
                            if ip_address and netmask:
                                interfaces = [ipaddress.ip_interface(ip_address + '/' + netmask).with_prefixlen]
                        except Exception:
                            logger.exception(f'Problem adding interface to nic {nic}')
                        mac_address = (iface.get('macAddress') or iface.get('ipmiMacAddress'))
                        if not mac_address:
                            mac_address = None
                        device.add_nic(mac=mac_address,
                                       ips=ips,
                                       subnets=interfaces,
                                       name=iface.get('name'))
                    except Exception:
                        logger.exception(f"Problem with adding nic: {iface} to SoftLayer device")
            except Exception:
                logger.exception(f"Problem with all interfaces to SoftLayer device")

            device.datacenter = (device_raw.get('datacenter') or {}).get('longName')
            device.status = (device_raw.get('hardwareStatus') or {}).get('status') or \
                            (device_raw.get('status') or {}).get('name')
            try:
                for vlan in (device_raw.get('networkVlans') or []):
                    device.vlans.append(SoftlayerVlan(id=vlan.get('id'),
                                                      network_space=vlan.get('networkSpace'),
                                                      number=vlan.get('vlanNumber')))
            except Exception:
                logger.exception(f"Problem with adding vlan {vlan} to SoftLayer device")

            try:
                for account in (device_raw.get('remoteManagementAccounts') or []):
                    device.remote_management_accounts.append(account.get('username'))
            except Exception:
                logger.exception(f"Problem with adding management account {account} to SoftLayer device")

            device.provision_date = parse_date(device_raw.get('provisionDate'))
            for tag in (device_raw.get('tagReferences') or []):
                device.softlayer_tags.append((tag.get('tag') or {}).get('name'))
            device.notes = device_raw.get('notes')

            device.set_raw(device_raw)
            yield device

    @classmethod
    def _db_config_schema(cls) -> dict:
        return {
            "items": [
                {
                    "name": "num_of_simultaneous_devices",
                    "title": "Numer of simultaneous threads",
                    "type": "number"
                }
            ],
            "required": [
                "num_of_simultaneous_devices"
            ],
            "pretty_name": "IBM Cloud Configuration",
            "type": "array"
        }

    @classmethod
    def _db_config_default(cls):
        return {
            "num_of_simultaneous_devices": 50
        }

    def _on_config_update(self, config):
        self.num_of_simultaneous_devices = config['num_of_simultaneous_devices']

    @classmethod
    def adapter_properties(cls):
        return [AdapterProperty.Assets]
