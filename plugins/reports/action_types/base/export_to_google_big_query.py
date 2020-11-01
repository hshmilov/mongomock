import json
import logging

from axonius.clients.google_big_query.connection import GoogleBigQueryConnection
from axonius.types.enforcement_classes import AlertActionResult
from axonius.utils import db_querying_helper, gui_helpers
from axonius.utils.gui_helpers import get_fields_type_by_name
from reports.action_types.action_type_alert import ActionTypeAlert
from reports.action_types.action_type_base import add_node_selection, add_node_default

logger = logging.getLogger(f'axonius.{__name__}')


class ExportToGoogleBigQuery(ActionTypeAlert):
    """
    Export Table to Google Big Query.
    For now we do not support 'use_adapter' option, because Google Big Query Adapter is not public.
    """
    @staticmethod
    def default_config() -> dict:
        return add_node_default({
            'table_name': None,
            'project_id': None,
            'dataset_id': None,
            'keypair_file': None,
            'verify_ssl': False,
            'https_proxy': None,
            'proxy_username': None,
            'proxy_password': None,
        })

    @staticmethod
    def _get_valid_field_name(field):
        return field.replace('.', '_').replace('-', '_').replace(' ', '_')

    def _get_valid_field_list(self, field_list):
        return [self._get_valid_field_name(field) for field in field_list]

    # pylint: disable=protected-access
    def _run(self) -> AlertActionResult:
        if not self._internal_axon_ids:
            return AlertActionResult(False, 'No Data')

        table_id = self._config['table_name']
        field_list = self.trigger_view_config.get('fields', [
            'specific_data.data.name', 'specific_data.data.hostname', 'specific_data.data.os.type',
            'specific_data.data.last_used_users', 'labels'
        ])

        fields_type_by_name = get_fields_type_by_name(self._entity_type)
        fields_with_types = {self._get_valid_field_name(field): fields_type_by_name.get(field) for field in field_list}

        entities = list(db_querying_helper.get_entities(
            limit=0,
            skip=0,
            view_filter=self.trigger_view_parsed_filter,
            sort=gui_helpers.get_sort(self.trigger_view_config),
            projection={field: 1 for field in field_list},
            entity_type=self._entity_type,
            field_filters=self.trigger_view_config.get('colFilters', {}),
            excluded_adapters=self.trigger_view_config.get('colExcludedAdapters', {}))[0])

        field_list = self._get_valid_field_list(field_list)

        entities = [
            {self._get_valid_field_name(field_name): str(value) for field_name, value in
             entity.items() if self._get_valid_field_name(field_name) in field_list} for
            entity in entities]

        if not (self._config.get('keypair_file') and
                self._config.get('project_id') and
                self._config.get('dataset_id')):
            return AlertActionResult(
                False,
                'Missing Paramaters For Connection')

        connection = GoogleBigQueryConnection(
            domain='https://bigquery.googleapis.com',
            https_proxy=self._config.get('https_proxy'),
            service_account_file=json.loads(
                self._plugin_base._grab_file_contents(self._config.get('keypair_file'))),
            project_id=self._config.get('project_id'),
            dataset_id=self._config.get('dataset_id')
        )

        with connection:
            try:
                status, message = connection.create_table(table_id, fields_with_types, entities)
                if not status:
                    return AlertActionResult(
                        False,
                        message)
                return AlertActionResult(
                    True,
                    'Exported to Google Big Query')
            except Exception as e:
                return AlertActionResult(
                    False,
                    f'Failed to export table to Google Big Query {str(e)}')

    @staticmethod
    def config_schema() -> dict:
        return add_node_selection({
            'items': [
                {
                    'name': 'table_name',
                    'title': 'Table name',
                    'type': 'string',
                },
                {
                    'name': 'project_id',
                    'title': 'Project ID',
                    'description': 'The ID of the Google Cloud Project',
                    'type': 'string'
                },
                {
                    'name': 'dataset_id',
                    'title': 'Dataset ID',
                    'description': 'The ID of the Google Big Query Dataset',
                    'type': 'string'
                },
                {
                    'name': 'keypair_file',
                    'title': 'JSON Key pair for the service account authentication',
                    'description': 'The binary contents of the JSON keypair file',
                    'type': 'file',
                },

                {
                    'name': 'verify_ssl',
                    'title': 'Verify SSL',
                    'type': 'bool',
                    'default': False
                },
                {
                    'name': 'https_proxy',
                    'title': 'HTTPS proxy',
                    'type': 'string'
                },
                {
                    'name': 'proxy_username',
                    'title': 'HTTPS proxy user name',
                    'type': 'string'
                },
                {
                    'name': 'proxy_password',
                    'title': 'HTTPS proxy password',
                    'type': 'string',
                    'format': 'password'
                }
            ],
            'required': [
                'table_name',
                'verify_ssl',
                'project_id',
                'dataset_id',
                'keypair_file'
            ],
            'type': 'array'
        })
