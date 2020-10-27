import json
import logging

from axonius.types.enforcement_classes import EntitiesResult, EntityResult
from axonius.clients.service_now.connection import ServiceNowConnection
from reports.action_types.action_type_base import ActionTypeBase, add_node_selection, add_node_default

logger = logging.getLogger(f'axonius.{__name__}')

ADAPTER_NAME = 'service_now_adapter'

# pylint: disable=W0212


class UpdateServicenowComputerAction(ActionTypeBase):
    """
    Updates an computer in the ServiceNow account
    """

    @staticmethod
    def config_schema() -> dict:
        schema = {
            'items': [
                {
                    'name': 'use_adapter',
                    'title': 'Use stored credentials from the ServiceNow adapter',
                    'type': 'bool'
                },
                {
                    'name': 'domain',
                    'title': 'ServiceNow domain',
                    'type': 'string'
                },
                {
                    'name': 'username',
                    'title': 'User name',
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
                    'title': 'HTTPS proxy',
                    'type': 'string'
                },
                {
                    'name': 'extra_fields',
                    'title': 'Additional fields',
                    'type': 'string'
                },
                {
                    'name': 'ax_snow_fields_map',
                    'type': 'string',
                    'title': 'Axonius to ServiceNow field mapping'
                },
                {
                    'name': 'use_first_ip_only',
                    'title': 'Use first IP address only',
                    'type': 'bool'
                },
                {
                    'name': 'ips_delimiter',
                    'title': 'IP addresses delimiter',
                    'type': 'string'
                },
                {
                    'name': 'use_first_mac_only',
                    'title': 'Use first MAC address only',
                    'type': 'bool'
                },
                {
                    'name': 'mac_delimiter',
                    'title': 'MAC addresses delimiter',
                    'type': 'string'
                }
            ],
            'required': [
                'use_adapter',
                'verify_ssl',
                'use_first_ip_only',
                'use_first_mac_only',
            ],
            'type': 'array'
        }
        return add_node_selection(schema)

    @staticmethod
    def default_config() -> dict:
        return add_node_default({
            'use_adapter': False,
            'domain': None,
            'ax_snow_fields_map': None,
            'username': None,
            'password': None,
            'https_proxy': None,
            'extra_fields': None,
            'verify_ssl': True,
            'ips_delimiter': '/',
            'use_first_ip_only': False,
            'mac_delimiter': '/',
            'use_first_mac_only': True
        })

    # pylint: disable=too-many-arguments
    # pylint: disable=too-many-branches
    def _update_service_now_computer(self, class_name, sys_id, name, mac_address=None, ip_address=None,
                                     manufacturer=None, os_type=None, serial_number=None,
                                     extra_fields=None, ax_snow_values_map_dict=None):
        adapter_unique_name = self._plugin_base._get_adapter_unique_name(ADAPTER_NAME, self.action_node_id)
        connection_dict = dict()
        connection_dict['name'] = name
        connection_dict['sys_class_name'] = class_name
        connection_dict['sys_id'] = sys_id
        if mac_address:
            connection_dict['mac_address'] = mac_address
        if ip_address:
            connection_dict['ip_address'] = ip_address
        if manufacturer:
            connection_dict['manufacturer'] = manufacturer
        if serial_number:
            connection_dict['serial_number'] = serial_number
        if os_type:
            connection_dict['os'] = os_type
        try:
            if extra_fields:
                extra_fields_dict = json.loads(extra_fields)
                if isinstance(extra_fields_dict, dict):
                    connection_dict.update(extra_fields_dict)
        except Exception:
            logger.exception(f'Problem parsing extra fields')
        if ax_snow_values_map_dict:
            connection_dict.update(ax_snow_values_map_dict)
        request_json = connection_dict

        if self._config['use_adapter'] is True:
            response = self._plugin_base.request_remote_plugin('update_computer', adapter_unique_name, 'post',
                                                               json=request_json)
            return response.text
        try:
            if not self._config.get('domain') or not self._config.get('username') or not self._config.get('password'):
                return 'Missing Parameters For Connection'
            service_now_connection = ServiceNowConnection(domain=self._config['domain'],
                                                          verify_ssl=self._config.get('verify_ssl'),
                                                          username=self._config.get('username'),
                                                          password=self._config.get('password'),
                                                          https_proxy=self._config.get('https_proxy'))
            with service_now_connection:
                service_now_connection.update_service_now_computer(connection_dict)
                return ''
        except Exception as e:
            logger.exception(f'Got exception creating ServiceNow computer with {name}')
            return f'Got exception creating ServiceNow computer: {str(e)}'

    # pylint: disable=R0912,R0914,R0915,R1702
    def _run(self) -> EntitiesResult:
        ax_snow_fields_map_dict = dict()
        try:
            ax_snow_fields_map = self._config.get('ax_snow_fields_map')
            if ax_snow_fields_map:
                ax_snow_fields_map_dict = json.loads(ax_snow_fields_map)
                if not isinstance(ax_snow_fields_map_dict, dict):
                    ax_snow_fields_map_dict = {}
        except Exception:
            logger.exception(f'Problem parsing ax_snow_fields_map')
        service_now_projection = {
            'internal_axon_id': 1,
            'preferred_fields.hostname_preferred': 1,
            'preferred_fields.os.type_preferred': 1,
            'preferred_fields.os.distribution_preferred': 1,
            'preferred_fields.network_interfaces.mac_preferred': 1,
            'preferred_fields.network_interfaces.ips_preferred': 1,
            'adapters.plugin_unique_name': 1,
            'adapters.plugin_name': 1,
            'adapters.data.hostname': 1,
            'adapters.data.sys_id': 1,
            'adapters.data.name': 1,
            'adapters.data.class_name': 1,
            'adapters.data.os.type': 1,
            'adapters.data.device_serial': 1,
            'adapters.data.device_manufacturer': 1,
            'adapters.data.network_interfaces.mac': 1,
            'adapters.data.network_interfaces.ips': 1
        }
        for ax_field in ax_snow_fields_map_dict.keys():
            ax_field_projection = ax_field.split(':')[-1]
            service_now_projection[f'adapters.data.{ax_field_projection}'] = 1
        current_result = self._get_entities_from_view(service_now_projection)
        results = []
        for entry in current_result:
            try:
                name_raw = None
                class_name = None
                sys_id = None
                asset_name_raw = None
                mac_address_raw = None
                ip_address_raw = None
                manufacturer_raw = None
                serial_number_raw = None
                found_bad_hostname = False
                os_raw = None
                found_snow = False
                found_two_snow = False
                snow_manufacturer = None
                snow_serial = None
                snow_name = None
                ax_snow_values_map_dict = dict()
                for from_adapter in entry['adapters']:
                    data_from_adapter = from_adapter['data']
                    if from_adapter.get('plugin_name') == ADAPTER_NAME:
                        class_name = data_from_adapter.get('class_name')
                        sys_id = data_from_adapter.get('sys_id')
                        if class_name and sys_id:
                            snow_manufacturer = data_from_adapter.get('device_manufacturer')
                            snow_serial = data_from_adapter.get('device_serial')
                            snow_name = data_from_adapter.get('name')
                            if found_snow:
                                found_two_snow = True
                            found_snow = True
                        continue
                    if name_raw is None:
                        name_raw = data_from_adapter.get('hostname')
                    elif data_from_adapter.get('hostname'):
                        if data_from_adapter.get('hostname').split('.')[0].lower() != name_raw.split('.')[0].lower():
                            found_bad_hostname = True
                    if asset_name_raw is None:
                        asset_name_raw = data_from_adapter.get('name')
                    if os_raw is None:
                        os_raw = data_from_adapter.get('os', {}).get('type')
                    nics = data_from_adapter.get('network_interfaces')
                    if nics and isinstance(nics, list):
                        for nic in nics:
                            ips = nic.get('ips')
                            if ip_address_raw is None and ips and isinstance(ips, list):
                                ips_delimiter = self._config.get('ips_delimiter') or '/'
                                if self._config.get('use_first_ip_only'):
                                    ips = [ips[0]]
                                ip_address_raw = ips_delimiter.join(ips)
                            mac = nic.get('mac')
                            if mac_address_raw is None and mac and isinstance(mac, str):
                                mac_address_raw = mac
                    if serial_number_raw is None:
                        serial_number_raw = data_from_adapter.get(
                            'device_serial') or data_from_adapter.get('bios_serial')
                    if manufacturer_raw is None:
                        manufacturer_raw = data_from_adapter.get('device_manufacturer')
                    try:
                        for ax_field in ax_snow_fields_map_dict:
                            ax_field_adapter = None
                            ax_field_project = ax_field
                            if ':' in ax_field:
                                ax_field_adapter = ax_field.split(':')[0]
                                ax_field_project = ax_field.split(':')[-1]
                            snow_field = ax_snow_fields_map_dict[ax_field]
                            if not ax_snow_values_map_dict.get(snow_field) and data_from_adapter.get(ax_field_project) \
                                    and (from_adapter.get('plugin_name') == ax_field_adapter or not ax_field_adapter):
                                snow_value = data_from_adapter[ax_field_project]
                                if snow_value and not isinstance(snow_value, str):
                                    snow_value = str(snow_value)
                                ax_snow_values_map_dict[snow_field] = snow_value
                    except Exception:
                        logger.exception(f'Problem with translating dict')
                try:
                    preferred_fields = entry.get('preferred_fields')
                    if not isinstance(preferred_fields, dict):
                        preferred_fields = {}
                    hostname_preferred = preferred_fields.get('hostname_preferred')
                    if hostname_preferred:
                        name_raw = hostname_preferred
                    type_preferred = (preferred_fields.get('os') or {}).get('type_preferred')
                    distribution_preferred = (preferred_fields.get('os') or {}).get('distribution_preferred')
                    if type_preferred and distribution_preferred:
                        type_preferred = f'{type_preferred} {distribution_preferred}'
                    if type_preferred:
                        os_raw = type_preferred
                    network_interfaces = (preferred_fields.get('network_interfaces') or {})
                    mac_preferred = network_interfaces.get('mac_preferred') or []
                    if mac_preferred:
                        mac_delimiter = self._config.get('mac_delimiter') or '/'
                        if self._config.get('use_first_mac_only') or 'use_first_mac_only' not in self._config:
                            mac_address_raw = mac_preferred[0]
                        else:
                            mac_address_raw = mac_delimiter.join(mac_preferred)
                    ips_preferred = network_interfaces.get('ips_preferred') or []
                    if ips_preferred:
                        ip_address_raw = ips_preferred

                except Exception:
                    logger.exception(f'Problem with preferred fields')
                if not ip_address_raw:
                    ip_address_raw = None
                else:
                    ip_address_raw_list = []
                    for ip in ip_address_raw:
                        if ip not in ['127.0.0.1']:
                            ip_address_raw_list.append(ip)
                            if self._config.get('use_first_ip_only'):
                                break
                    ips_delimiter = self._config.get('ips_delimiter') or '/'
                    ip_address_raw = ips_delimiter.join(ip_address_raw_list)
                # Make sure that we have name
                if name_raw is None and asset_name_raw is None:
                    results.append(EntityResult(entry['internal_axon_id'], False, 'Device With No Name'))
                    continue
                if found_bad_hostname:
                    results.append(EntityResult(entry['internal_axon_id'], False, 'Device With Mutiple Names'))
                    continue
                if not found_snow:
                    results.append(EntityResult(entry['internal_axon_id'], False,
                                                'Device doesn\'t contain ServiceNow adapter'))
                    continue
                if found_two_snow:
                    results.append(EntityResult(entry['internal_axon_id'], False,
                                                'Device ontains more than one ServiceNow adapter'))
                    continue
                # If we don't have hostname we use asset name
                name_raw = name_raw if name_raw else asset_name_raw
                if snow_manufacturer:
                    manufacturer_raw = None
                if snow_serial:
                    serial_number_raw = None
                if snow_name:
                    name_raw = None
                message = self._update_service_now_computer(class_name=class_name,
                                                            sys_id=sys_id,
                                                            name=name_raw,
                                                            mac_address=mac_address_raw,
                                                            ip_address=ip_address_raw,
                                                            manufacturer=manufacturer_raw,
                                                            os_type=os_raw,
                                                            extra_fields=self._config.get('extra_fields'),
                                                            serial_number=serial_number_raw,
                                                            ax_snow_values_map_dict=ax_snow_values_map_dict
                                                            )

                results.append(EntityResult(entry['internal_axon_id'], not message, message or 'Success'))
            except Exception:
                logger.exception(f'Problem with entry {entry}')
                results.append(EntityResult(entry['internal_axon_id'], False, 'Unexpected Error'))
        return results
