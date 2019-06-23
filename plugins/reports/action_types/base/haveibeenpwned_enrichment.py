import logging

from axonius.consts.plugin_consts import HAVEIBEENPWNED_PLUGIN_NAME
from axonius.types.enforcement_classes import EntitiesResult, EntityResult
from reports.action_types.action_type_base import ActionTypeBase, generic_fail

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
        return {
            'items': [
                {
                    'name': 'https_proxy',
                    'title': 'HTTPS Proxy',
                    'type': 'string'
                },
                {
                    'name': 'verify_ssl',
                    'title': 'Verify SSL',
                    'type': 'bool'
                }
            ],
            'required': [
                'verify_ssl'
            ],
            'type': 'array'
        }

    @staticmethod
    def default_config() -> dict:
        return {}

    def _trigger_haveibeenpwned_adapter(self):
        action_data = {'internal_axon_ids': self._internal_axon_ids, 'client_config': self._config}
        action_result = self._plugin_base._trigger_remote_plugin(
            HAVEIBEENPWNED_PLUGIN_NAME,
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
