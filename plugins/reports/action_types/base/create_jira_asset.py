import logging
import requests

from axonius.types.enforcement_classes import EntitiesResult, EntityResult
from axonius.clients.rest.connection import RESTConnection
from reports.action_types.action_type_base import ActionTypeBase

logger = logging.getLogger(f'axonius.{__name__}')

DEFAULT_ORIGIN = 'AxoniusEC'
DEFAULT_ORIGIN_ID = 'axonius-enforcement'
JIRA_API_PATH = 'rest/assetapi/asset'


class CreateJiraAssetAction(ActionTypeBase):
    """
    Create an asset in Jira Assets Platform. See https://developer.atlassian.com/cloud/assetsapi/rest/#api-asset-put
    Asset Origin OriginID will be `internal_axon_id`
    """

    @staticmethod
    def config_schema() -> dict:
        return {
            'items': [
                {
                    'name': 'domain',
                    'title': 'Jira domain',
                    'type': 'string'
                },
                {
                    'name': 'username',
                    'title': 'User name',
                    'type': 'string'
                },
                {
                    'name': 'password',
                    'title': 'API key',
                    'type': 'string',
                    'format': 'password'
                },
                {
                    'name': 'verify_ssl',
                    'title': 'Verify SSL',
                    'type': 'bool'
                },
                {
                    'name': 'https_proxy',
                    'title': 'HTTPS proxy',
                    'type': 'string'
                },
                {
                    'name': 'asset_type_key',
                    'title': 'Asset type appKey',
                    'type': 'string'
                },
                {
                    'name': 'asset_type_id',
                    'title': 'Asset type originId',
                    'type': 'string'
                },
                {
                    'name': 'assignee_id',
                    'title': 'Assignee account ID',
                    'type': 'string',
                    'description': 'The Atlassian account id of the assignee.'
                },
                {
                    'name': 'assignee_email',
                    'title': 'Assignee email',
                    'type': 'string',
                    'description': 'Only provide an email if the accountId field is omitted. '
                                   'A mapping from the provided email to an accountId is attempted. '
                                   'If no matching accountId is found, no assignee will be persisted'
                }
            ],
            'required': [
                'domain',
                'username',
                'password',
                'verify_ssl',
                'asset_type_key',
                'asset_type_id'
            ],
            'type': 'array'
        }

    @staticmethod
    def default_config() -> dict:
        return {
            'domain': None,
            'https_proxy': None,
            'username': None,
            'password': None,
            'verify_ssl': False,
            'assignee_email': None,
            'assignee_id': None,
            'asset_type_key': DEFAULT_ORIGIN,
            'asset_type_id': DEFAULT_ORIGIN_ID
        }

    @staticmethod
    def _populate_entity_fields(entity: dict):
        result = [{
            'fieldId': 'axonius-import-tag',
            'value': 'Imported from Axonius'
        }, ]
        if not isinstance(entity.get('adapters'), list):
            # In this case, raise an exception and stop all devices because this is
            # an internal db error and needs attention.
            logger.error(f'Got bad entity from db: {entity}')
            raise ValueError(entity)
        for from_adapter in entity.get('adapters') or []:
            if not isinstance(from_adapter, dict):
                logger.warning(f'Got bad adapter data: {from_adapter}')
                continue
            data_from_adapter = from_adapter.get('data')
            if not isinstance(data_from_adapter, dict):
                logger.warning(f'Got bad adapter data: {data_from_adapter}')
                continue
            adapter_name = from_adapter.get('plugin_name') or 'UNKNOWN'
            for field_name, field_value in data_from_adapter.items():
                result.append({
                    'fieldId': f'{adapter_name}.{field_name}',
                    'value': str(field_value)
                })
        return result

    @staticmethod
    def _get_entity_label(entity: dict):
        if not isinstance(entity.get('adapters'), list):
            # In this case, raise an exception and stop all devices because this is
            # an internal db error and needs attention.
            logger.error(f'Got bad entity from db: {entity}')
            raise ValueError(entity)
        for from_adapter in entity.get('adapters') or []:
            if not isinstance(from_adapter, dict):
                logger.warning(f'Got bad adapter data: {from_adapter}')
                continue
            data_from_adapter = from_adapter.get('data')
            if not isinstance(data_from_adapter, dict):
                logger.warning(f'Got bad adapter data: {data_from_adapter}')
                continue
            if data_from_adapter.get('name'):
                return data_from_adapter.get('name')
            if data_from_adapter.get('hostname'):
                return data_from_adapter.get('hostname')
        # Raise KeyError in case internal_axon_id does not exist
        # which it should, in any entity returned from Axonius DB
        return entity['internal_axon_id']

    @staticmethod
    def _get_entity_origin_id(entity: dict):
        # Raise KeyError in case internal_axon_id does not exist
        # which it should, in any entity returned from Axonius DB
        return entity['internal_axon_id']

    def _run(self) -> EntitiesResult:

        projection = {
            'internal_axon_id': 1,
            'adapters.plugin_name': 1,
            'adapters.data.hostname': 1,
            'adapters.data.id': 1,
            'adapters.data.name': 1,
            'adapters.data.os.type': 1,
            'adapters.data.device_serial': 1,
            'adapters.data.device_manufacturer': 1,
            'adapters.data.network_interfaces.mac': 1,
            'adapters.data.network_interfaces.ips': 1,
            'adapters.data.description': 1,
            'adapters.data.domain': 1,
        }
        current_result = self._get_entities_from_view(projection)
        url = RESTConnection.build_url(self._config['domain'], url_base_prefix=JIRA_API_PATH)
        results = []
        for entry in current_result:
            try:
                origin = {
                    'appKey': self._config.get('asset_type_key'),
                    'originId': self._get_entity_origin_id(entry)
                }
                label = {
                    'value': self._get_entity_label(entry)
                }
                asset_type = {
                    'appKey': self._config.get('asset_type_key'),
                    'originId': self._config.get('asset_type_id')
                }
                assignee = {
                    'accountId': self._config.get('assignee_id'),
                    'email': self._config.get('assignee_email')
                }
                if assignee['accountId']:
                    assignee['email'] = None  # Enforce no email if assignee id is provided, see JIRA API docs
                device_fields = self._populate_entity_fields(entry)
                body_dict = {
                    'origin': origin,
                    'label': label,
                    'type': asset_type,
                    'assignee': assignee,
                    'fields': device_fields
                }
                if self._config.get('https_proxy'):
                    proxies = {'https': self._config.get('https_proxy')}
                else:
                    proxies = None
                logger.debug(f'Sending device details {body_dict} to {url}')
                response = requests.put(url,
                                        data=body_dict,
                                        verify=self._config['verify_ssl'],
                                        auth=(self._config['username'], self._config['password']),
                                        proxies=proxies
                                        )
                result = response.status_code == 200
                # response.text in case of success is not human-readable, but in case of failure is important.
                message = None if result else response.text
                logger.info(f'Got {response.status_code}:{response.text} from {url}')
                results.append(EntityResult(entry['internal_axon_id'], result, message or 'Success'))
            except Exception:
                logger.exception(f'Problem with entry {entry}')
                results.append(EntityResult(entry['internal_axon_id'], False, 'Unexpected Error'))
        return results
