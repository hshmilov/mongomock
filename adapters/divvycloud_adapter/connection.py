import logging

from axonius.clients.rest.connection import RESTConnection
from axonius.clients.rest.exception import RESTException
from divvycloud_adapter import consts

logger = logging.getLogger(f'axonius.{__name__}')


class DivvyCloudConnection(RESTConnection):

    def _connect(self):
        if self._username is not None and self._password is not None:
            response = self._post('v2/public/user/login',
                                  body_params={
                                      'username': self._username,
                                      'password': self._password
                                  }
                                  )
            if 'session_id' not in response:
                raise RESTException(f'Did not get session id on response: {str(response)}')
            self._session_headers['X-Auth-Token'] = response['session_id']
        else:
            raise RESTException('No username or password')

    def get_device_list(self):
        def get_instances(offset):
            # There are many types of resources (networks, storage, and more).
            # We query only instances.

            instances_answer = self._post('v2/public/resource/query',
                                          body_params={
                                              'selected_resource_type': 'instance',
                                              'scopes': [],
                                              'filters': [],
                                              'offset': offset,
                                              'limit': consts.INSTANCES_QUERY_RATE
                                          })

            instances_count = int((instances_answer.get('counts') or {}).get('instance') or 0)

            instances = []
            for r in (instances_answer.get('resources') or []):
                if r.get('instance') is not None:
                    instances.append(r.get('instance'))

            return instances_count, instances

        instances_count, first_instances = get_instances(0)
        logger.info(f'We have {instances_count} instances. Querying them by batches of {consts.INSTANCES_QUERY_RATE}')

        # Return the first batch of instances
        number_of_instances_queried = consts.INSTANCES_QUERY_RATE
        yield from first_instances

        while number_of_instances_queried < instances_count:
            try:
                # We update the instance number since it varies all the time (cloud instances go up and down)
                instances_count, next_instances = get_instances(number_of_instances_queried)
                number_of_instances_queried += consts.INSTANCES_QUERY_RATE
                yield from next_instances
            except Exception:
                logger.exception(f'Problem querying instances from offset {number_of_instances_queried}')
