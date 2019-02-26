import logging

from axonius.consts.plugin_consts import DEVICE_CONTROL_PLUGIN_NAME
from axonius.types.enforcement_classes import EntitiesResult, EntityResult

from reports.action_types.action_type_base import ActionTypeBase, generic_fail

logger = logging.getLogger(f'axonius.{__name__}')


# pylint: disable=W0212


class RunExecutable(ActionTypeBase):
    """
    Runs an executable
    """

    @staticmethod
    def config_schema() -> dict:
        return {
            'items': [
                {
                    'name': 'executable',
                    'title': 'File to execute',
                    'type': 'file'
                },
                {
                    'name': 'params',
                    'title': 'Command line',
                    'type': 'string'
                }
            ],
            'required': [
                'executable'
            ],
            'type': 'array'
        }

    @staticmethod
    def default_config() -> dict:
        return {
            'executable': None,
            'params': ''
        }

    def _run(self) -> EntitiesResult:
        action_data = {
            'internal_axon_ids': self._internal_axon_ids,
            'action_type': 'deploy',
            'action_name': self._action_saved_name,
            'binary': self._config['executable'],
            'params': self._config.get('params', '')
        }
        result = self._plugin_base.request_remote_plugin('trigger/execute?priority=True&blocking=True',
                                                         DEVICE_CONTROL_PLUGIN_NAME,
                                                         'post',
                                                         json=action_data).json()
        if result.get('status') == 'error':
            return generic_fail(self._internal_axon_ids, result)

        def prettify_output(id_, result: dict) -> EntityResult:
            value = result['value']
            if isinstance(value, dict):
                value = value['status']
            success = result['success']
            return EntityResult(id_, success, value)

        return [
            prettify_output(k, v)
            for k, v
            in result.items()
        ]
