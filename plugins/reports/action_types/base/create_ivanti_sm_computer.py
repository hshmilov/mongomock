import json
import logging

from axonius.types.enforcement_classes import EntitiesResult, EntityResult
from axonius.clients.ivanti_sm.connection import IvantiSmConnection
from reports.action_types.action_type_base import ActionTypeBase, add_node_selection, add_node_default

logger = logging.getLogger(f'axonius.{__name__}')

ADAPTER_NAME = 'ivanti_sm_adapter'

# pylint: disable=W0212


class IvantiSmComputerAction(ActionTypeBase):
    """
    Creates an computer in the Ivanti SM account
    """

    @staticmethod
    def config_schema() -> dict:
        schema = {
            'items': [
                {
                    'name': 'use_adapter',
                    'title': 'Use stored credentials from the Ivant Service Manager adapter',
                    'type': 'bool'
                },
                {
                    'name': 'domain',
                    'title': 'Ivanti Service Manager domain',
                    'type': 'string'
                },
                {
                    'name': 'apikey',
                    'title': 'API Key',
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
                    'name': 'ax_ivanti_fields_map',
                    'type': 'string',
                    'title': 'Axonius to ServiceNow field mapping'
                }
            ],
            'required': [
                'use_adapter',
                'verify_ssl'
            ],
            'type': 'array'
        }
        return add_node_selection(schema)

    @staticmethod
    def default_config() -> dict:
        return add_node_default({
            'use_adapter': False,
            'domain': None,
            'apikey': None,
            'https_proxy': None,
            'ax_ivanti_fields_map': None,
            'extra_fields': None,
            'verify_ssl': True,
        })

    # pylint: disable=too-many-arguments,too-many-branches
    def _create_ivanti_sm_computer(self, name, mac_address=None, ip_address=None,
                                   manufacturer=None, os_type=None, serial_number=None,
                                   to_correlate_plugin_unique_name=None, to_correlate_device_id=None,
                                   extra_fields=None, ax_ivanti_values_map_dict=None):
        adapter_unique_name = self._plugin_base._get_adapter_unique_name(ADAPTER_NAME, self.action_node_id)
        connection_dict = dict()
        if not name:
            return None
        connection_dict['Name'] = name
        if mac_address:
            connection_dict['MACAddress'] = mac_address
        if ip_address:
            connection_dict['IPAddress'] = ip_address
        if manufacturer:
            connection_dict['Manufacturer'] = manufacturer
        if serial_number:
            connection_dict['SerialNumber'] = serial_number
        if os_type:
            connection_dict['OperatingSystem'] = os_type
        try:
            if extra_fields:
                extra_fields_dict = json.loads(extra_fields)
                if isinstance(extra_fields_dict, dict):
                    connection_dict.update(extra_fields_dict)
        except Exception:
            logger.exception(f'Problem parsing extra fields')
        if ax_ivanti_values_map_dict:
            connection_dict.update(ax_ivanti_values_map_dict)
        request_json = {'ivanti': connection_dict,
                        'to_ccorrelate': {'to_correlate_plugin_unique_name': to_correlate_plugin_unique_name,
                                          'device_id': to_correlate_device_id}}

        if self._config['use_adapter'] is True:
            response = self._plugin_base.request_remote_plugin('create_computer', adapter_unique_name, 'post',
                                                               json=request_json)
            return response.text
        try:
            if not self._config.get('domain') or not self._config.get('apikey'):
                return 'Missing Parameters For Connection'
            ivanti_sm_connection = IvantiSmConnection(domain=self._config['domain'],
                                                      verify_ssl=self._config.get('verify_ssl'),
                                                      apikey=self._config.get('apikey'),
                                                      https_proxy=self._config.get('https_proxy'))
            with ivanti_sm_connection:
                ivanti_sm_connection.create_ivanti_sm_computer(connection_dict)
                return ''
        except Exception as e:
            logger.exception(f'Got exception creating Ivanti SM computer with {name}')
            return f'Got exception creating Ivanti SM computer: {str(e)}'

    # pylint: disable=R0912,R0914,R0915,R1702
    def _run(self) -> EntitiesResult:
        ax_ivanti_fields_map_dict = dict()
        try:
            ax_ivanti_fields_map = self._config.get('ax_ivanti_fields_map')
            if ax_ivanti_fields_map:
                ax_ivanti_fields_map_dict = json.loads(ax_ivanti_fields_map)
                if not isinstance(ax_ivanti_fields_map_dict, dict):
                    ax_ivanti_fields_map_dict = {}
        except Exception:
            logger.exception(f'Problem parsing ax_snow_fields_map')

        ivanti_projection = {
            'internal_axon_id': 1,
            'adapters.plugin_unique_name': 1,
            'adapters.plugin_name': 1,
            'adapters.data.hostname': 1,
            'adapters.data.id': 1,
            'adapters.data.name': 1,
            'adapters.data.os.type': 1,
            'adapters.data.device_serial': 1,
            'adapters.data.device_manufacturer': 1,
            'adapters.data.network_interfaces.mac': 1,
            'adapters.data.network_interfaces.ips': 1
        }
        for ax_field in ax_ivanti_fields_map_dict.keys():
            ax_field_projection = ax_field.split(':')[-1]
            ivanti_projection[f'adapters.data.{ax_field_projection}'] = 1
        current_result = self._get_entities_from_view(ivanti_projection)
        results = []
        for entry in current_result:
            try:
                name_raw = None
                asset_name_raw = None
                mac_address_raw = None
                ip_address_raw = set()
                manufacturer_raw = None
                serial_number_raw = None
                os_raw = None
                corre_plugin_id = None
                to_correlate_device_id = None
                found_ivanti = False
                ax_ivanti_values_map_dict = dict()
                for from_adapter in entry['adapters']:
                    if from_adapter.get('plugin_name') == ADAPTER_NAME:
                        found_ivanti = True
                        break
                    data_from_adapter = from_adapter['data']
                    if corre_plugin_id is None:
                        corre_plugin_id = from_adapter.get('plugin_unique_name')
                        to_correlate_device_id = data_from_adapter.get('id')
                    if name_raw is None:
                        name_raw = data_from_adapter.get('hostname')
                    if asset_name_raw is None:
                        asset_name_raw = data_from_adapter.get('name')
                    if os_raw is None:
                        os_raw = data_from_adapter.get('os', {}).get('type')
                    nics = data_from_adapter.get('network_interfaces')
                    if nics and isinstance(nics, list):
                        for nic in nics:
                            ips = nic.get('ips')
                            if ips and isinstance(ips, list):
                                ip_address_raw.union(ips)
                            mac = nic.get('mac')
                            if mac_address_raw is None and mac and isinstance(mac, str):
                                mac_address_raw = mac
                    if serial_number_raw is None:
                        serial_number_raw = data_from_adapter.get(
                            'device_serial') or data_from_adapter.get('bios_serial')
                    if manufacturer_raw is None:
                        manufacturer_raw = data_from_adapter.get('device_manufacturer')
                    try:
                        for ax_field in ax_ivanti_fields_map_dict:
                            ax_field_adapter = None
                            ax_field_project = ax_field
                            if ':' in ax_field:
                                ax_field_adapter = ax_field.split(':')[0]
                                ax_field_project = ax_field.split(':')[-1]
                            snow_field = ax_ivanti_fields_map_dict[ax_field]
                            if not ax_ivanti_values_map_dict.get(snow_field) \
                                    and data_from_adapter.get(ax_field_project) \
                                    and (from_adapter.get('plugin_name') == ax_field_adapter or not ax_field_adapter):
                                ivanti_value = data_from_adapter[ax_field_project]
                                if ivanti_value and not isinstance(ivanti_value, str):
                                    ivanti_value = str(ivanti_value)
                                ax_ivanti_values_map_dict[snow_field] = ivanti_value
                    except Exception:
                        logger.exception(f'Problem with translating dict')
                # Make sure that we have name
                if not ip_address_raw:
                    ip_address_raw = None
                else:
                    ip_address_raw = list(ip_address_raw)
                    ip_address_raw = '/'.join(ip_address_raw)
                if name_raw is None and asset_name_raw is None:
                    results.append(EntityResult(entry['internal_axon_id'], False, 'Device With No Name'))
                    continue
                if found_ivanti:
                    results.append(EntityResult(entry['internal_axon_id'], False,
                                                'Device Already With Ivanti SM Adapter'))
                    continue

                # If we don't have hostname we use asset name
                name_raw = name_raw if name_raw else asset_name_raw
                message = self._create_ivanti_sm_computer(name=name_raw,
                                                          mac_address=mac_address_raw,
                                                          ip_address=ip_address_raw,
                                                          manufacturer=manufacturer_raw,
                                                          os_type=os_raw,
                                                          serial_number=serial_number_raw,
                                                          to_correlate_plugin_unique_name=corre_plugin_id,
                                                          to_correlate_device_id=to_correlate_device_id,
                                                          extra_fields=self._config.get('extra_fields'),
                                                          ax_ivanti_values_map_dict=ax_ivanti_values_map_dict)

                results.append(EntityResult(entry['internal_axon_id'], not message, message or 'Success'))
            except Exception:
                logger.exception(f'Problem with entry {entry}')
                results.append(EntityResult(entry['internal_axon_id'], False, 'Unexpected Error'))
        return results
