import logging

from axonius.clients.qualys import consts
from axonius.clients.qualys.connection import QualysScansConnection
from axonius.types.enforcement_classes import EntitiesResult
from reports.action_types.action_type_base import ActionTypeBase, generic_fail, generic_success, add_node_selection, \
    add_node_default
from reports.action_types.base.qualys_utils import QualysActionUtils, ACTION_CONFIG_TAGS, ADAPTER_NAME, \
    ACTION_CONFIG_PARENT_TAG, ACTION_CONFIG_USE_ADAPTER

logger = logging.getLogger(f'axonius.{__name__}')


class QualysAddTag(ActionTypeBase):

    @staticmethod
    def config_schema() -> dict:
        schema = {
            'items': [
                {
                    'name': ACTION_CONFIG_USE_ADAPTER,
                    'title': 'Use stored credentials from the Qualys Cloud Platform adapter',
                    'type': 'bool',
                },
                {
                    'name': consts.QUALYS_SCANS_DOMAIN,
                    'title': 'Qualys Cloud Platform domain',
                    'type': 'string'
                },
                {
                    'name': consts.USERNAME,
                    'title': 'User Name',
                    'type': 'string'
                },
                {
                    'name': consts.PASSWORD,
                    'title': 'Password',
                    'type': 'string',
                    'format': 'password'
                },
                {
                    'name': consts.VERIFY_SSL,
                    'title': 'Verify SSL',
                    'type': 'bool'
                },
                {
                    'name': consts.HTTPS_PROXY,
                    'title': 'HTTPS Proxy',
                    'type': 'string'
                },
                {
                    'name': ACTION_CONFIG_TAGS,
                    'title': 'Tags',
                    'type': 'array',
                    'items': {'type': 'string'}
                },
                {
                    'name': ACTION_CONFIG_PARENT_TAG,
                    'title': 'Parent tag name',
                    'type': 'string'
                },
            ],
            'required': [
                ACTION_CONFIG_USE_ADAPTER,
                consts.VERIFY_SSL,
                ACTION_CONFIG_TAGS,
            ],
            'type': 'array',
        }
        return add_node_selection(schema)

    @staticmethod
    def default_config() -> dict:
        default_config = QualysActionUtils.GENERAL_DEFAULT_CONFIG.copy()
        default_config[ACTION_CONFIG_PARENT_TAG] = None
        default_config[ACTION_CONFIG_USE_ADAPTER] = False
        return add_node_default(default_config)

    # pylint: disable=too-many-locals,too-many-statements
    def _run(self) -> EntitiesResult:
        try:
            # pylint: disable=protected-access
            adapter_unique_name = self._plugin_base._get_adapter_unique_name(ADAPTER_NAME, self.action_node_id)
            parent_tag_name = self._config.get(ACTION_CONFIG_PARENT_TAG)
            tags_to_add = self._config.get(ACTION_CONFIG_TAGS) or []
            logger.info(f'Running Add Qualys HostAsset Tag action with tags {tags_to_add}'
                        f' and parent {parent_tag_name}')

            current_result = self._get_entities_from_view({
                'internal_axon_id': 1,
                'adapters.plugin_name': 1,
                'adapters.data.qualys_id': 1,
            })

            # Filter out invalid devices returned by the query
            axon_by_qualys_id = (yield from QualysActionUtils.get_axon_by_qualys_id_and_reject_invalid(current_result))

            qualys_dict = {
                'parent_tag_name': parent_tag_name,
                'tags_to_add': tags_to_add,
                'qualys_ids': list(axon_by_qualys_id.keys())
            }

            if self._config['use_adapter'] is True:
                response = self._plugin_base.request_remote_plugin('add_tag_to_ids', adapter_unique_name, 'POST',
                                                                   json=qualys_dict)
                if response is None:
                    raise ValueError(f'Failed communicating with adapter')
                if response.status_code != 200:
                    return (yield from generic_fail(axon_by_qualys_id.values(), response.text))
                return (yield from generic_success(axon_by_qualys_id.values()))

            if not (self._config.get(consts.QUALYS_SCANS_DOMAIN) and
                    self._config.get(consts.USERNAME) and
                    self._config.get(consts.PASSWORD)):
                return (yield from generic_fail(axon_by_qualys_id.values(), 'Missing Parameters For Connection'))

            # pylint: disable=protected-access
            connection = QualysScansConnection(domain=self._config[consts.QUALYS_SCANS_DOMAIN],
                                               verify_ssl=self._config[consts.VERIFY_SSL],
                                               username=self._config.get(consts.USERNAME),
                                               password=self._config.get(consts.PASSWORD),
                                               https_proxy=self._config.get(consts.HTTPS_PROXY))

            with connection:
                status, error_message = connection.add_tags_to_qualys_ids(axon_by_qualys_id)
                if not status:
                    return (yield from generic_fail(axon_by_qualys_id.values(), error_message))
                return (yield from generic_success(axon_by_qualys_id.values()))
        except Exception:
            logger.exception(f'Problem with action add tag run')
            return (yield from generic_fail(self._internal_axon_ids, 'Unexpected error during action'))
