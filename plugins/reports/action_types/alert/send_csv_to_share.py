import io
import urllib
import logging
# pylint: disable=import-error


from axonius.utils import gui_helpers
from axonius.utils.axonius_query_language import parse_filter
from axonius.types.enforcement_classes import AlertActionResult
from axonius.utils.remote_file_smb_handler import get_smb_handler
from reports.action_types.action_type_alert import ActionTypeAlert


logger = logging.getLogger(f'axonius.{__name__}')


class SendCsvToShare(ActionTypeAlert):
    """
    Send CSV results to defined share
    """
    @staticmethod
    def config_schema() -> dict:
        return {
            'items': [
                {
                    'name': 'csv_share',
                    'title': 'CSV share path',
                    'type': 'string'
                },
                {
                    'name': 'csv_share_username',
                    'title': 'CSV share user name',
                    'type': 'string'
                },
                {
                    'name': 'csv_share_password',
                    'title': 'CSV share password',
                    'type': 'string',
                    'format': 'password'
                },
                {
                    'name': 'use_nbns',
                    'type': 'bool',
                    'title': 'Use NBNS'
                }
            ],
            'required': [
                'csv_share',
                'use_nbns'
            ],
            'type': 'array'
        }

    @staticmethod
    def default_config() -> dict:
        return {
            'csv_share': None,
            'csv_share_username': None,
            'csv_share_password': None,
            'use_nbns': True
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

            csv_data = io.BytesIO(csv_string.getvalue().encode('utf-8'))
            share_username = self._config.get('csv_share_username')
            share_password = self._config.get('csv_share_password')
            share_path = self._config.get('csv_share')[2:]
            share_path = share_path.replace('\\', '/')
            if share_username is not None:
                share_username = share_username.replace('\\', ';')
            if share_username and share_password:
                share_path = f'{urllib.parse.quote(share_username)}:' \
                             f'{urllib.parse.quote(share_password)}@{share_path}'
            elif share_username:
                # support guest or password-less smb auth
                share_path = f'{urllib.parse.quote(share_username)}@{share_path}'
            final_path = f'smb://{share_path}'
            opener = urllib.request.build_opener(get_smb_handler(use_nbns=self._config.get('use_nbns')))
            fh = opener.open(final_path, data=csv_data)
            fh.close()

            return AlertActionResult(True, 'Wrote to Share')
        except Exception:
            logger.exception('Problem sending CSV to share')
            return AlertActionResult(False, 'Failed writing to Share')
