import logging

from funcy import chunks

from axonius.consts.plugin_consts import ACTIVE_DIRECTORY_PLUGIN_NAME
from axonius.types.enforcement_classes import EntitiesResult, EntityResult

from reports.action_types.action_type_base import ActionTypeBase, generic_fail, add_node_default, add_node_selection

logger = logging.getLogger(f'axonius.{__name__}')


CHUNK_SIZE = 5000


class ChangeLdapAttribute(ActionTypeBase):
    """
    Change Ldap attribute
    """
    @staticmethod
    def prettify_output(id_, result: dict) -> EntityResult:
        value = result['value']
        success = result['success']
        return EntityResult(id_, success, value)

    @staticmethod
    def config_schema() -> dict:
        schema = {
            'items': [
                {
                    'name': 'use_adapter',
                    'title': 'Use stored credentials from the Active Directory adapter',
                    'type': 'bool'
                },
                {
                    'name': 'username',
                    'title': 'User Name',
                    'type': 'string'
                },
                {
                    'name': 'password',
                    'title': 'Password',
                    'type': 'string',
                    'format': 'password'
                },
                {
                    'name': 'ldap_attributes',
                    'title': 'LDAP Attributes',
                    'type': 'array',
                    'items':
                        {
                            'name': 'ldap_attributes',
                            'title': 'Attributes',
                            'type': 'array',
                            'required': True,
                            'items': [
                                {
                                    'name': 'attribute_name',
                                    'title': 'Attribute Name',
                                    'type': 'string',
                                    'required': True
                                },
                                {
                                    'name': 'attribute_value',
                                    'title': 'Attribute Value',
                                    'type': 'string',
                                    'required': True
                                }
                            ]
                        }
                },
            ],
            'required': [
                'use_adapter',
                'ldap_attributes',
            ],
            'type': 'array'
        }
        return add_node_selection(schema, ACTIVE_DIRECTORY_PLUGIN_NAME)

    @staticmethod
    def default_config() -> dict:
        return add_node_default({'use_adapter': False}, ACTIVE_DIRECTORY_PLUGIN_NAME)

    def _run(self) -> EntitiesResult:
        credentials_exist = self._config.get('username') and self._config.get('password')
        use_adapter = self._config.get('use_adapter')

        if not credentials_exist and not use_adapter:
            yield from generic_fail(
                self._internal_axon_ids,
                reason=f'Please use the adapter credentials or specify custom credentials'
            )
            return

        if use_adapter:
            credentials = {}
        else:
            credentials = {
                'username': self._config.get('username'),
                'password': self._config.get('password')
            }

        for chunk in chunks(CHUNK_SIZE, self._internal_axon_ids):
            action_data = {
                'internal_axon_ids': self._internal_axon_ids,
                'client_config': self._config,
                'credentials': credentials,
                'entity': self._entity_type.value
            }
            # pylint: disable=protected-access
            logger.info(f'Sending change ldap attributes request to {len(chunk)} devices using active directory')
            adapter_unique_name = self._plugin_base._get_adapter_unique_name(
                ACTIVE_DIRECTORY_PLUGIN_NAME, self.action_node_id)
            action_result = self._plugin_base._trigger_remote_plugin(
                adapter_unique_name,
                priority=True, blocking=True, data=action_data, job_name='change_ldap_attributes'
            ).json()

            yield from (
                self.prettify_output(k, v)
                for k, v
                in action_result.items()
            )
