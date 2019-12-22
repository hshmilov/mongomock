import logging
import requests

from axonius.utils import gui_helpers, db_querying_helper
from axonius.utils.json import to_json, from_json

from axonius.utils.axonius_query_language import parse_filter
from axonius.types.enforcement_classes import AlertActionResult
from reports.action_types.action_type_alert import ActionTypeAlert


logger = logging.getLogger(f'axonius.{__name__}')


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
                    'title': 'Authorization Header Username',
                    'type': 'string'
                },
                {
                    'name': 'auth_password',
                    'title': 'Authorization Header Password',
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
                    'name': 'http_proxy',
                    'title': 'HTTP Proxy',
                    'type': 'string'
                },
                {
                    'name': 'extra_headers',
                    'title': 'Additional Headers',
                    'type': 'string'
                }
            ],
            'required': [
                'webhook_url',
                'verify_ssl'
            ],
            'type': 'array'
        }

    @staticmethod
    def default_config() -> dict:
        return {
            'extra_headers': '',
            'https_proxy': None,
            'http_proxy': None,
            'auth_username': None,
            'auth_password': None,
            'verify_ssl': False
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
        if not query:
            logger.error(f'Could not fetch query: {str(query_name)}')
            return AlertActionResult(False, 'Failed to fetch query')
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

        parsed_query_filter = parse_filter(query['view']['query']['filter'])
        field_list = query['view'].get('fields', [])
        sort = gui_helpers.get_sort(query['view'])
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
        entities = list()
        for entity_raw in entities_raw:
            entities.append(to_json(entity_raw))
        entities_json = to_json(entities or None)
        response = requests.post(self._config['webhook_url'], json=entities_json,
                                 verify=self._config['verify_ssl'],
                                 auth=auth_tuple,
                                 headers=extra_headers,
                                 proxies=proxies)
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
