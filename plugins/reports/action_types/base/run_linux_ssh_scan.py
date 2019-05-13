import logging
import copy

from axonius.plugin_base import PluginBase
from axonius.consts.plugin_consts import LINUX_SSH_PLUGIN_NAME
from axonius.types.enforcement_classes import EntitiesResult, EntityResult
from axonius.clients.linux_ssh.consts import ACTION_SCHEMA, INSTANCE, DEFAULT_INSTANCE
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
        plugin_base = PluginBase.Instance
        schema = copy.deepcopy(ACTION_SCHEMA)
        node_names = [instance['node_name'] for instance in plugin_base._get_nodes_table()]
        for item in schema['items']:
            if item['name'] == INSTANCE:
                item['enum'] = node_names
                break
        return schema

    @staticmethod
    def default_config() -> dict:
        return {}

    def _trigger_linux_adapter(self, node_name):
        action_data = {'internal_axon_ids': self._internal_axon_ids, 'client_config': self._config}

        adapter_unique_name = self._plugin_base._get_adapter_unique_name(LINUX_SSH_PLUGIN_NAME, node_name)
        action_result = self._plugin_base._trigger_remote_plugin(
            adapter_unique_name, priority=True, blocking=True, data=action_data
        )
        action_result = action_result.json()

        if action_result.get('status') == 'error':
            raise RuntimeError(action_result['message'])

        return action_result

    def _linux_ssh_fail(self, reason):
        reason = str(reason)
        reason = f'Error while running Linux SSH Scan: {reason}'
        return generic_fail(internal_axon_ids=self._internal_axon_ids, reason=reason)

    def __run(self) -> EntitiesResult:
        node_name = self._config.get(INSTANCE) or DEFAULT_INSTANCE
        action_result = self._trigger_linux_adapter(node_name)
        return [self.prettify_output(k, v) for k, v in action_result.items()]

    def _run(self) -> EntitiesResult:
        try:
            return self.__run()
        except RuntimeError as e:
            return self._linux_ssh_fail(e)
        except Exception as e:
            logger.exception('Error while running Linux SSH Scan')
            return self._linux_ssh_fail(e)
