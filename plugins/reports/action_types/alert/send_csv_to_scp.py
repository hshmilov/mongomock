import logging


from axonius.utils import gui_helpers
from axonius.utils.axonius_query_language import parse_filter
from axonius.types.enforcement_classes import AlertActionResult
from axonius.clients.linux_ssh.connection import LinuxSshConnection
from axonius.utils.memfiles import temp_memfd
from axonius.clients.linux_ssh.consts import UPLOAD_PATH_NAME, HOSTNAME, PORT, USERNAME, PASSWORD
from reports.action_types.action_type_alert import ActionTypeAlert


logger = logging.getLogger(f'axonius.{__name__}')


class SendCsvToScp(ActionTypeAlert):
    """
    Send CSV results to defined scp
    """

    @staticmethod
    def config_schema() -> dict:
        return {'items': [{'name': HOSTNAME, 'title': 'Hostname', 'type': 'string'},
                          {'name': USERNAME, 'title': 'User name', 'type': 'string'},
                          {'name': PASSWORD, 'title': 'Password', 'type': 'string', 'format': 'password'},
                          {'name': PORT, 'title': 'SSH port',
                           'type': 'integer',
                           'description': 'Protocol port'},
                          {'name': UPLOAD_PATH_NAME, 'title': 'CSV target path', 'type': 'string'}],
                'required': [USERNAME, PASSWORD, HOSTNAME, PORT, UPLOAD_PATH_NAME],
                'type': 'array'}

    @staticmethod
    def default_config() -> dict:
        return {HOSTNAME: None,
                USERNAME: None,
                PASSWORD: None,
                PORT: 22,
                UPLOAD_PATH_NAME: None
                }

    def _run(self) -> AlertActionResult:
        try:
            if not self._internal_axon_ids:
                return AlertActionResult(False, 'No Data')
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

            binary_arr = csv_string.getvalue().encode('utf-8')
            dst_path = self._config.get(UPLOAD_PATH_NAME)
            connection = LinuxSshConnection(hostname=self._config[HOSTNAME],
                                            port=self._config[PORT],
                                            username=self._config[USERNAME],
                                            password=self._config[PASSWORD])
            with connection:
                with temp_memfd('upload_file', binary_arr) as filepath:
                    # upload file to the server
                    connection.upload_file(filepath, str(dst_path))
            return AlertActionResult(True, 'Wrote to SCP')
        except Exception:
            logger.exception('Problem sending CSV to SCP')
            return AlertActionResult(False, 'Failed writing to SCP')
