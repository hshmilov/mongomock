import logging

from axonius.types.enforcement_classes import EntitiesResult, EntityResult
from axonius.plugin_base import PluginBase
from reports.action_types.action_type_base import ActionTypeBase, generic_fail

logger = logging.getLogger(f'axonius.{__name__}')


class TenableScAddIPsToAsset(ActionTypeBase):
    """
    Creates an computer in the ServiceNow account
    """

    @staticmethod
    def config_schema() -> dict:
        return {
            'items': [
                {
                    'name': 'asset_name',
                    'title': 'Asset Name',
                    'type': 'string'
                },
                {
                    'name': 'create_new_asset',
                    'title': 'Create New Asset',
                    'type': 'bool'
                }
            ],
            'required': [
                'asset_name',
                'create_new_asset'
            ],
            'type': 'array'
        }

    @staticmethod
    def default_config() -> dict:
        return {
            'asset_name': None,
            'create_new_asset': False
        }

    # pylint: disable=R0912,R0914,R0915,R1702
    def _run(self) -> EntitiesResult:
        current_result = self._get_entities_from_view({
            'adapters.data.network_interfaces.ips': 1,
            'internal_axon_id': 1
        })
        ips = set()
        results = []
        for entry in current_result:
            try:
                for adapter_data in entry['adapters']:
                    adapter_data = adapter_data.get('data') or {}
                    if isinstance(adapter_data.get('network_interfaces'), list):
                        for nic in adapter_data.get('network_interfaces'):
                            if isinstance(nic.get('ips'), list):
                                for ip in nic.get('ips'):
                                    ips.add(ip)
                results.append(EntityResult(entry['internal_axon_id'], True, 'sucesss'))
            except Exception:
                logger.exception(f'Failed adding nic entry {entry}')
                results.append(EntityResult(entry['internal_axon_id'], False, 'Unexpected Error'))
        asset_name = self._config['asset_name']
        create_new_asset = self._config['create_new_asset']
        action_name = 'create_asset_with_ips' if create_new_asset else 'add_ips_to_asset'
        tenable_sc_dict = {'ips': list(ips), 'asset_name': asset_name}
        response = PluginBase.Instance.request_remote_plugin(action_name, 'tenable_security_center_adapter',
                                                             'post', json=tenable_sc_dict)
        if response.status_code == 200:
            return results
        if response.status_code == 500:
            return generic_fail(self._internal_axon_ids, reason=response.data.message)
        return generic_fail(self._internal_axon_ids)
