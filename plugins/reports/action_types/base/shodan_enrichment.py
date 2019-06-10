import logging

from axonius.consts.plugin_consts import SHODAN_PLUGIN_NAME
from axonius.types.enforcement_classes import EntitiesResult, EntityResult
from axonius.clients.shodan.consts import DEFAULT_DOMAIN
from reports.action_types.action_type_base import ActionTypeBase, generic_fail

logger = logging.getLogger(f'axonius.{__name__}')

# pylint: disable=protected-access


class ShodanEnrichment(ActionTypeBase):
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
                    'name': 'domain',
                    'title': 'Shodan Domain',
                    'type': 'string',
                    'default': DEFAULT_DOMAIN
                },
                {
                    'name': 'apikey',
                    'title': 'API Key',
                    'type': 'string',
                    'format': 'password'
                },
                {
                    'name': 'https_proxy',
                    'title': 'HTTPS Proxy',
                    'type': 'string'
                },
            ],
            'required': [
                'apikey'
            ],
            'type': 'array'
        }

    @staticmethod
    def default_config() -> dict:
        return {'domain': DEFAULT_DOMAIN}

    def _trigger_shodan_adapter(self):
        action_data = {'internal_axon_ids': self._internal_axon_ids, 'client_config': self._config}

        action_result = self._plugin_base._trigger_remote_plugin(
            SHODAN_PLUGIN_NAME,
            priority=True,
            blocking=True,
            data=action_data
        )
        action_result = action_result.json()

        if action_result.get('status') == 'error':
            raise RuntimeError(action_result['message'])

        return action_result

    def _shodan_fail(self, reason):
        reason = str(reason)
        reason = f'Error while running Shodan Enrichment: {reason}'
        return generic_fail(internal_axon_ids=self._internal_axon_ids, reason=reason)

    def __run(self) -> EntitiesResult:
        action_result = self._trigger_shodan_adapter()
        return [self.prettify_output(k, v) for k, v in action_result.items()]

    def _run(self) -> EntitiesResult:
        try:
            return self.__run()
        except Exception as e:
            logger.exception('Error while running Shodan Enrichment')
            return self._shodan_fail(e)
