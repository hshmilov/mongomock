import logging

from axonius.consts.plugin_consts import HAVEIBEENPWNED_PLUGIN_NAME
from axonius.types.enforcement_classes import EntitiesResult, EntityResult
from axonius.clients.haveibeenpwned.consts import HAVEIBEENPWNED_DOMAIN
from reports.action_types.action_type_base import ActionTypeBase, generic_fail, add_node_selection, add_node_default


logger = logging.getLogger(f'axonius.{__name__}')

# pylint: disable=protected-access


class HaveibeenpwnedEnrichment(ActionTypeBase):
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
                    'name': 'domain_preferred',
                    'title': 'Have I Been Pwned Domain',
                    'type': 'string',
                    'default': HAVEIBEENPWNED_DOMAIN
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
                    'title': 'HTTPS Proxy',
                    'type': 'string'
                },
                {
                    'name': 'alternative_suffix',
                    'title': 'Alternative Email Suffix',
                    'type': 'string'
                }
            ],
            'required': [
                'verify_ssl',
                'apikey'
            ],
            'type': 'array'
        }
        return add_node_selection(schema, HAVEIBEENPWNED_PLUGIN_NAME)

    @staticmethod
    def default_config() -> dict:
        return add_node_default({'verify_ssl': False,
                                 'https_proxy': None,
                                 'alternative_suffix': None,
                                 'apikey': None,
                                 'domain_preferred': HAVEIBEENPWNED_DOMAIN},
                                HAVEIBEENPWNED_PLUGIN_NAME)

    def _trigger_haveibeenpwned_adapter(self):
        adapter_unique_name = self._plugin_base._get_adapter_unique_name(
            HAVEIBEENPWNED_PLUGIN_NAME, self.action_node_id)
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

    def _haveibeenpwned_fail(self, reason):
        reason = str(reason)
        reason = f'Error while running Haveibeenpwned Enrichment: {reason}'
        return generic_fail(internal_axon_ids=self._internal_axon_ids, reason=reason)

    def __run(self) -> EntitiesResult:
        action_result = self._trigger_haveibeenpwned_adapter()
        return [self.prettify_output(k, v) for k, v in action_result.items()]

    def _run(self) -> EntitiesResult:
        try:
            return self.__run()
        except Exception as e:
            logger.exception('Error while running Haveibeenpwned Enrichment')
            return self._haveibeenpwned_fail(e)
