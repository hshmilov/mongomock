import logging

from axonius.types.enforcement_classes import EntitiesResult, EntityResult
from axonius.clients.service_now.connection import ServiceNowConnection
from axonius.consts import report_consts
from reports.action_types.action_type_base import ActionTypeBase, add_node_selection, add_node_default

logger = logging.getLogger(f'axonius.{__name__}')

ADAPTER_NAME = 'service_now_adapter'

# pylint: disable=W0212


class ServiceNowIncidentPerEntity(ActionTypeBase):
    """
    Creates an incident per every service_now entity
    """

    @staticmethod
    def config_schema() -> dict:
        schema = {
            'items': [
                {
                    'name': 'use_adapter',
                    'title': 'Use ServiceNow Adapter',
                    'type': 'bool'
                },
                {
                    'name': 'domain',
                    'title': 'ServiceNow Domain',
                    'type': 'string'
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
                    'name': 'verify_ssl',
                    'title': 'Verify SSL',
                    'type': 'bool'
                },
                {
                    'name': 'https_proxy',
                    'title': 'HTTPS Proxy',
                    'type': 'string'
                },
                {
                    'name': 'incident_title',
                    'title': 'Incident Short Description',
                    'type': 'string'
                },
                {
                    'name': 'severity',
                    'title': 'Message Severity',
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
                    'name': 'cmdb_ci',
                    'title': 'Configuration Item',
                    'type': 'string'
                },
                {
                    'name': 'u_symptom',
                    'title': 'Symptom',
                    'type': 'string'
                },
                {
                    'name': 'assignment_group',
                    'title': 'Assignment Group',
                    'type': 'string'
                }
            ],
            'required': [
                'use_adapter'
                'severity',
                'incident_title'
            ],
            'type': 'array'
        }
        return add_node_selection(schema, ADAPTER_NAME)

    @staticmethod
    def default_config() -> dict:
        return add_node_default({
            'use_adapter': False,
            'domain': None,
            'username': None,
            'password': None,
            'https_proxy': None,
            'verify_ssl': True,
            'u_requested_for': None,
            'caller_id': None,
            'severity': 'info',
            'incident_title': None,
            'cmdb_ci': None,
            'u_symptom': None,
            'assignment_group': None
        }, ADAPTER_NAME)

    def _create_service_now_incident(self, short_description, description, impact, u_incident_type,
                                     caller_id, cmdb_ci, u_symptom, assignment_group, u_requested_for):
        adapter_unique_name = self._plugin_base._get_adapter_unique_name(ADAPTER_NAME, self.action_node_id)
        service_now_dict = {'short_description': short_description,
                            'description': description,
                            'impact': impact,
                            'u_incident_type': u_incident_type,
                            'caller_id': caller_id,
                            'cmdb_ci': cmdb_ci,
                            'u_symptom': u_symptom,
                            'assignment_group': assignment_group,
                            'u_requested_for': u_requested_for}
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

    # pylint: disable=R0912,R0914,R0915,R1702
    def _run(self) -> EntitiesResult:

        service_now_projection = {
            'internal_axon_id': 1,
            'adapters.plugin_name': 1,
            'adapters.data.hostname': 1,
            'adapters.data.id': 1,
            'adapters.data.name': 1,
            'adapters.data.os.type': 1,
            'adapters.data.device_serial': 1,
            'adapters.data.device_manufacturer': 1,
            'adapters.data.network_interfaces.mac': 1,
            'adapters.data.description': 1,
            'adapters.data.cpus.cores': 1,
            'adapters.data.cpus.name': 1,
            'adapters.data.cpus.ghz': 1,
            'adapters.data.username': 1,
            'adapters.data.display_name': 1,
            'adapters.data.mail': 1,
            'adapters.data.last_used_users': 1,
            'adapters.data.domain': 1,
            'adapters.data.power_state': 1
        }
        current_result = self._get_entities_from_view(service_now_projection)
        results = []

        for entry in current_result:
            try:
                impact = report_consts.SERVICE_NOW_SEVERITY.get(self._config['severity'],
                                                                report_consts.SERVICE_NOW_SEVERITY['error'])
                message = self._create_service_now_incident(short_description=self._config['incident_title'],
                                                            description=str(entry),
                                                            impact=impact,
                                                            u_incident_type=self._config.get('u_incident_type'),
                                                            caller_id=self._config.get('caller_id'),
                                                            cmdb_ci=self._config.get('cmdb_ci'),
                                                            u_symptom=self._config.get('u_symptom'),
                                                            assignment_group=self._config.get('assignment_group'),
                                                            u_requested_for=self._config.get('u_requested_for'))
                results.append(EntityResult(entry['internal_axon_id'], not message, message or 'Success'))
            except Exception:
                logger.exception(f'Problem with entry {entry}')
                results.append(EntityResult(entry['internal_axon_id'], False, 'Unexpected Error'))
        return results
