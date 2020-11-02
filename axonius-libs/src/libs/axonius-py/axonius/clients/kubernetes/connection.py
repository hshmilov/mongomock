import logging

from kubernetes import client

from axonius.clients.kubernetes.consts import MAX_ALLOWED_FAILURES, PAGE_SIZE, MAX_NUMBER_OF_DEVICES
from axonius.clients.rest.exception import RESTException
from axonius.utils.parsing import int_or_none, parse_bool_from_raw
from kubernetes_adapter.structures import get_value_or_default

logger = logging.getLogger(f'axonius.{__name__}')


# pylint: disable=E1101,E0203
class KubernetesConnection:
    """ SDK client for Kubernetes adapter """

    def __init__(self, domain, token, port, verify_ssl, *args, **kwargs):
        self._client = None
        self._domain = domain
        self._token = token
        self._port = int_or_none(port)
        self._verify_ssl = parse_bool_from_raw(verify_ssl)

    def __enter__(self):
        self._connect()
        return self

    def __exit__(self, exc_type, exc_value, traceback):
        self._client = None

    def _connect(self):
        if not (self._domain and self._port):
            raise RESTException('Either domain or port not provided!')

        if not self._token:
            raise RESTException('API token not provided!')

        self._domain = self._domain.rstrip('/')  # Remove trailing slash.

        configuration = client.Configuration()
        configuration.host = f'{self._domain}:{self._port}'
        configuration.verify_ssl = self._verify_ssl
        configuration.api_key = {'authorization': f'Bearer {self._token}'}

        try:
            api_client = client.ApiClient(configuration)
            self._client = client.CoreV1Api(api_client)
            pods = self.get_all_pods(limit=1)

            if len(pods) == 0:
                raise Exception('0 pods returned from the server while connecting!')

            logger.info('Connected successfully!')
        except Exception as e:
            raise ValueError(f'Invalid response from server, please check domain or token,{str(e)}')

    def _paginated_device_get(self):
        try:
            total_fetched_pods = 0
            continuation_token = None
            fail_count = 0

            while total_fetched_pods < MAX_NUMBER_OF_DEVICES:
                try:
                    pods, continuation_token = self.get_all_pods(limit=PAGE_SIZE, continuation_token=continuation_token)
                except Exception as err:
                    fail_count += 1
                    logger.debug(f'Error occurred while fetching pods: {str(err)} , Failures Count: {fail_count}')
                    if fail_count <= MAX_ALLOWED_FAILURES:  # Avoid possible infinite loop
                        continue
                    break

                total_fetched_pods += len(pods)
                yield from pods
                if not continuation_token:
                    logger.debug('Finished paginating pods.')
                    break

            logger.info(f'Got total of {total_fetched_pods} pods')
        except Exception:
            logger.exception(f'Invalid request made while paginating pods')
            raise

    def get_all_pods(self, limit=None, continuation_token=None):
        """
        :param limit: limit items per call
        :param continuation_token: where to continue from
        :return: tuple: pods_list, continuation_token
        """

        if not self._client:
            raise Exception('Connection client was not initialized!')

        params = {'watch': False}
        if limit:
            params['limit'] = limit
        if continuation_token:
            params['_continue'] = continuation_token

        response = self._client.list_pod_for_all_namespaces(**params).to_dict()
        if not (response and isinstance(response, dict)):
            raise Exception('Could not fetch pods from the server!')

        items = get_value_or_default('items', response.get('items'), list)
        metadata = get_value_or_default('metadata', response.get('metadata'), dict)
        _continue = get_value_or_default('_continue', metadata.get('_continue'), str)

        if not items:
            raise Exception(f'Got empty pods: {str(items)}')
        if not metadata:
            raise Exception('Could not fetch metadata which is required for getting a continuation token')

        return items, _continue

    def get_device_list(self):
        try:
            yield from self._paginated_device_get()
        except RESTException as err:
            logger.exception(str(err))
            raise
