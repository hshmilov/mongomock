import json
import logging

from axonius.types.enforcement_classes import EntitiesResult, EntityResult
from axonius.clients.cherwell.connection import CherwellConnection
from axonius.clients.cherwell.consts import IT_ASSET_BUS_OB_ID
from reports.action_types.action_type_base import ActionTypeBase, add_node_selection, add_node_default

logger = logging.getLogger(f'axonius.{__name__}')

ADAPTER_NAME = 'cherwell_adapter'

# pylint: disable=W0212


class CherwellCreateComputerAction(ActionTypeBase):
    """
    Create a computer in the Cherwell account
    """

    @staticmethod
    def config_schema() -> dict:
        schema = {
            'items': [
                {
                    'name': 'use_adapter',
                    'title': 'Use stored credentials from the Cherwell adapter',
                    'type': 'bool'
                },
                {
                    'name': 'domain',
                    'title': 'Cherwell domain',
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
                    'name': 'client_id',
                    'title': 'Client ID',
                    'type': 'string'
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
                    'name': 'bus_ob_id',
                    'title': 'Business Object ID',
                    'type': 'string'
                },
                {
                    'name': 'extra_fields',
                    'title': 'Additional fields',
                    'type': 'string'
                },
                {
                    'name': 'ax_cherwell_fields_map',
                    'type': 'string',
                    'title': 'Axonius to Cherwell field mapping'
                }
            ],
            'required': [
                'use_adapter',
                'verify_ssl',
                'bus_ob_id'
            ],
            'type': 'array'
        }
        return add_node_selection(schema)

    @staticmethod
    def default_config() -> dict:
        return add_node_default({
            'use_adapter': False,
            'domain': None,
            'username': None,
            'password': None,
            'https_proxy': None,
            'extra_fields': None,
            'ax_cherwell_fields_map': None,
            'verify_ssl': False,
            'client_id': None,
            'bus_ob_id': IT_ASSET_BUS_OB_ID
        })

    # pylint: disable=too-many-arguments
    # pylint: disable=too-many-locals, too-many-nested-blocks, too-many-branches, too-many-statements
    def _create_cherwell_computer(self, bus_ob_id, bus_ob_rec_id, bus_ob_public_id,
                                  name, mac_address=None, ip_address=None, extra_fields=None,
                                  ax_cherwell_values_map_dict=None,
                                  to_correlate_plugin_unique_name=None, to_correlate_device_id=None,
                                  manufacturer=None, os_type=None, serial_number=None,
                                  os_build=None):
        adapter_unique_name = self._plugin_base._get_adapter_unique_name(ADAPTER_NAME, self.action_node_id)
        connection_dict = dict()
        if not name:
            return None
        connection_dict['name'] = name
        connection_dict['bus_ob_id'] = bus_ob_id
        connection_dict['bus_ob_rec_id'] = bus_ob_rec_id
        connection_dict['bus_ob_public_id'] = bus_ob_public_id
        connection_dict['extra_fields'] = {}
        try:
            if extra_fields:
                extra_fields_dict = json.loads(extra_fields)
                if isinstance(extra_fields_dict, dict):
                    connection_dict['extra_fields'].update(extra_fields_dict)
            if ax_cherwell_values_map_dict:
                connection_dict['extra_fields'].update(ax_cherwell_values_map_dict)
        except Exception:
            logger.exception(f'Problem parsing extra fields')
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
        if os_build:
            connection_dict['os_build'] = os_build
        request_json = {'cherwell': connection_dict,
                        'to_ccorrelate': {'to_correlate_plugin_unique_name': to_correlate_plugin_unique_name,
                                          'device_id': to_correlate_device_id}}

        if self._config['use_adapter'] is True:
            response = self._plugin_base.request_remote_plugin('create_computer', adapter_unique_name, 'post',
                                                               json=request_json)
            return response.text
        try:
            if not self._config.get('domain') or not self._config.get('username') or not self._config.get('password'):
                return 'Missing Parameters For Connection'
            cherwell_connection = CherwellConnection(domain=self._config['domain'],
                                                     client_id=self._config.get('client_id'),
                                                     verify_ssl=self._config.get('verify_ssl'),
                                                     username=self._config.get('username'),
                                                     password=self._config.get('password'),
                                                     https_proxy=self._config.get('https_proxy'))
            with cherwell_connection:
                cherwell_connection.update_cherwell_computer(connection_dict)
                return ''
        except Exception as e:
            logger.exception(f'Got exception creating Cherwell computer with {name}')
            return f'Got exception creating Cherwell computer: {str(e)}'

    # pylint: disable=R0912,R0914,R0915,R1702
    def _run(self) -> EntitiesResult:
        ax_cherwell_fields_map_dict = dict()
        try:
            ax_cherwell_fields_map = self._config.get('ax_cherwell_fields_map')
            if ax_cherwell_fields_map:
                ax_cherwell_fields_map_dict = json.loads(ax_cherwell_fields_map)
                if not isinstance(ax_cherwell_fields_map_dict, dict):
                    ax_cherwell_fields_map_dict = {}
        except Exception:
            logger.exception(f'Problem parsing ax_snow_fields_map')
        cherwell_projection = {
            'internal_axon_id': 1,
            'adapters.plugin_unique_name': 1,
            'adapters.plugin_name': 1,
            'adapters.data.hostname': 1,
            'adapters.data.id': 1,
            'adapters.data.name': 1,
            'adapters.data.bus_ob_id': 1,
            'adapters.data.bus_ob_rec_id': 1,
            'adapters.data.bus_ob_public_id': 1,
            'adapters.data.os.type': 1,
            'adapters.data.device_serial': 1,
            'adapters.data.device_manufacturer': 1,
            'adapters.data.network_interfaces.mac': 1,
            'adapters.data.network_interfaces.ips': 1
        }
        for ax_field in ax_cherwell_fields_map_dict.keys():
            ax_field_projection = ax_field.split(':')[-1]
            cherwell_projection[f'adapters.data.{ax_field_projection}'] = 1
        current_result = self._get_entities_from_view(cherwell_projection)
        results = []

        for entry in current_result:
            try:
                name_raw = None
                asset_name_raw = None
                mac_address_raw = None
                ip_address_raw = None
                corre_plugin_id = None
                to_correlate_device_id = None
                manufacturer_raw = None
                serial_number_raw = None
                os_raw = None
                os_build = None
                found_cherwell = False
                ax_cherwell_values_map_dict = dict()
                for from_adapter in entry['adapters']:
                    data_from_adapter = from_adapter['data']
                    if from_adapter.get('plugin_name') == ADAPTER_NAME:
                        found_cherwell = True
                        break
                    if corre_plugin_id is None:
                        corre_plugin_id = from_adapter.get('plugin_unique_name')
                        to_correlate_device_id = data_from_adapter.get('id')
                    if name_raw is None:
                        name_raw = data_from_adapter.get('hostname')
                    if asset_name_raw is None:
                        asset_name_raw = data_from_adapter.get('name')
                    if os_raw is None:
                        os_raw = data_from_adapter.get('os', {}).get('type')
                    if os_build is None:
                        os_build = data_from_adapter.get('os', {}).get('build')
                    nics = data_from_adapter.get('network_interfaces')
                    if nics and isinstance(nics, list):
                        for nic in nics:
                            ips = nic.get('ips')
                            if ip_address_raw is None and ips and isinstance(ips, list):
                                ip_address_raw = '/'.join(ips)
                            mac = nic.get('mac')
                            if mac_address_raw is None and mac and isinstance(mac, str):
                                mac_address_raw = mac
                    if serial_number_raw is None:
                        serial_number_raw = data_from_adapter.get(
                            'device_serial') or data_from_adapter.get('bios_serial')
                    if manufacturer_raw is None:
                        manufacturer_raw = data_from_adapter.get('device_manufacturer')
                    try:
                        for ax_field in ax_cherwell_fields_map_dict:
                            ax_field_adapter = None
                            ax_field_project = ax_field
                            if ':' in ax_field:
                                ax_field_adapter = ax_field.split(':')[0]
                                ax_field_project = ax_field.split(':')[-1]
                            cherwell_field = ax_cherwell_fields_map_dict[ax_field]
                            if not ax_cherwell_values_map_dict.get(cherwell_field) \
                                    and data_from_adapter.get(ax_field_project) \
                                    and (from_adapter.get('plugin_name') == ax_field_adapter or not ax_field_adapter):
                                cherwell_value = data_from_adapter[ax_field_project]
                                if cherwell_value and not isinstance(cherwell_value, str):
                                    cherwell_value = str(cherwell_value)
                                ax_cherwell_values_map_dict[cherwell_field] = cherwell_value
                    except Exception:
                        logger.exception(f'Problem with translating dict')
                # Make sure that we have name
                if name_raw is None and asset_name_raw is None:
                    results.append(EntityResult(entry['internal_axon_id'], False, 'Device With No Name'))
                    continue
                if found_cherwell:
                    results.append(EntityResult(entry['internal_axon_id'], False,
                                                'Device already with Cherwell adapter'))
                    continue
                bus_ob_rec_id = ''
                bus_ob_public_id = ''
                bus_ob_id = self._config.get('bus_ob_id') or IT_ASSET_BUS_OB_ID
                # If we don't have hostname we use asset name
                name_raw = name_raw if name_raw else asset_name_raw

                message = self._create_cherwell_computer(bus_ob_id=bus_ob_id,
                                                         bus_ob_rec_id=bus_ob_rec_id,
                                                         bus_ob_public_id=bus_ob_public_id,
                                                         name=name_raw,
                                                         mac_address=mac_address_raw,
                                                         ip_address=ip_address_raw,
                                                         to_correlate_plugin_unique_name=corre_plugin_id,
                                                         to_correlate_device_id=to_correlate_device_id,
                                                         manufacturer=manufacturer_raw,
                                                         os_type=os_raw,
                                                         extra_fields=self._config.get('extra_fields'),
                                                         serial_number=serial_number_raw,
                                                         ax_cherwell_values_map_dict=ax_cherwell_values_map_dict,
                                                         os_build=os_build
                                                         )

                results.append(EntityResult(entry['internal_axon_id'], not message, message or 'Success'))
            except Exception:
                logger.exception(f'Problem with entry {entry}')
                results.append(EntityResult(entry['internal_axon_id'], False, 'Unexpected Error'))
        return results
