import logging

from axonius.consts.plugin_consts import DEVICE_CONTROL_PLUGIN_NAME
from axonius.types.enforcement_classes import EntitiesResult, EntityResult

from reports.action_types.action_type_base import ActionTypeBase, generic_fail

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
                    'name': 'use_adapter',
                    'title': 'Use stored credentials from the Active Directory adapter',
                    'type': 'bool'
                },
                {
                    'name': 'wmi_username',
                    'title': 'WMI User',
                    'type': 'string'
                },
                {
                    'name': 'wmi_password',
                    'title': 'WMI Password',
                    'type': 'string',
                    'format': 'password'
                },
                {
                    'name': 'params',
                    'title': 'Command line parameters',
                    'type': 'string'
                },
                {
                    'name': 'extra_files',
                    'title': 'Files to deploy',
                    'type': 'array',
                    'items':
                        {
                            'name': 'file',
                            'title': 'File',
                            'type': 'file',
                            'items': [
                                {
                                    'name': 'file',
                                    'title': 'File',
                                    'type': 'file'
                                }
                            ]
                        }
                }
            ],
            'required': [
                'use_adapter',
                'params'
            ],
            'type': 'array'
        }

    @staticmethod
    def default_config() -> dict:
        return {
            'use_adapter': False,
            'params': ''
        }

    def _run(self) -> EntitiesResult:
        credentials_exist = self._config.get('wmi_username') and self._config.get('wmi_password')
        use_adapter = self._config.get('use_adapter')

        if not credentials_exist and not use_adapter:
            return generic_fail(
                self._internal_axon_ids,
                reason=f'Please use the adapter credentials or specify custom credentials'
            )

        if use_adapter:
            credentials = {}
        else:
            credentials = {
                'username': self._config.get('wmi_username'),
                'password': self._config.get('wmi_password')
            }

        logger.info(f'Executing run_cmd for {len(self._internal_axon_ids)} devices')
        action_data = {
            'internal_axon_ids': self._internal_axon_ids,
            'action_type': 'shell',
            'action_name': self._action_saved_name,
            'extra_files': self._config.get('extra_files') or [],
            'command': self._config['params'],
            'custom_credentials': credentials
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
