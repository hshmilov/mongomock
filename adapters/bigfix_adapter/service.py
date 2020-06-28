import logging
import xml.etree.ElementTree as ET


from axonius.adapter_base import AdapterBase, AdapterProperty
from axonius.adapter_exceptions import ClientConnectionException
from axonius.clients.rest.connection import RESTConnection
from axonius.clients.rest.exception import RESTException
from axonius.clients.xml.connection import parse_xml_from_string
from axonius.devices.device_adapter import DeviceAdapter, AGENT_NAMES
from axonius.fields import Field
from axonius.mixins.configurable import Configurable
from axonius.utils.datetime import parse_date
from axonius.utils.files import get_local_config_file
from axonius.utils.parsing import normalize_var_name, is_valid_ipv6
from bigfix_adapter import consts
from bigfix_adapter.connection import BigfixConnection

logger = logging.getLogger(f'axonius.{__name__}')


class BigfixAdapter(AdapterBase, Configurable):

    class MyDeviceAdapter(DeviceAdapter):
        bigfix_device_type = Field(str, 'Device type')
        bigfix_computer_type = Field(str, 'Computer type')
        identify_number = Field(str, 'Identify Number')

    def __init__(self, *args, **kwargs):
        super().__init__(config_file_path=get_local_config_file(__file__), *args, **kwargs)

    def _get_client_id(self, client_config):
        return client_config['domain']

    def _test_reachability(self, client_config):
        return RESTConnection.test_reachability(client_config.get('domain'),
                                                client_config.get('port') or consts.DEFAULT_PORT,
                                                https_proxy=client_config.get('https_proxy'))

    def _connect_client(self, client_config):
        try:
            connection = BigfixConnection(domain=client_config['domain'],
                                          verify_ssl=client_config['verify_ssl'],
                                          username=client_config['username'],
                                          password=client_config['password'],
                                          url_base_prefix='/api/',
                                          https_proxy=client_config.get('https_proxy'),
                                          port=(client_config.get('port') or consts.DEFAULT_PORT))
            with connection:
                pass  # check that the connection credentials are valid
            return connection
        except RESTException as e:
            message = 'Error connecting to client with domain {0}, reason: {1}'.format(
                client_config['domain'], str(e))
            raise ClientConnectionException(message)

    def _query_devices_by_client(self, client_name, client_data):
        """
        Get all devices from a specific Bigfix domain

        :param str client_name: The name of the client
        :param obj client_data: The data that represent a Bigfix connection

        :return: A json with all the attributes returned from the Bigfix Server
        """
        try:
            client_data.connect()

            try:
                mac_dict = client_data.get_query_data_per_device_list('MAC Addresses')
            except Exception:
                mac_dict = dict()
                logger.exception(f'Failed getting mac unix, continuing')
            try:
                aix_installed_software_dict = client_data.get_query_data_per_device_list('Producs in Object Repository'
                                                                                         ' - AIX')
            except Exception:
                aix_installed_software_dict = dict()
                logger.exception(f'Failed getting aix installed software list, continuing')
            try:
                linux_installed_software_dict = client_data.get_query_data_per_device_list('Packages Installed '
                                                                                           '- Linux')
            except Exception:
                linux_installed_software_dict = dict()
                logger.exception(f'Failed getting linux installed software list, continuing')
            try:
                installed_software_dict = client_data.get_query_data_per_device_list('Installed Applications')
            except Exception:
                installed_software_dict = dict()
                logger.exception(f'Failed getting installed software list, continuing')
            try:
                identify_dict = client_data.get_query_data_per_device_list('Identifying Number')
            except Exception:
                identify_dict = dict()
                logger.exception(f'Failed getting identify, continuing')

            try:
                manufacturer_dict = client_data.get_query_data_per_device_list('Manufacturer')
            except Exception:
                manufacturer_dict = dict()
                logger.exception(f'Failed getting manufacturer_dict, continuing')

            try:
                model_dict = client_data.get_query_data_per_device_list('Model')
            except Exception:
                model_dict = dict()
                logger.exception(f'Failed getting model_dict, continuing')

            for device_raw in client_data.get_device_list():
                yield device_raw, installed_software_dict, identify_dict, \
                    manufacturer_dict, model_dict, linux_installed_software_dict, \
                    mac_dict, aix_installed_software_dict
        finally:
            client_data.close()

    def _clients_schema(self):
        """
        The schema BigfixAdapter expects from configs

        :return: JSON scheme
        """
        return {
            'items': [
                {
                    'name': 'domain',
                    'title': 'Bigfix Domain',
                    'type': 'string'
                },
                {
                    'name': 'port',
                    'title': 'Port',
                    'type': 'integer',
                    'format': 'port'
                },
                {
                    'name': 'username',
                    'title': 'User Name',
                    'type': 'string'
                },
                {
                    'name': 'password',
                    'title': 'Password',
                    'type': 'string',
                    'format': 'password'
                },
                {
                    'name': 'verify_ssl',
                    'title': 'Verify SSL',
                    'type': 'bool'
                },
                {
                    'name': 'https_proxy',
                    'title': 'HTTPS Proxy',
                    'type': 'string'
                }
            ],
            'required': [
                'domain',
                'username',
                'password',
                'verify_ssl'
            ],
            'type': 'array'
        }

    def _parse_raw_data(self, devices_raw_data):
        for device_raw_xml, computer_id_to_installed_software, identify_dict,\
            manufacturer_dict, model_dict, linux_installed_software_dict, \
            mac_dict, aix_installed_software_dict in \
                devices_raw_data:
            try:
                device_raw = dict()
                for xml_property in parse_xml_from_string(device_raw_xml.encode('utf-8'))[0]:
                    try:
                        if xml_property.tag == 'Property':
                            if xml_property.attrib['Name'] in device_raw:
                                device_raw[xml_property.attrib['Name']] += ',' + str(xml_property.text)
                            else:
                                device_raw[xml_property.attrib['Name']] = str(xml_property.text)
                    except Exception:
                        logger.exception('Cant parse some xml properties')
                device = self._new_device_adapter()
                if not device_raw.get('ID'):
                    continue
                else:
                    device_id = device_raw.get('ID')
                    device.id = str(device_id)
                dns_name = device_raw.get('DNS Name')
                computer_name = device_raw.get('Computer Name')

                try:
                    if computer_name is not None and dns_name is not None:
                        if dns_name.lower().startswith(computer_name.lower()):
                            device.hostname = dns_name
                        else:
                            device.hostname = dns_name
                            device.name = computer_name
                    else:
                        device.hostname = computer_name or dns_name
                except Exception:
                    logger.exception(f'Failed to parse hostname: '
                                     f'dns name is {str(dns_name)} and computer name is {str(computer_name)}')
                try:
                    hostname_for_id = device.hostname
                    device.id = device.id + '_' + hostname_for_id
                except Exception:
                    pass
                try:
                    device.figure_os((device_raw.get('OS') or '') + ' ' + (device_raw.get('Device Type') or ''))
                except Exception:
                    logger.warning(f'Problem with figure os {device_raw}', exc_info=True)
                try:
                    try:
                        mac_key = None
                        for key_raw in device_raw:
                            if 'mac addresses' in key_raw.lower():
                                mac_key = key_raw
                                break
                        mac_addresses = []
                        if mac_key:
                            if ';' in device_raw[mac_key]:
                                mac_addresses = device_raw[mac_key].split(';')
                            else:
                                mac_addresses = device_raw[mac_key].split(',')
                        mac_addresses = [mac_address.strip() for mac_address in mac_addresses]
                    except Exception:
                        mac_addresses = []
                        logger.exception(f'Problem getting mac for {device_raw}')
                    ips = (device_raw.get('IP Address') or '').split(',') + \
                          (device_raw.get('IPv6 Address') or '').split(',')
                    ips = [ip.strip() for ip in ips]
                    if self.__exclude_ipv6:
                        ips = [ip for ip in ips if not is_valid_ipv6(ip)]
                    device.add_ips_and_macs(mac_addresses, ips)
                except Exception:
                    logger.exception('Problem adding nic to Bigfix')
                device.add_agent_version(agent=AGENT_NAMES.bigfix, version=device_raw.get('Agent Version'))
                if isinstance(device_raw.get('User Name'), str) and '<none>' not in device_raw.get('User Name'):
                    device.last_used_users = device_raw.get('User Name').split(',')
                last_report_time = device_raw.get('Last Report Time')
                try:
                    device.last_seen = parse_date(last_report_time)
                except Exception:
                    logger.exception(f'Failure parsing last seen date: {last_report_time}')
                device.bigfix_device_type = device_raw.get('Device Type')
                device.bigfix_computer_type = device_raw.get('Computer Type')
                device.device_serial = device_raw.get('Serial')
                try:
                    for key_name in device_raw:
                        try:
                            normalized_key_name = 'bigfix_' + normalize_var_name(key_name)
                            if not device.does_field_exist(normalized_key_name):
                                cn_capitalized = ' '.join([word.capitalize() for word in key_name.split(' ')])
                                device.declare_new_field(normalized_key_name, Field(str, f'Bigfix {cn_capitalized}'))

                            device[normalized_key_name] = str(device_raw.get(key_name))\
                                if device_raw.get(key_name) is not None else None
                        except Exception:
                            logger.exception(f'Problem adding key {key_name}')
                except Exception:
                    logger.exception(f'Problem adding fields to {device_raw}')

                try:
                    manufacturer_list = manufacturer_dict.get(str(device_id))
                    if manufacturer_list:
                        device.device_manufacturer = manufacturer_list[0]
                except Exception:
                    logger.exception(f'Problem with manufacture for {device_raw}')

                try:
                    model_list = model_dict.get(str(device_id))
                    if model_list:
                        device.device_model = model_list[0]
                except Exception:
                    logger.exception(f'Problem with model for {device_raw}')
                try:
                    aix_list = aix_installed_software_dict.get(str(device_id))
                    if isinstance(aix_list, list):
                        for aix_str in aix_list:
                            device.add_installed_software(
                                name=aix_str.strip()
                            )
                except Exception:
                    logger.exception(f'Problem with aix sw for {device_raw}')
                try:
                    linux_list = linux_installed_software_dict.get(str(device_id))
                    if isinstance(linux_list, list):
                        for linux_str in linux_list:
                            try:
                                name, version = linux_str.split('|')
                            except ValueError:
                                name = linux_str
                                version = ''
                            device.add_installed_software(
                                name=name.strip(),
                                version=version.strip()
                            )
                except Exception:
                    logger.exception(f'Problem with linux sw for {device_raw}')
                try:
                    mac_list = mac_dict.get(str(device_id))
                    if isinstance(mac_list, list):
                        for mac_str in mac_list:
                            if isinstance(mac_str, str):
                                mac = mac_str.split(': ')[-1]
                                device.add_nic(mac=mac)
                except Exception:
                    logger.exception(f'Problem with MAC address')

                try:
                    identify_list = identify_dict.get(str(device_id))
                    if identify_list:
                        device.identify_number = identify_list[0]
                except Exception:
                    logger.exception(f'Problem with idetify number for {device_raw}')
                try:
                    for installed_software in computer_id_to_installed_software.get(str(device_id)) or []:
                        try:
                            try:
                                name, version = installed_software.split('|')
                            except ValueError:
                                name = installed_software
                                version = ''
                            device.add_installed_software(
                                name=name.strip(),
                                version=version.strip()
                            )
                        except Exception:
                            logger.exception(f'Problem adding installed software {installed_software}')
                except Exception:
                    logger.exception(f'Problem adding installed software list')
                device.set_raw(device_raw)
                yield device
            except Exception:
                logger.exception(f'Problem with fetching Bigfix Device {device_raw}')

    @classmethod
    def adapter_properties(cls):
        return [AdapterProperty.Agent]

    @classmethod
    def _db_config_schema(cls) -> dict:
        return {
            "items": [
                {
                    'name': 'exclude_ipv6',
                    'title': 'Exclude IPv6 addresses',
                    'type': 'bool'
                }
            ],
            "required": ['exclude_ipv6'],
            "pretty_name": "Bigfix Configuration",
            "type": "array"
        }

    @classmethod
    def _db_config_default(cls):
        return {
            'exclude_ipv6': False
        }

    def _on_config_update(self, config):
        self.__exclude_ipv6 = config['exclude_ipv6']
