import logging

from axonius.clients.rest.connection import RESTConnection

logger = logging.getLogger(f'axonius.{__name__}')


class ZendeskConnection(RESTConnection):
    def __init__(self, *args, **kwargs):
        super().__init__(*args, url_base_prefix='api/v2',
                         headers={'Content-Type': 'application/json',
                                  'Accept': 'application/json'}, **kwargs)

    def _connect(self):
        pass

    def get_device_list(self):
        pass

    def create_ticket(self, ticket_subject, priority, ticket_body):
        body_params = {'ticket': {'subject': ticket_subject,
                                  'comment': {'body': ticket_body}}
                       }
        if priority:
            body_params['ticket']['priority'] = priority
        try:
            self._post('tickets.json',
                       do_basic_auth=True,
                       body_params=body_params)
            return ''
        except Exception as e:
            logger.exception(f'Problem with sending ticket with params: {ticket_body} , {ticket_subject}, {priority}')
            return str(e)
