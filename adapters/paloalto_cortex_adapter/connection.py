# pylint: disable=arguments-differ
import logging
import time

from datetime import datetime, timedelta

# pylint: disable=import-error
from pancloud import LoggingService, Credentials
from axonius.clients.rest.connection import RESTConnection
from axonius.clients.rest.exception import RESTException
from paloalto_cortex_adapter import consts

logger = logging.getLogger(f'axonius.{__name__}')

# pylint: disable=logging-format-interpolation


# pylint: disable=too-many-instance-attributes, too-many-nested-blocks
class PaloAltoCortexConnection(RESTConnection):
    """ rest client for Paloalto Cortex adapter """

    def __init__(self, *args, **kwargs):
        super().__init__(*args,
                         domain=consts.CLOUD_URL,
                         **kwargs)
        self._instance_id = None
        self.__logging_service = None
        self._permanent_headers = {'x-api-key': self._apikey}
        self.__last_token_fetch = None

    def refresh_access_token(self, force=False):
        if not self.__last_token_fetch or \
                (self.__last_token_fetch + timedelta(minutes=consts.REFRESH_ACCESS_TOKEN_MINUTES) < datetime.now()) \
                or force:
            response = self._get(consts.ACCESS_TOKEN_ENDPOINT)

            if 'access_token' not in response:
                logger.error(f'Authentication error: {response}')
                if 'unauthenticated' in str(response).lower():
                    raise ValueError(f'Incorrect API Key')
                raise ValueError(response)

            if 'region' not in response:
                logger.error(f'Authentication error: {response}')
                raise ValueError(f'Error contacting authorization server')

            if 'instance_id' not in response:
                raise ValueError(f'Please re-authorize the application in the Palo Alto Networks Cortex Hub')

            region = response['region']
            self._instance_id = response['instance_id']

            logger.info(f'Got access token from {consts.CLOUD_URL}, continuing to contacting palo alto')

            # Here should be a process of getting url + credentials
            self.__logging_service = LoggingService(
                url=f'https://api.{region}.cdl.paloaltonetworks.com',
                credentials=Credentials(access_token=response['access_token']),
                proxies=self._proxies
            )

            self.__last_token_fetch = datetime.now()

    def _connect(self):
        if not self._apikey:
            raise RESTException('No API Key')

        self.refresh_access_token(force=True)

        # Validate access token
        full_query = {
            'query': f'SELECT * FROM `{self._instance_id}.firewall.globalprotect` limit 1',
            'startTime': int((datetime.now() - timedelta(weeks=1)).timestamp()),
            'endTime': int(datetime.now().timestamp()),
            'maxWaitTime': 0  # no logs in initial response
        }
        query = self.__logging_service.query(full_query)
        if 'queryId' not in query.json():
            raise ValueError(f'Error in response: {query.json()}')
        logger.info(f'Successfully connected.')

    def close(self):
        self.__logging_service = None
        super().close()

    def delete_query(self, query_id, **kwargs):
        response = self.__logging_service.delete(query_id, **kwargs)
        try:
            dr_json = response.json()
        except ValueError as e:
            raise ValueError(f'Invalid JSON: {e}')

        if not 200 <= response.status_code < 300:
            if 'errorCode' in dr_json and 'errorMessage' in dr_json:
                raise ValueError(f'{dr_json["errorCode"]} - {dr_json["errorMessage"]}')
            raise ValueError(f'{str(response.status_code)}:{response.reason}')

        if response.status_code == 200:
            return
        raise ValueError(f'delete: status_code: {response.status_code}')

    # pylint: disable=too-many-branches
    def xpoll(self, query_id=None, sequence_no=None, params=None,
              delete_query=True, **kwargs):
        """
            yields records for query.
        """
        r = self.__logging_service.poll(query_id, sequence_no, params, **kwargs)
        try:
            r_json = r.json()
        except ValueError as e:
            raise ValueError(f'Invalid JSON: {e}. content is {r.content}')

        if not 200 <= r.status_code < 300:
            if 'errorCode' in r_json and 'errorMessage' in r_json:
                raise ValueError(f'{str(r.status_code)}:{r_json}')

        if r_json.get('queryStatus') in ['FINISHED', 'JOB_FINISHED']:
            try:
                yield r_json['result']
            except KeyError:
                raise ValueError(f'bad response, no result: {r_json}')

            if r_json['queryStatus'] == 'JOB_FINISHED':
                if delete_query:
                    try:
                        self.delete_query(query_id, **kwargs)
                    except Exception:
                        logger.exception(f'could not delete query id, bypassing')
                return

            if sequence_no is not None:
                sequence_no += 1
            else:
                sequence_no = 1
            logger.info(f'Sequence no: {sequence_no}')

        elif r_json.get('queryStatus') == 'JOB_FAILED':
            raise ValueError(f'Job failed: {r_json}')

        elif r_json.get('queryStatus') == 'RUNNING' or r.status_code == consts.STATUS_CODE_RATE_LIMIT_REACHED:
            possible_window_size = str(r_json.get('errorDetails')).lower()
            if 'window' in possible_window_size and '60' in possible_window_size:
                logger.info(f'We have reached a rate limit of 60 seconds. sleeping 60 seconds')
                # We've reached a rate limit of 60 seconds
                time.sleep(60)
            elif 'window' in possible_window_size and '3600' in possible_window_size:
                logger.info(f'We have reached a rate limit of 3600 seconds. sleeping 3600 seconds')
                # We've reached a rate limit of 3600 seconds
                time.sleep(3600)

            elif params is not None and 'maxWaitTime' in params:
                pass
            else:
                time.sleep(1)
        else:
            raise ValueError('Bad queryStatus: ' + r_json['queryStatus'])

        # recursion
        yield from self.xpoll(query_id, sequence_no, params, delete_query, **kwargs)

    # pylint: disable=arguments-differ
    def get_device_list(self, weeks_ago_to_fetch):
        for device in self.get_global_protect_devices(weeks_ago_to_fetch):
            yield device

    def get_global_protect_devices(self, weeks_ago_to_fetch):
        table = f'{self._instance_id}.firewall.globalprotect'
        query = f'SELECT * FROM `{table}` order by time_generated DESC limit 10000000'
        full_query = {
            'query': query,
            'startTime': int((datetime.now() - timedelta(weeks=weeks_ago_to_fetch)).timestamp()),
            'endTime': int(datetime.now().timestamp()),
            'maxWaitTime': 0  # no logs in initial response
        }

        query = self.__logging_service.query(full_query)
        try:
            query_id = query.json()['queryId']
        except Exception:
            raise ValueError(query.content)

        agent_ids = set()
        try:
            for record in self.xpoll(
                    query_id=query_id,
                    sequence_no=0,
                    params={'maxWaitTime': consts.MAX_PANCLOUD_POLL_WAIT_TIME}
            ):
                try:
                    for log in record['esResult']['hits']['hits']:
                        try:
                            data = log['_source']
                            if 'endpoint_serial_number' in data and data.get('endpoint_serial_number') not in agent_ids:
                                yield data
                                agent_ids.add(data['endpoint_serial_number'])
                        except Exception:
                            logger.exception(f'Failed fetching device from log {log}')
                except Exception:
                    logger.exception(f'Failed getting results for record {record}')
                    break
                self.refresh_access_token()
        except Exception:
            logger.exception(f'Exception in xpoll process')
