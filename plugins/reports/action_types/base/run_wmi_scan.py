import logging

from funcy import chunks

from axonius.consts.plugin_consts import GENERAL_INFO_PLUGIN_NAME
from axonius.types.enforcement_classes import EntitiesResult, EntityResult

from reports.action_types.action_type_base import ActionTypeBase, generic_fail

logger = logging.getLogger(f'axonius.{__name__}')


class RunWMIScan(ActionTypeBase):
    """
    Runs a WMI Scan
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
                    'name': 'reg_check_exists',
                    'title': 'Registry keys to check for existence',
                    'type': 'array',
                    'items': {
                        'type': 'string'
                    }
                }
            ],
            'required': [
                'use_adapter'
            ],
            'type': 'array'
        }

    @staticmethod
    def default_config() -> dict:
        return {
            'use_adapter': False
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

        for chunk in chunks(30000, self._internal_axon_ids):
            action_data = {
                'internal_axon_ids': chunk,
                'action_type': 'shell',
                'action_name': self._action_saved_name,
                'command': self._config,
                'custom_credentials': credentials
            }
            # pylint: disable=protected-access
            logger.info(f'Sending wmi scan request to {len(chunk)} devices using general info')
            action_result = self._plugin_base._trigger_remote_plugin(
                GENERAL_INFO_PLUGIN_NAME,
                priority=True, blocking=True, data=action_data
            ).json()

            def prettify_output(id_, result: dict) -> EntityResult:
                value = result['value']
                success = result['success']
                return EntityResult(id_, success, value)

            yield from (
                prettify_output(k, v)
                for k, v
                in action_result.items()
            )
