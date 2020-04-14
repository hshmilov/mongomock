import logging

from axonius.clients.rest.connection import RESTConnection
from axonius.clients.opsgenie.consts import OPSGENIE_PRIORITIES

logger = logging.getLogger(f'axonius.{__name__}')


class OpsgenieConnection(RESTConnection):
    def __init__(self, *args, **kwargs):
        super().__init__(*args, url_base_prefix='v2',
                         headers={'Content-Type': 'application/json',
                                  'Accept': 'application/json'}, **kwargs)
        self._permanent_headers['Authorization'] = f'GenieKey {self._apikey}'

    def _connect(self):
        pass

    def get_device_list(self):
        pass

    def create_alert(self, message, priority=None, tags=None, alias=None,
                     user=None, note=None, source=None, description=None):
        if not priority or priority not in OPSGENIE_PRIORITIES:
            priority = 'P3'
        body_params = {'message': message,
                       'priority': priority}
        if tags and isinstance(tags, str):
            body_params['tags'] = tags.split(',')
        if alias:
            body_params['alias'] = alias
        if user:
            body_params['user'] = user
        if note:
            body_params['note'] = note
        if source:
            body_params['source'] = source
        if description:
            body_params['description'] = description
        logger.info(f'Sending opgenie with params: {body_params}')
        try:
            self._post('alerts',
                       body_params=body_params)
            return ''
        except Exception as e:
            logger.exception(f'Problem with creating alert with params: {body_params}')
            return str(e)
