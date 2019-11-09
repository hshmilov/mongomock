import logging

from axonius.types.enforcement_classes import EntitiesResult, EntityResult
from axonius.clients.service_now.connection import ServiceNowConnection
from reports.action_types.action_type_base import ActionTypeBase, add_node_selection, add_node_default

logger = logging.getLogger(f'axonius.{__name__}')

ADAPTER_NAME = 'service_now_adapter'

# pylint: disable=W0212


class ServiceNowComputerAction(ActionTypeBase):
    """
    Creates an computer in the ServiceNow account
    """

    @staticmethod
    def config_schema() -> dict:
        schema = {
            'items': [
                {
                    'name': 'use_adapter',
                    'title': 'Use ServiceNow Adapter',
                    'type': 'bool'
                },
                {
                    'name': 'domain',
                    'title': 'ServiceNow Domain',
                    'type': 'string'
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
                },
                {
                    'name': 'cmdb_ci_table',
                    'title': 'CMDB CI Table Name',
                    'type': 'string'
                }
            ],
            'required': [
                'use_adapter'
            ],
            'type': 'array'
        }
        return add_node_selection(schema, ADAPTER_NAME)

    @staticmethod
    def default_config() -> dict:
        return add_node_default({
            'use_adapter': False,
            'domain': None,
            'username': None,
            'password': None,
            'https_proxy': None,
            'cmdb_ci_table': None,
            'verify_ssl': True
        }, ADAPTER_NAME)

    def _create_service_now_computer(self, name, mac_address=None, ip_address=None,
                                     manufacturer=None, os_type=None, serial_number=None,
                                     to_correlate_plugin_unique_name=None, to_correlate_device_id=None,
                                     cmdb_ci_table=None):
        adapter_unique_name = self._plugin_base._get_adapter_unique_name(ADAPTER_NAME, self.action_node_id)
        connection_dict = dict()
        if not name:
            return None
        if cmdb_ci_table:
            connection_dict['cmdb_ci_table'] = cmdb_ci_table
        connection_dict['name'] = name
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
        request_json = {'snow': connection_dict,
                        'to_ccorrelate': {'to_correlate_plugin_unique_name': to_correlate_plugin_unique_name,
                                          'device_id': to_correlate_device_id}}

        if self._config['use_adapter'] is True:
            response = self._plugin_base.request_remote_plugin('create_computer', adapter_unique_name, 'post',
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
                service_now_connection.create_service_now_computer(connection_dict)
                return ''
        except Exception as e:
            logger.exception(f'Got exception creating ServiceNow computer with {name}')
            return f'Got exception creating ServiceNow computer: {str(e)}'

    # pylint: disable=R0912,R0914,R0915,R1702
    def _run(self) -> EntitiesResult:

        service_now_projection = {
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
        current_result = self._get_entities_from_view(service_now_projection)
        results = []

        for entry in current_result:
            try:
                name_raw = None
                asset_name_raw = None
                mac_address_raw = None
                ip_address_raw = None
                manufacturer_raw = None
                serial_number_raw = None
                os_raw = None
                corre_plugin_id = None
                to_correlate_device_id = None
                found_snow = False
                for from_adapter in entry['adapters']:
                    if from_adapter.get('plugin_name') == ADAPTER_NAME:
                        found_snow = True
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
                # Make sure that we have name
                if name_raw is None and asset_name_raw is None:
                    results.append(EntityResult(entry['internal_axon_id'], False, 'Device With No Name'))
                    continue
                if found_snow:
                    results.append(EntityResult(entry['internal_axon_id'], False,
                                                'Device Already With ServiceNow Adapter'))
                    continue

                # If we don't have hostname we use asset name
                name_raw = name_raw if name_raw else asset_name_raw

                message = self._create_service_now_computer(name=name_raw,
                                                            mac_address=mac_address_raw,
                                                            ip_address=ip_address_raw,
                                                            manufacturer=manufacturer_raw,
                                                            os_type=os_raw,
                                                            serial_number=serial_number_raw,
                                                            to_correlate_plugin_unique_name=corre_plugin_id,
                                                            to_correlate_device_id=to_correlate_device_id,
                                                            cmdb_ci_table=self._config.get('cmdb_ci_table'))

                results.append(EntityResult(entry['internal_axon_id'], not message, message or 'Success'))
            except Exception:
                logger.exception(f'Problem with entry {entry}')
                results.append(EntityResult(entry['internal_axon_id'], False, 'Unexpected Error'))
        return results
