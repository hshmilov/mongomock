import logging

from axonius.consts.plugin_consts import DEVICE_CONTROL_PLUGIN_NAME
from axonius.types.enforcement_classes import EntitiesResult, EntityResult

from reports.action_types.action_type_base import ActionTypeBase

logger = logging.getLogger(f'axonius.{__name__}')


# pylint: disable=W0212


class RunCmd(ActionTypeBase):
    """
    Runs an cmd
    """

    @staticmethod
    def config_schema() -> dict:
        return {
            'items': [
                {
                    'name': 'params',
                    'title': 'Command line parameters',
                    'type': 'string'
                }
            ],
            'required': [
                'params'
            ],
            'type': 'array'
        }

    @staticmethod
    def default_config() -> dict:
        return {
            'params': ''
        }

    def _run(self) -> EntitiesResult:
        action_data = {
            'internal_axon_ids': self._internal_axon_ids,
            'action_type': 'shell',
            'action_name': self._action_saved_name,
            'command': self._config['params']
        }
        result = self._plugin_base._trigger_remote_plugin(DEVICE_CONTROL_PLUGIN_NAME,
                                                          priority=True, blocking=True,
                                                          data=action_data).json()

        def prettify_output(id_, result: dict) -> EntityResult:
            value = result['value']
            success = result['success']
            return EntityResult(id_, success, value)

        return [
            prettify_output(k, v)
            for k, v
            in result.items()
        ]
