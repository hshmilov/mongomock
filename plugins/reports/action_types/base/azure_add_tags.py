import logging

# pylint: disable=no-name-in-module,import-error
from azure.mgmt.resource import ResourceManagementClient
from msrestazure.azure_active_directory import ServicePrincipalCredentials
from msrestazure import azure_cloud
from axonius.clients.rest.connection import RESTConnection
from axonius.types.enforcement_classes import EntityResult, EntitiesResult
from reports.action_types.action_type_base import ActionTypeBase, add_node_default, add_node_selection, generic_fail

logger = logging.getLogger(f'axonius.{__name__}')

AZURE_SUBSCRIPTION_ID = 'subscription_id'
AZURE_CLIENT_ID = 'client_id'
AZURE_CLIENT_SECRET = 'client_secret'
AZURE_TENANT_ID = 'tenant_id'
AZURE_VERIFY_SSL = 'verify_ssl'
AZURE_CLOUD_ENVIRONMENT = 'cloud_environment'

PROXY = 'https_proxy'
TAG_KEY = 'tag_key'
TAG_VALUE = 'tag_value'

AZURE_ACTION_REQUIRED_PARAMS = [
    'internal_axon_id',
    'adapters.data.cloud_id',
    'adapters.plugin_name',
]
ADAPTER_NAME = 'azure_adapter'


class AzureClient:
    DEFAULT_CLOUD = 'Azure Public Cloud'

    @classmethod
    def get_clouds(cls):
        clouds = {}
        for name in dir(azure_cloud):
            item = getattr(azure_cloud, name)
            if isinstance(item, azure_cloud.Cloud):
                # use a nice name, format example: AZURE_US_GOV_CLOUD -> Azure US Gov Cloud
                clouds[name.replace('_', ' ').title().replace('Us ', 'US ')] = item
        assert cls.DEFAULT_CLOUD in clouds
        return clouds

    @classmethod
    def get_creds(cls, config_dict):
        cloud = cls.get_clouds()[config_dict[AZURE_CLOUD_ENVIRONMENT]]
        https_proxy = config_dict[PROXY]
        proxies = {'https': RESTConnection.build_url(https_proxy).strip('/')} if https_proxy else None
        client_id = config_dict[AZURE_CLIENT_ID]
        client_secret = config_dict[AZURE_CLIENT_SECRET]
        tenant_id = config_dict[AZURE_TENANT_ID]
        verify_ssl = config_dict[AZURE_VERIFY_SSL]
        credentials = ServicePrincipalCredentials(client_id=client_id, secret=client_secret, tenant=tenant_id,
                                                  cloud_environment=cloud, proxies=proxies, verify=verify_ssl)
        return credentials


class AzureAddTagsAction(ActionTypeBase):
    """
    Azure Add Tag to Resource
    XXX WARNING: this is a CREATE OR UPDATE operation, meaning existing data may be OVERWRITTEN!
    For more details see https://docs.microsoft.com/en-us/rest/api/resources/tags/createorupdateatscope
    """
    @staticmethod
    def config_schema() -> dict:
        schema = {
            'items': [
                {
                    'name': AZURE_SUBSCRIPTION_ID,
                    'title': 'Azure subscription ID',
                    'type': 'string'
                },
                {
                    'name': AZURE_CLOUD_ENVIRONMENT,
                    'title': 'Cloud environment',
                    'type': 'string',
                    'enum': list(AzureClient.get_clouds().keys()),
                    'default': AzureClient.DEFAULT_CLOUD
                },
                {
                    'name': AZURE_CLIENT_ID,
                    'title': 'Azure client ID',
                    'type': 'string'
                },
                {
                    'name': AZURE_CLIENT_SECRET,
                    'title': 'Azure client secret',
                    'type': 'string',
                    'format': 'password'
                },
                {
                    'name': AZURE_TENANT_ID,
                    'title': 'Azure tenant ID',
                    'type': 'string'
                },
                {
                    'name': AZURE_VERIFY_SSL,
                    'title': 'Verify SSL',
                    'type': 'bool',
                    'default': True
                },
                {
                    'name': PROXY,
                    'title': 'HTTPS proxy',
                    'type': 'string'
                },
                {
                    'name': TAG_KEY,
                    'title': 'Tag name',
                    'type': 'string',
                    'description': 'A tag name can have a maximum of 512 characters and is case-insensitive. '
                                   'Tag names cannot have the following prefixes which are reserved for Azure use: '
                                   '"microsoft", "azure", "windows".'
                },
                {
                    'name': TAG_VALUE,
                    'title': 'Tag value',
                    'type': 'string'
                },
            ],
            'required': [
                AZURE_SUBSCRIPTION_ID,
                AZURE_CLOUD_ENVIRONMENT,
                AZURE_CLIENT_ID,
                AZURE_CLIENT_SECRET,
                AZURE_TENANT_ID,
                TAG_KEY,
                AZURE_VERIFY_SSL,
            ],
            'type': 'array'
        }
        return add_node_selection(schema)

    @staticmethod
    def default_config() -> dict:
        return add_node_default({
            AZURE_SUBSCRIPTION_ID: None,
            AZURE_CLIENT_ID: None,
            AZURE_CLIENT_SECRET: None,
            AZURE_TENANT_ID: None,
            AZURE_CLOUD_ENVIRONMENT: AzureClient.DEFAULT_CLOUD,
            TAG_KEY: None,
            TAG_VALUE: None,
            PROXY: None,
            AZURE_VERIFY_SSL: True,
        })

    @staticmethod
    def _build_request_body(tag_name, tag_value=None):
        return {
            'properties': {
                'tags': {
                    tag_name: tag_value
                }
            }
        }

    @staticmethod
    def _get_adapter_data(entity):
        for plugin in entity['adapters']:
            if plugin.get('plugin_name') == ADAPTER_NAME:
                yield plugin.get('data') or {}
        return {}

    # pylint:disable=E1101
    def _run(self) -> EntitiesResult:
        results = list()
        try:
            current_result = self._get_entities_from_view(
                {param: 1 for param in AZURE_ACTION_REQUIRED_PARAMS}
            )
            creds = AzureClient.get_creds(self._config)
            azure_ids_list = list()
            for entity in current_result:
                adapter_data = self._get_adapter_data(entity)
                for datum in adapter_data:
                    scope = datum.get('cloud_id')
                    if scope:
                        azure_ids_list.append((scope, entity['internal_axon_id']))

            with ResourceManagementClient(creds, self._config[AZURE_SUBSCRIPTION_ID]) as client:
                tags_obj = client.resources.models.Tags(
                    tags={
                        self._config[TAG_KEY]: self._config[TAG_VALUE]
                    }
                )
                props = client.resources.models.TagsResource(properties=tags_obj)
                for scope, axon_id in azure_ids_list:
                    try:
                        logger.info(f'Adding tag {tags_obj.as_dict()} to {scope}')
                        client.tags.resource_create(scope, props)
                    except Exception as e:
                        message = f'Failed to add tag: {str(e)}'
                        logger.exception(message)
                        success = False
                    else:
                        success = True
                        message = 'Success'
                        logger.info(f'Operation successful!')
                    finally:
                        results.append(EntityResult(axon_id, success, message))
        except Exception as e:
            logger.exception(f'Problem with add tag action: {str(e)}')
            return (yield from generic_fail(self._internal_axon_ids, 'Unexpected error during action'))
        return (yield from results)
