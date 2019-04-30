import logging

from axonius.consts.plugin_consts import LINUX_SSH_PLUGIN_NAME
from axonius.types.enforcement_classes import EntitiesResult, EntityResult
from axonius.clients.linux_ssh.consts import ACTION_SCHEMA
from reports.action_types.action_type_base import ActionTypeBase, generic_fail

logger = logging.getLogger(f'axonius.{__name__}')

# pylint: disable=protected-access


class RunLinuxSSHScan(ActionTypeBase):
    @staticmethod
    def prettify_output(id_, result: dict) -> EntityResult:
        value = result['value']
        success = result['success']
        return EntityResult(id_, success, value)

    @staticmethod
    def config_schema() -> dict:
        return ACTION_SCHEMA

    @staticmethod
    def default_config() -> dict:
        return {}

    def __run(self) -> EntitiesResult:
        action_data = {'internal_axon_ids': self._internal_axon_ids, 'client_config': self._config}

        action_result = self._plugin_base._trigger_remote_plugin(
            LINUX_SSH_PLUGIN_NAME, priority=True, blocking=True, data=action_data
        )
        action_result = action_result.json()
        if action_result.get('status') == 'error':
            return generic_fail(self._internal_axon_ids,
                                f'Error while running Linux SSH scan: {action_result["message"]}')

        return [self.prettify_output(k, v) for k, v in action_result.items()]

    def _run(self) -> EntitiesResult:
        try:
            return self.__run()
        except Exception as e:
            logger.exception('Failed to run action')
            return generic_fail(self._internal_axon_ids, reason=f'Error while running Linux SSH scan:{str(e)}')
