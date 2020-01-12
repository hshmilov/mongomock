import logging
import requests

from axonius.utils import gui_helpers, db_querying_helper
from axonius.utils.json import to_json, from_json

from axonius.utils.axonius_query_language import parse_filter
from axonius.types.enforcement_classes import AlertActionResult
from reports.action_types.action_type_alert import ActionTypeAlert


logger = logging.getLogger(f'axonius.{__name__}')

CUSTOM_FORMAT_STRING = '{$BODY}'
BODY_EXAMPLE = '{"entitiesList": {$BODY}}'
TIMEOUT_CONNECT = 10
TIMEOUT_READ = 1200


class SendWebhookAction(ActionTypeAlert):
    """
    Sends a HTTP/S POST request
    """

    @staticmethod
    def config_schema() -> dict:
        return {
            'items': [
                {
                    'name': 'webhook_url',
                    'title': 'Webhook URL',
                    'type': 'string'
                },
                {
                    'name': 'auth_username',
                    'title': 'Authorization header user name',
                    'type': 'string'
                },
                {
                    'name': 'auth_password',
                    'title': 'Authorization header password',
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
                    'name': 'http_proxy',
                    'title': 'HTTP proxy',
                    'type': 'string'
                },
                {
                    'name': 'extra_headers',
                    'title': 'Additional headers',
                    'type': 'string'
                },
                {
                    'name': 'custom_format',
                    'title': 'Custom format for body (use {$BODY} as keyword)',
                    'type': 'string'
                },
                {
                    'name': 'connect_timeout',
                    'title': 'Connection timeout (seconds)',
                    'type': 'string'
                },
                {
                    'name': 'read_timeout',
                    'title': 'Writing data to webhook timeout (seconds)',
                    'type': 'string'
                }
            ],
            'required': [
                'webhook_url',
                'verify_ssl',
                'custom_format',
                'connect_timeout',
                'read_timeout'
            ],
            'type': 'array'
        }

    @staticmethod
    def default_config() -> dict:
        return {
            'extra_headers': '{"Content-type": "application/json"}',
            'https_proxy': None,
            'http_proxy': None,
            'auth_username': None,
            'auth_password': None,
            'verify_ssl': False,
            'custom_format': '{"entities": {$BODY}}',
            'connect_timeout': TIMEOUT_CONNECT,
            'read_timeout': TIMEOUT_READ
        }

    @staticmethod
    def parse_extra_headers(headers: str) -> dict:
        try:
            parsed_headers = from_json(headers)
        except Exception as e:
            logger.exception(f'Failed to parse extra headers {headers}: {str(e)} ')
            raise
        else:
            return parsed_headers

    # pylint: disable=R0912,R0914
    def _run(self) -> AlertActionResult:
        query_name = self._run_configuration.view.name
        query = self._plugin_base.gui_dbs.entity_query_views_db_map[self._entity_type].find_one(
            {
                'name': query_name
            })
        # check for extra headers
        extra_headers_raw = self._config.get('extra_headers')
        if extra_headers_raw:
            try:
                extra_headers = self.parse_extra_headers(extra_headers_raw)
            except Exception as e:
                message = f'Invalid extra headers. Got: {extra_headers_raw}'
                logger.exception(message)
                return AlertActionResult(False, message)
        else:
            extra_headers = None
        username = self._config.get('auth_username', '')
        password = self._config.get('auth_password', '')
        auth_tuple = (username, password) if (username and password) else None
        try:
            timeout_read = int(self._config.get('read_timeout'))
        except (ValueError, TypeError):
            timeout_read = TIMEOUT_READ
        try:
            timeout_connect = int(self._config.get('connect_timeout'))
        except (ValueError, TypeError):
            timeout_connect = TIMEOUT_CONNECT
        timeout = (timeout_connect, timeout_read)
        if query:
            parsed_query_filter = parse_filter(query['view']['query']['filter'])
            field_list = query['view'].get('fields', [])
            sort = gui_helpers.get_sort(query['view'])
        else:
            parsed_query_filter = self._create_query(self._internal_axon_ids)
            field_list = ['specific_data.data.name', 'specific_data.data.hostname',
                          'specific_data.data.os.type', 'specific_data.data.last_used_users', 'labels']
            sort = {}
        proxies = dict()
        if self._config.get('http_proxy'):
            proxies['http'] = self._config.get('http_proxy')
        if self._config.get('https_proxy'):
            proxies['https'] = self._config.get('https_proxy')

        entities_raw = db_querying_helper.get_entities(None, None, parsed_query_filter,
                                                       sort,
                                                       {
                                                           field: 1
                                                           for field
                                                           in field_list
                                                       },
                                                       self._entity_type)
        entities = list(entities_raw)
        entities_json = to_json(entities or None)
        final_body = self._config['custom_format'].replace(CUSTOM_FORMAT_STRING, entities_json)
        response = requests.post(self._config['webhook_url'], data=final_body,
                                 verify=self._config['verify_ssl'],
                                 auth=auth_tuple,
                                 headers=extra_headers,
                                 proxies=proxies,
                                 timeout=timeout)
        logger.debug(f'Sent webhook request to {self._config["webhook_url"]}, '
                     f'got {str(response.status_code)}')
        result = response.status_code == 200
        try:
            result_status = response.json()
        except Exception:
            result_status = response.text
        if not result:
            logger.error(f'Failed to send devices to webhook. Got {str(response.status_code)}. '
                         f'The response was: {str(result_status)}')
        return AlertActionResult(result, result_status)
