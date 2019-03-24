import io
import urllib
import logging
from smb.SMBHandler import SMBHandler


from axonius.utils import gui_helpers
from axonius.utils.axonius_query_language import parse_filter
from axonius.types.enforcement_classes import AlertActionResult
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
                    'title': 'CSV Share Path',
                    'type': 'string'
                },
                {
                    'name': 'csv_share_username',
                    'title': 'CSV Share Username',
                    'type': 'string'
                },
                {
                    'name': 'csv_share_password',
                    'title': 'CSV Share Password',
                    'type': 'string',
                    'format': 'password'
                },
            ],
            'required': [
                'csv_share'
            ],
            'type': 'array'
        }

    @staticmethod
    def default_config() -> dict:
        return {
            'csv_share': None,
            'csv_share_username': None,
            'csv_share_password': None
        }

    def _run(self) -> AlertActionResult:
        try:
            query_name = self._run_configuration.view.name
            query = self._plugin_base.gui_dbs.entity_query_views_db_map[self._entity_type].find_one({
                'name': query_name
            })
            parsed_query_filter = parse_filter(query['view']['query']['filter'])
            field_list = query['view'].get('fields', [])
            csv_string = gui_helpers.get_csv(parsed_query_filter,
                                             gui_helpers.get_sort(query['view']),
                                             {field: 1 for field in field_list},
                                             self._entity_type)

            csv_data = io.BytesIO(csv_string.getvalue().encode('utf-8'))
            share_username = self._config.get('csv_share_username')
            share_password = self._config.get('csv_share_password')
            if not share_password or not share_username:
                share_password = None
                share_username = None
            share_path = self._config.get('csv_share')
            if not share_path.startswith('\\\\'):
                raise Exception(f'Bad Share Format {share_path}')
            share_path = share_path[2:]
            share_path = share_path.replace('\\', '/')
            if share_username and share_password:
                share_path = f'{urllib.parse.quote(share_username)}:' \
                             f'{urllib.parse.quote(share_password)}@{share_path}'
            share_path = 'smb://' + share_path
            opener = urllib.request.build_opener(SMBHandler)
            fh = opener.open(share_path, data=csv_data)
            fh.close()

            return AlertActionResult(True, 'Wrote to Share')
        except Exception:
            logger.exception('Problem sending CSV to share')
            return AlertActionResult(False, 'Failed writing to Share')
