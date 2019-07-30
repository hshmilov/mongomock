import logging

from axonius.clients.linux_ssh.consts import CMD_ACTION_SCHEMA, BASE_DEFAULTS_SCHEMA, ACTION_TYPES
from axonius.consts.plugin_consts import LINUX_SSH_PLUGIN_NAME
from axonius.types.enforcement_classes import EntitiesResult, EntityResult
from reports.action_types.action_type_base import (ActionTypeBase,
                                                   add_node_selection,
                                                   generic_fail, add_node_default)

logger = logging.getLogger(f'axonius.{__name__}')

# pylint: disable=protected-access


class RunLinuxCommand(ActionTypeBase):
    @staticmethod
    def prettify_output(id_, result: dict) -> EntityResult:
        value = result['value']
        success = result['success']
        return EntityResult(id_, success, value)

    @staticmethod
    def config_schema() -> dict:
        return add_node_selection(CMD_ACTION_SCHEMA, LINUX_SSH_PLUGIN_NAME)

    @staticmethod
    def default_config() -> dict:
        return add_node_default(BASE_DEFAULTS_SCHEMA, LINUX_SSH_PLUGIN_NAME)

    def _trigger_linux_adapter(self, node_id):
        action_data = {'internal_axon_ids': self._internal_axon_ids, 'client_config': self._config}
        adapter_unique_name = self._plugin_base._get_adapter_unique_name(LINUX_SSH_PLUGIN_NAME, node_id)
        action_result = self._plugin_base._trigger_remote_plugin(adapter_unique_name,
                                                                 priority=True,
                                                                 blocking=True,
                                                                 data=action_data,
                                                                 job_name=ACTION_TYPES.cmd)
        action_result = action_result.json()
        if action_result.get('status') == 'error':
            raise RuntimeError(action_result['message'])
        return action_result

    def _linux_command_fail(self, reason):
        reason = str(reason)
        reason = f'Error while running Linux Command: {reason}'
        return generic_fail(internal_axon_ids=self._internal_axon_ids, reason=reason)

    def __run(self) -> EntitiesResult:
        node_id = self.action_node_id
        action_result = self._trigger_linux_adapter(node_id)
        return [self.prettify_output(k, v) for k, v in action_result.items()]

    def _run(self) -> EntitiesResult:
        try:
            return self.__run()
        except RuntimeError as e:
            return self._linux_command_fail(e)
        except Exception as e:
            logger.exception('Error while running Linux Command')
            return self._linux_command_fail(e)
