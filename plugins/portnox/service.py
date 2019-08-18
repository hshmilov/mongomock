import logging

from axonius.consts.plugin_consts import PLUGIN_UNIQUE_NAME
from axonius.mixins.triggerable import RunIdentifier, Triggerable
from axonius.plugin_base import EntityType
from axonius.fields import Field
from axonius.devices.device_adapter import DeviceAdapter
from axonius.types.correlation import CorrelationReason, CorrelationResult
from axonius.plugin_base import PluginBase
from axonius.blacklists import ALL_BLACKLIST
from axonius.utils.parsing import get_manufacturer_from_mac
from axonius.utils.files import get_local_config_file

from axonius.utils.gui_helpers import find_entity_field
from axonius.utils.datetime import parse_date
from axonius.clients.portnox.connection import PortnoxConnection

logger = logging.getLogger(f'axonius.{__name__}')


# pylint: disable=too-many-branches


def get_entity_field_list(device_data, field):
    """" find_entity_field returns object when single
         field exist and list when multiple objects exist.
         it hard to work like this, so this wrapper always returns a list """

    result = find_entity_field(device_data, field)
    if result is None:
        return []
    if not isinstance(result, list):
        result = [result]
    return result


# pylint: disable=R0201
class PortnoxService(Triggerable, PluginBase):
    # pylint: disable=too-many-instance-attributes
    class MyDeviceAdapter(DeviceAdapter):
        ssid = Field(str, 'SSID')
        last_status = Field(str, 'Last Status')
        failed_compliances = Field(str, 'Failed Compliances')
        authentication_scheme = Field(str, 'Authentication Scheme')
        switch_ip_address = Field(str, 'Switch IP Address')
        switch_module = Field(str, 'Switch Module')
        switch_port = Field(str, 'Switch Port')
        virtual_host = Field(str, 'Virtual Host')
        virtual_switch = Field(str, 'Virtual Switch')

    def __init__(self, *args, **kwargs):
        super().__init__(get_local_config_file(__file__),
                         *args, **kwargs)

    @staticmethod
    def get_valid_config(config):
        try:
            required_args = ['domain', 'username', 'password', 'verify_ssl']
            if not all(arg in config for arg in required_args):
                return None
        except Exception:
            logger.exception('Error when preparing arguments')
            return None
        return config

    def _triggered(self, job_name: str, post_json: dict, run_identifier: RunIdentifier, *args):
        if job_name != 'enrich':
            return super()._triggered(job_name, post_json, run_identifier, *args)

        logger.info('Portnox was Triggered.')
        internal_axon_ids = post_json['internal_axon_ids']
        client_config = post_json['client_config']

        client_config = self.get_valid_config(client_config)
        if not client_config:
            logger.debug(f'Bad config {client_config}')
            return {'status': 'error', 'message': f'Argument Error: Please specify a valid apikey'}

        with PortnoxConnection(domain=client_config['domain'],
                               username=client_config.get('username'),
                               password=client_config.get('password'), verify_ssl=client_config.get('verify_ssl'),
                               https_proxy=client_config.get('https_proxy')) as connection:
            results = {}
            for id_ in internal_axon_ids:
                try:
                    device = list(self.devices.get(internal_axon_id=id_))[0]
                    internal_axon_id, result = self._handle_device(device, connection)
                    results[internal_axon_id] = result
                except Exception as e:
                    results[id_] = {'success': False, 'value': str(e)}
        logger.info('Portnox Trigger end.')
        return results

    @staticmethod
    def _get_enrichment_client_id(id_, portnox_id):
        return '_'.join(('portnoxenrichment', id_, portnox_id))

    def _create_device(self, device_raw, client_id):
        try:
            device = self._new_device_adapter()
            device.id = client_id
            ips = device_raw.get('IpAddress').split(',') if device_raw.get('IpAddress') else None
            device.add_nic(mac=device_raw.get('MacAddress'), ips=ips)
            device.last_seen = parse_date(device_raw.get('LastSeen'))
            device.ssid = device_raw.get('SSID')
            device.last_status = device_raw.get('LastStatus')
            device.failed_compliances = device_raw.get('FailedCompliances')
            device.authentication_scheme = device_raw.get('AuthenticationScheme')
            try:
                if isinstance(device_raw.get('LoggedOnUsers'), list):
                    device.last_used_users = device_raw.get('LoggedOnUsers')
            except Exception:
                logger.exception(f'Problem with getting users for {device_raw}')
            device.figure_os(device_raw.get('OperatingSystem'))
            device.switch_ip_address = device_raw.get('SwitchIpAddress')
            device.switch_module = device_raw.get('SwitchModule')
            device.switch_port = device_raw.get('SwitchPort')
            device.virtual_host = device_raw.get('VirtualHost')
            device.virtual_switch = device_raw.get('VirtualSwitch')
            device.set_raw(device_raw)
            return device
        except Exception:
            logger.exception(f'Problem with device_raw {device_raw}')
            return None

    def _handle_portnox_id(self, device, portnox_id, connection):
        try:
            client_id = self._get_enrichment_client_id(device.internal_axon_id, portnox_id)
            device_raw = connection.get_portnox_id_information(portnox_id)

            new_device = self._create_device(device_raw, client_id)
            if not new_device:
                return False

            # Here we create a new device adapter tab out of cycle
            self._save_data_from_plugin(client_id,
                                        {'raw': [], 'parsed': [new_device.to_dict()]},
                                        EntityType.Devices,
                                        False)

            self._save_field_names_to_db(EntityType.Devices)
            # No correlation for now. I am afraid it will cause bad correlations.
            # I keep the code so it would be easy to return it.
            # self._correlate_enrichment_if_needed(device, new_device)
            return True
        except Exception as e:
            logger.exception(f'Failed to fetch portnox id info for {portnox_id}')
            return False

    def _handle_device(self, device, connection):
        try:
            if not device.specific_data:
                json = {'success': False, 'value': 'Portnox Error: Adapters not found'}
                return (device.internal_axon_id, json)

            macs_raw = get_entity_field_list(device.data, 'specific_data.data.network_interfaces.mac')
            portnox_ids = []
            for mac_raw in macs_raw:
                try:
                    if not get_manufacturer_from_mac(mac_raw):
                        continue
                    if mac_raw in ALL_BLACKLIST:
                        continue
                    mac_raw = mac_raw.upper().replace(':', '')
                    portnox_ids.append(mac_raw)
                except Exception:
                    pass

            if not portnox_ids:
                json = {'success': False, 'value': 'Portnox Error: Missing IDs fields'}
                return (device.internal_axon_id, json)

            if not any([self._handle_portnox_id(device, portnox_id, connection) for portnox_id in portnox_ids]):
                return (device.internal_axon_id, {'success': False, 'value': 'Portnox Enrichment - no results'})

            return (device.internal_axon_id, {'success': True, 'value': 'Portnox Enrichment success'})
        except Exception as e:
            logger.exception('Exception while handling devices')
            return (device.internal_axon_id, {'success': False, 'value': f'Portnox Enrichment Error: {str(e)}'})

    def _correlate_enrichment_if_needed(self, device, new_device):
        try:
            id_ = get_entity_field_list(device.data, 'adapters_data.portnox.id')
            id_ = ''.join(id_)

            # If id is in the "old" device id so this devices are already correlated
            # no need to correlate again.
            if new_device['id'] in id_:
                return

            logger.debug('Correlating enrichment')
            first_plugin_unique_name = device.specific_data[0][PLUGIN_UNIQUE_NAME]
            first_device_adapter_id = device.specific_data[0]['data']['id']
            new_device_id = new_device.id
            new_device = new_device.to_dict()

            associated_adapters = [(first_plugin_unique_name, first_device_adapter_id),
                                   (self.plugin_unique_name, new_device_id)]

            correlation = CorrelationResult(associated_adapters=associated_adapters,
                                            data={'reason': 'Portnox Enrichment'},
                                            reason=CorrelationReason.PortnoxEnrichment)

            self.link_adapters(EntityType.Devices, correlation)
        except Exception as e:
            logger.exception('Failed to correlate')
