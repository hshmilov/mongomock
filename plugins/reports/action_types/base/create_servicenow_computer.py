import logging

from reports.action_types.action_type_base import ActionTypeBase
from reports.enforcement_classes import EntitiesResult, EntityResult

logger = logging.getLogger(f'axonius.{__name__}')


class ServiceNowComputerAction(ActionTypeBase):
    """
    Creates an computer in the ServiceNow account
    """

    @staticmethod
    def config_schema() -> dict:
        return {
        }

    @staticmethod
    def default_config() -> dict:
        return {
        }

    # pylint: disable=R0912,R0914
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
        results = {}

        for entry in current_result:
            name_raw = None
            asset_name_raw = None
            mac_address_raw = None
            ip_address_raw = None
            manufacturer_raw = None
            serial_number_raw = None
            os_raw = None
            to_corre_plugin_id = None
            to_correlate_device_id = None
            found_snow = False
            for from_adapter in entry['adapters']:
                if from_adapter.get('plugin_name') == 'service_now_adapter':
                    found_snow = True
                    break
                data_from_adapter = from_adapter['data']
                if to_corre_plugin_id is None:
                    to_corre_plugin_id = from_adapter.get('plugin_unique_name')
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
                    serial_number_raw = data_from_adapter.get('device_serial') or data_from_adapter.get('bios_serial')
                if manufacturer_raw is None:
                    manufacturer_raw = data_from_adapter.get('device_manufacturer')
            # Make sure that we have name
            if name_raw is None and asset_name_raw is None:
                results[entry['internal_axon_id']] = EntityResult(False, 'Device With No Name')
                continue
            if found_snow:
                results[entry['internal_axon_id']] = EntityResult(False, 'Device Already With ServiceNow Adapter')
                continue

            # If we don't have hostname we use asset name
            name_raw = name_raw if name_raw else asset_name_raw

            message = self._plugin_base.create_service_now_computer(name=name_raw,
                                                                    mac_address=mac_address_raw,
                                                                    ip_address=ip_address_raw,
                                                                    manufacturer=manufacturer_raw,
                                                                    os=os_raw,
                                                                    serial_number=serial_number_raw,
                                                                    to_correlate_plugin_unique_name=to_corre_plugin_id,
                                                                    to_correlate_device_id=to_correlate_device_id)
            results[entry['internal_axon_id']] = EntityResult(not message, message or 'Success')
        return results
