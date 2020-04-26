import logging

from axonius.consts import report_consts
from axonius.types.enforcement_classes import AlertActionResult
from axonius.clients.cherwell.connection import CherwellConnection
from reports.action_types.action_type_alert import ActionTypeAlert
from reports.action_types.action_type_base import add_node_selection, add_node_default

logger = logging.getLogger(f'axonius.{__name__}')

ADAPTER_NAME = 'cherwell_adapter'

# pylint: disable=W0212


class CherwellIncidentAction(ActionTypeAlert):
    """
    Creates an incident in the Cherwell account
    """

    @staticmethod
    def config_schema() -> dict:
        schema = {
            'items': [
                {
                    'name': 'use_adapter',
                    'title': 'Use stored credentials from the Cherwell adapter',
                    'type': 'bool'
                },
                {
                    'name': 'domain',
                    'title': 'Cherwell domain',
                    'type': 'string'
                },
                {
                    'name': 'username',
                    'title': 'User name',
                    'type': 'string'
                },
                {
                    'name': 'password',
                    'title': 'Password',
                    'type': 'string',
                    'format': 'password'
                },
                {
                    'name': 'client_id',
                    'title': 'Client ID',
                    'type': 'string'
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
                    'name': 'short_description',
                    'title': 'Short description',
                    'type': 'string'
                },
                {
                    'name': 'incident_description',
                    'title': 'Incident description',
                    'type': 'string'
                },
                {
                    'name': 'description_default',
                    'title': 'Add default incident description',
                    'type': 'bool'
                },
                {
                    'name': 'customer_display_name',
                    'title': 'Customer display name',
                    'type': 'string'
                },
                {
                    'name': 'priority',
                    'title': 'Priority',
                    'type': 'integer'
                },
                {
                    'name': 'source',
                    'title': 'Source',
                    'type': 'string'
                },
                {
                    'name': 'service',
                    'title': 'Service',
                    'type': 'string'
                },
                {
                    'name': 'category',
                    'type': 'string',
                    'title': 'Category'
                },
                {
                    'name': 'subcategory',
                    'type': 'string',
                    'title': 'Subcategory'
                },
                {
                    'name': 'incident_type',
                    'title': 'Incident type',
                    'type': 'string'
                },
                {
                    'name': 'status',
                    'title': 'Status',
                    'type': 'string'
                }
            ],
            'required': [
                'verify_ssl',
                'priority',
                'use_adapter',
                'incident_description',
                'description_default'
            ],
            'type': 'array'
        }
        return add_node_selection(schema)

    @staticmethod
    def default_config() -> dict:
        return add_node_default({
            'use_adapter': False,
            'domain': None,
            'username': None,
            'customer_display_name': None,
            'password': None,
            'priority': 5,
            'https_proxy': None,
            'incident_description': None,
            'service': None,
            'source': None,
            'category': None,
            'subcategory': None,
            'short_description': None,
            'verify_ssl': False,
            'status': None,
            'client_id': None,
            'incident_type': None
        })

    # pylint: disable=too-many-arguments
    def _create_cherwell_incident(self, description,
                                  customer_display_name, status,
                                  service, priority, source,
                                  category, subcategory, incident_type, short_description):
        adapter_unique_name = self._plugin_base._get_adapter_unique_name(ADAPTER_NAME, self.action_node_id)
        cherwell_dict = {'description': description,
                         'customer_display_name': customer_display_name,
                         'service': service,
                         'category': category,
                         'subcategory': subcategory,
                         'source': source,
                         'priority': priority,
                         'incident_type': incident_type,
                         'short_description': short_description,
                         'status': status
                         }
        if self._config['use_adapter'] is True:
            response = self._plugin_base.request_remote_plugin('create_incident', adapter_unique_name, 'post',
                                                               json=cherwell_dict)
            return response.text
        try:
            if not self._config.get('domain') or not self._config.get('username') or not self._config.get('password'):
                return 'Missing Parameters For Connection'
            cherwell_connection = CherwellConnection(domain=self._config['domain'],
                                                     client_id=self._config.get('client_id'),
                                                     verify_ssl=self._config.get('verify_ssl'),
                                                     username=self._config.get('username'),
                                                     password=self._config.get('password'),
                                                     https_proxy=self._config.get('https_proxy'))
            with cherwell_connection:
                cherwell_connection.create_incident(cherwell_dict)
                return ''
        except Exception as e:
            logger.exception(f'Got exception creating Cherwell ')
            return f'Got exception creating Cherwell incident: {str(e)}'

    def _run(self) -> AlertActionResult:
        if not self._internal_axon_ids:
            return AlertActionResult(False, 'No Data')
        query_name = self._run_configuration.view.name
        old_results_num_of_devices = len(self._internal_axon_ids) + len(self._removed_axon_ids) - \
            len(self._added_axon_ids)
        query_link = self._generate_query_link(query_name)
        log_message = report_consts.REPORT_CONTENT.format(name=self._report_data['name'],
                                                          query=query_name,
                                                          num_of_triggers=self._run_configuration.times_triggered,
                                                          trigger_message=self._get_trigger_description(),
                                                          num_of_current_devices=len(self._internal_axon_ids),
                                                          old_results_num_of_devices=old_results_num_of_devices,
                                                          query_link=query_link)
        incident_description = self._config.get('incident_description')
        if self._config['description_default']:
            incident_description += '\n' + log_message

        message = self._create_cherwell_incident(description=incident_description,
                                                 category=self._config.get('category'),
                                                 customer_display_name=self._config.get('customer_display_name'),
                                                 service=self._config.get('service'),
                                                 priority=self._config.get('priority'),
                                                 source=self._config.get('source'),
                                                 status=self._config.get('status'),
                                                 subcategory=self._config.get('subcategory'),
                                                 incident_type=self._config.get('incident_type'),
                                                 short_description=self._config.get('short_description')
                                                 )
        return AlertActionResult(not message, message or 'Success')
