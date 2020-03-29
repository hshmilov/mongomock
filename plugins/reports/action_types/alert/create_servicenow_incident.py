import logging

from axonius.consts import report_consts
from axonius.types.enforcement_classes import AlertActionResult
from axonius.utils.axonius_query_language import parse_filter
from axonius.utils import gui_helpers
from axonius.clients.service_now.connection import ServiceNowConnection
from reports.action_types.action_type_alert import ActionTypeAlert
from reports.action_types.action_type_base import add_node_selection, add_node_default

logger = logging.getLogger(f'axonius.{__name__}')

ADAPTER_NAME = 'service_now_adapter'

# pylint: disable=W0212


class ServiceNowIncidentAction(ActionTypeAlert):
    """
    Creates an incident in the ServiceNow account
    """

    @staticmethod
    def config_schema() -> dict:
        schema = {
            'items': [
                {
                    'name': 'use_adapter',
                    'title': 'Use stored credentials from the ServiceNow adapter',
                    'type': 'bool'
                },
                {
                    'name': 'domain',
                    'title': 'ServiceNow domain',
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
                    'name': 'incident_title',
                    'title': 'Incident short description',
                    'type': 'string'
                },
                {
                    'name': 'add_link_to_title',
                    'type': 'bool',
                    'title': 'Add link to Saved Query to the incident short description'
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
                    'name': 'severity',
                    'title': 'Message severity',
                    'type': 'string',
                    'enum': [
                        'info', 'warning', 'error'
                    ]
                },
                {
                    'name': 'u_incident_type',
                    'type': 'string',
                    'title': 'Incident Type'
                },
                {
                    'name': 'caller_id',
                    'title': 'Caller ID',
                    'type': 'string'
                },
                {
                    'name': 'u_requested_for',
                    'title': 'Requested for',
                    'type': 'string'
                },
                {
                    'name': 'u_symptom',
                    'title': 'Symptom',
                    'type': 'string'
                },
                {
                    'name': 'assignment_group',
                    'title': 'Assignment group',
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
                    'name': 'extra_fields',
                    'title': 'Extra Fields',
                    'type': 'string'
                },
                {
                    'name': 'send_csv_as_attachment',
                    'title': 'Send CSV As Attachment',
                    'type': 'bool'
                }
            ],
            'required': [
                'use_adapter',
                'verify_ssl',
                'description_default',
                'incident_description',
                'description_default',
                'severity',
                'incident_title',
                'add_link_to_title',
                'send_csv_as_attachment'
            ],
            'type': 'array'
        }
        return add_node_selection(schema)

    @staticmethod
    def default_config() -> dict:
        return add_node_default({
            'severity': 'info',
            'description_default': False,
            'extra_fields': None,
            'incident_description': None,
            'incident_title': None,
            'use_adapter': False,
            'domain': None,
            'username': None,
            'password': None,
            'https_proxy': None,
            'verify_ssl': True,
            'u_symptom': None,
            'assignment_group': None,
            'u_requested_for': None,
            'caller_id': None,
            'category': None,
            'add_link_to_title': False,
            'subcategory': None,
            'send_csv_as_attachment': False
        })

    # pylint: disable=too-many-arguments
    def _create_service_now_incident(self, short_description, description, impact, u_incident_type,
                                     caller_id, u_symptom, assignment_group, u_requested_for,
                                     category=None, subcategory=None,
                                     extra_fields=None, csv_string=None):
        adapter_unique_name = self._plugin_base._get_adapter_unique_name(ADAPTER_NAME, self.action_node_id)
        service_now_dict = {'short_description': short_description,
                            'description': description,
                            'impact': impact,
                            'u_incident_type': u_incident_type,
                            'caller_id': caller_id,
                            'u_symptom': u_symptom,
                            'assignment_group': assignment_group,
                            'u_requested_for': u_requested_for,
                            'category': category,
                            'subcategory': subcategory,
                            'extra_fields': extra_fields,
                            'csv_string': csv_string
                            }
        try:
            if self._config['use_adapter'] is True:
                response = self._plugin_base.request_remote_plugin('create_incident', adapter_unique_name, 'post',
                                                                   json=service_now_dict)
                return response.text
            if not self._config.get('domain') or not self._config.get('username') or not self._config.get('password'):
                return 'Missing Parameters For Connection'
            service_now_connection = ServiceNowConnection(domain=self._config['domain'],
                                                          verify_ssl=self._config.get('verify_ssl'),
                                                          username=self._config.get('username'),
                                                          password=self._config.get('password'),
                                                          https_proxy=self._config.get('https_proxy'))
            with service_now_connection:
                service_now_connection.create_service_now_incident(service_now_dict)
                return ''
        except Exception as e:
            logger.exception(f'Got exception creating ServiceNow incident wiht {service_now_dict}')
            return f'Got exception creating ServiceNow incident: {str(e)}'

    def _run(self) -> AlertActionResult:
        if not self._internal_axon_ids:
            return AlertActionResult(False, 'No Data')
        query_name = self._run_configuration.view.name
        old_results_num_of_devices = len(self._internal_axon_ids) + len(self._removed_axon_ids) - \
            len(self._added_axon_ids)
        query_link = self._generate_query_link(query_name)
        short_description = self._config['incident_title']
        if self._config.get('add_link_to_title'):
            short_description += f' - {query_link}'
        log_message = report_consts.REPORT_CONTENT.format(name=self._report_data['name'],
                                                          query=query_name,
                                                          num_of_triggers=self._run_configuration.times_triggered,
                                                          trigger_message=self._get_trigger_description(),
                                                          num_of_current_devices=len(self._internal_axon_ids),
                                                          old_results_num_of_devices=old_results_num_of_devices,
                                                          query_link=query_link)
        impact = report_consts.SERVICE_NOW_SEVERITY.get(self._config['severity'],
                                                        report_consts.SERVICE_NOW_SEVERITY['error'])

        csv_string = None
        if self._config.get('send_csv_as_attachment'):
            try:
                query_name = self._run_configuration.view.name
                query = self._plugin_base.gui_dbs.entity_query_views_db_map[self._entity_type].find_one({
                    'name': query_name
                })
                if query:
                    parsed_query_filter = parse_filter(query['view']['query']['filter'])
                    field_list = query['view'].get('fields', [])
                    sort = gui_helpers.get_sort(query['view'])
                    field_filters = query['view'].get('colFilters', {})
                else:
                    parsed_query_filter = self._create_query(self._internal_axon_ids)
                    field_list = ['specific_data.data.name', 'specific_data.data.hostname',
                                  'specific_data.data.os.type', 'specific_data.data.last_used_users', 'labels']
                    sort = {}
                    field_filters = {}
                csv_string = gui_helpers.get_csv(parsed_query_filter,
                                                 sort,
                                                 {field: 1 for field in field_list},
                                                 self._entity_type,
                                                 field_filters=field_filters)
            except Exception:
                logger.exception(f'Failed getting csv')

        message = self._create_service_now_incident(short_description=short_description,
                                                    description=log_message,
                                                    impact=impact,
                                                    u_incident_type=self._config.get('u_incident_type'),
                                                    caller_id=self._config.get('caller_id'),
                                                    u_symptom=self._config.get('u_symptom'),
                                                    assignment_group=self._config.get('assignment_group'),
                                                    u_requested_for=self._config.get('u_requested_for'),
                                                    category=self._config.get('category'),
                                                    subcategory=self._config.get('subcategory'),
                                                    extra_fields=self._config.get('extra_fields'),
                                                    csv_string=csv_string
                                                    )
        return AlertActionResult(not message, message or 'Success')
