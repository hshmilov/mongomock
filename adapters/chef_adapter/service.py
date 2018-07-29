import logging

logger = logging.getLogger(f"axonius.{__name__}")
import datetime
import pytz

from axonius.adapter_base import AdapterBase, AdapterProperty
from axonius.adapter_exceptions import ClientConnectionException
from axonius.devices.device_adapter import DeviceAdapter
from axonius.utils.parsing import format_mac, is_valid_ip
from axonius.utils.files import get_local_config_file
from chef_adapter.exceptions import ChefException
from chef_adapter.connection import ChefConnection
from axonius.fields import Field, JsonStringFormat, ListField
from axonius.utils.parsing import format_ip

CHEF_DOMAIN = 'domain'
ORGANIZATION = 'organization'
CLIENT_KEY = 'client_key'
CLIENT = 'client'
SSL_VERIFY = 'ssl_verify'


class ChefAdapter(AdapterBase):
    class MyDeviceAdapter(DeviceAdapter):
        environment = Field(str, "Chef environment")
        instance_id = Field(str, "AWS instance ID")
        public_ip = Field(str, 'Discovered public ip', converter=format_ip, json_format=JsonStringFormat.ip)
        chef_tags = ListField(str, 'Chef tags')

    def __init__(self):
        super().__init__(get_local_config_file(__file__))

    def _get_client_id(self, client_config):
        return client_config[CHEF_DOMAIN]

    def _connect_client(self, client_config):
        try:
            connection = ChefConnection(client_config[CHEF_DOMAIN], client_config[ORGANIZATION],
                                        self._grab_file_contents(client_config[CLIENT_KEY]), client_config[CLIENT],
                                        client_config[SSL_VERIFY])
            with connection:
                pass
            return connection
        except ChefException as e:
            message = "Error connecting to client with domain {0}, reason: {1}".format(
                client_config[CHEF_DOMAIN], str(e))
            logger.exception(message)
            raise ClientConnectionException(message)

    def _query_devices_by_client(self, client_name, client_data):
        """
        Get all devices from a specific Chef domain

        :param str client_name: The name of the client
        :param obj client_data: The data that represent a Chef connection

        :return: A json with all the attributes returned from the Chef Server
        """
        return client_data.get_devices()

    def _clients_schema(self):
        """
        The schema ChefAdapter expects from configs

        :return: JSON scheme
        """
        return {
            "items": [
                {
                    "name": CHEF_DOMAIN,
                    "title": "Chef Domain",
                    "type": "string"
                },
                {
                    "name": ORGANIZATION,
                    "title": "Organization",
                    "type": "string",
                },
                {
                    "name": CLIENT_KEY,
                    "title": "Client Key File (pem)",
                    "description": "The binary contents of the key_file",
                    "type": "file"
                },
                {
                    "name": CLIENT,
                    "title": "Client",
                    "type": "string",
                },
                {  # if false, it will allow for invalid SSL certificates (but still uses HTTPS)
                    "name": SSL_VERIFY,
                    "title": "Verify SSL Certificate",
                    "type": "bool",
                    "default": False
                }
            ],
            "required": [
                CHEF_DOMAIN,
                ORGANIZATION,
                CLIENT_KEY,
                CLIENT
            ],
            "type": "array"
        }

    def _parse_raw_data(self, devices_raw_data):
        for device_raw in devices_raw_data:
            try:
                device = self._new_device_adapter()
                device.name = device_raw['name']  # exception is thrown and logged if we don't have an id
                device.id = device.name
                device.environment = device_raw.get('chef_environment')
                device_raw_automatic = device_raw.get('automatic')
                device.figure_os(' '.join([(device_raw_automatic.get('platform_family') or ''),
                                           (device_raw_automatic.get('platform') or ''),
                                           (device_raw_automatic.get('platform_version') or ''),
                                           ((device_raw_automatic.get('hostnamectl') or {}).get(
                                               'architecture') or '')]))

                device.hostname = (device_raw_automatic.get('cloud') or {}).get(
                    'local_hostname') or device_raw_automatic.get('fqdn')
                device.instance_id = (device_raw_automatic.get('ec2') or {}).get('instance_id')
                try:
                    device.last_seen = datetime.datetime.fromtimestamp(device_raw_automatic['ohai_time'])
                except Exception:
                    logger.exception(f"something is really wrong with the device"
                                     f" - chef doesn't have a last check-in for it {device_raw}")
                device.time_zone = (device_raw_automatic.get('time') or {}).get('timezone')
                try:
                    if device.time_zone:
                        device.last_seen = pytz.timezone(device.time_zone).localize(device.last_seen).astimezone(
                            pytz.UTC)
                except Exception:
                    logger.exception(f'Error adjusting timezone {device_raw}')
                # domain assign won't work for cloud clients (but hostname will contain the domain)
                device.domain = device_raw_automatic.get('domain')
                try:
                    for software_name, software_params in (device_raw_automatic.get("packages") or {}).items():
                        device.add_installed_software(name=software_name,
                                                      version=' '.join([(software_params.get('version') or ''),
                                                                        (software_params.get('release') or '')]))
                except Exception:
                    logger.exception(f"Problem with adding software to Chef client {device_raw}")
                try:
                    for software_name, software_params in (device_raw_automatic.get("chef_packages") or {}).items():
                        device.add_installed_software(name=software_name,
                                                      vendor='chef',
                                                      version=(software_params.get('version') or ''))
                except Exception:
                    logger.exception(f"Problem with adding software on chef pachages to Chef client {device_raw}")
                dmi = device_raw_automatic.get('dmi') or {}
                systeminfo = dmi.get('system')
                device.device_manufacturer = systeminfo.get('manufacturer')
                device.device_model = systeminfo.get('product_name')
                device.device_model_family = systeminfo.get('family')
                device.device_serial = systeminfo.get('serial_number')
                try:
                    cpus = device_raw_automatic.get('cpu') or {}
                    device.total_number_of_cores = cpus.get('total')
                    device.total_number_of_physical_processors = cpus.get('real')
                except Exception:
                    logger.exception(f"Problem getting CPUs for {device_raw}")
                try:
                    for cpu in (cpus or {}).items():
                        if 'core_id' in cpu:
                            device.add_cpu(name=cpu.get('model_name'),
                                           ghz=float(cpu.get('mhz') or 0) / 1024.0)
                except Exception:
                    logger.exception(f"Problem with adding CPU to Chef client {device_raw}")
                try:
                    device.boot_time = device.last_seen - \
                        datetime.timedelta(seconds=(device_raw_automatic.get('uptime_seconds') or 0))
                    biosinfo = dmi.get('bios') or {}
                    device.bios_version = ', '.join(['Vendor: ' + (biosinfo.get('vendor') or ''),
                                                     'Version: ' + (biosinfo.get('version') or ''),
                                                     'BIOS Revision: ' + (biosinfo.get('bios_revision') or ''),
                                                     'Firmware Revision: ' + (biosinfo.get('firmware_revision') or '')])
                    memory = device_raw_automatic.get('memory') or {}
                    device.total_physical_memory = float((memory.get('total') or '0kb')[:-2]) / 1024.0 / 1024.0
                    device.free_physical_memory = float((memory.get('free') or '0kb')[:-2]) / 1024.0 / 1024.0
                    if device.total_physical_memory:
                        device.physical_memory_percentage = 100 * device.free_physical_memory / device.total_physical_memory
                except Exception:
                    logger.exception(f"Problem getting memory or boot time for chef device {device_raw}")
                try:
                    for name, iface in ((device_raw_automatic.get('network') or {}).get('interfaces') or {}).items():
                        ip_addrs = []
                        mac = None
                        for addr, params in (iface.get('addresses') or {}).items():
                            if is_valid_ip(addr):
                                ip_addrs.append(addr)
                            else:
                                mac = format_mac(addr)
                        device.add_nic(mac=mac, ips=ip_addrs)
                except Exception:
                    logger.exception(f"Problem with adding nic to Chef client {device_raw}")

                # MongoDB can only store up to 8-byte ints :(
                try:
                    ((device_raw.get('automatic') or {}).get('sysconf') or {}).pop('ULONG_MAX')
                except Exception:
                    logger.exception(f"Problem with pop of sys conf at {device_raw}")

                try:
                    device.public_ip = device_raw['automatic']['public_ip']['data']['ip']
                    device.chef_tags = device_raw['normal']['tags']
                except Exception:
                    logger.exception(f"Problem adding public ips or tage for {device_raw}")

                device.set_raw(device_raw)

                yield device
            except Exception:
                logger.exception(f'Failed to parse device')

    @classmethod
    def adapter_properties(cls):
        return [AdapterProperty.Agent]
