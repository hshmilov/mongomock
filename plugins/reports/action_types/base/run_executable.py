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
                'use_adapter',
                'executable'
            ],
            'type': 'array'
        }

    @staticmethod
    def default_config() -> dict:
        return {
            'use_adapter': False,
            'executable': None,
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

        logger.info(f'Executing run_executable for {len(self._internal_axon_ids)} devices')
        action_data = {
            'internal_axon_ids': self._internal_axon_ids,
            'action_type': 'deploy',
            'action_name': self._action_saved_name,
            'binary': self._config['executable'],
            'params': self._config.get('params', ''),
            'custom_credentials': credentials
        }
        result = self._plugin_base._trigger_remote_plugin(DEVICE_CONTROL_PLUGIN_NAME,
                                                          priority=True, blocking=True,
                                                          data=action_data).json()
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
