import logging

from axonius.consts.plugin_consts import PORTNOX_PLUGIN_NAME
from axonius.types.enforcement_classes import EntitiesResult, EntityResult
from reports.action_types.action_type_base import ActionTypeBase, generic_fail, add_node_selection, add_node_default

logger = logging.getLogger(f'axonius.{__name__}')

# pylint: disable=protected-access


class PortnoxEnrichment(ActionTypeBase):
    @staticmethod
    def prettify_output(id_, result: dict) -> EntityResult:
        value = result['value']
        success = result['success']
        return EntityResult(id_, success, value)

    @staticmethod
    def config_schema() -> dict:
        schema = {
            'items': [
                {
                    'name': 'domain',
                    'title': 'Portnox Domain',
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
            ],
            'required': [
                'domain',
                'username',
                'password',
                'verify_ssl'

            ],
            'type': 'array'
        }
        return add_node_selection(schema, PORTNOX_PLUGIN_NAME)

    @staticmethod
    def default_config() -> dict:
        return add_node_default({'domain': None, 'username': None,
                                 'password': None, 'verify_ssl': False}, PORTNOX_PLUGIN_NAME)

    def _trigger_portnox(self):
        adapter_unique_name = self._plugin_base._get_adapter_unique_name(PORTNOX_PLUGIN_NAME, self.action_node_id)
        action_data = {'internal_axon_ids': self._internal_axon_ids, 'client_config': self._config}

        action_result = self._plugin_base._trigger_remote_plugin(
            adapter_unique_name,
            job_name='enrich',
            priority=True,
            blocking=True,
            data=action_data
        )
        action_result = action_result.json()

        if action_result.get('status') == 'error':
            raise RuntimeError(action_result['message'])

        return action_result

    def _portnox_fail(self, reason):
        reason = str(reason)
        reason = f'Error while running Portnox Enrichment: {reason}'
        return generic_fail(internal_axon_ids=self._internal_axon_ids, reason=reason)

    def __run(self) -> EntitiesResult:
        action_result = self._trigger_portnox()
        return [self.prettify_output(k, v) for k, v in action_result.items()]

    def _run(self) -> EntitiesResult:
        try:
            return self.__run()
        except Exception as e:
            logger.exception('Error while running Portnox Enrichment')
            return self._Portnox_fail(e)
