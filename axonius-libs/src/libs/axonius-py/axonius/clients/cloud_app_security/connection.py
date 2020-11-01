import datetime
import logging

from axonius.clients.rest.connection import RESTConnection
from axonius.clients.rest.exception import RESTException
from axonius.clients.cloud_app_security.consts import MAX_NUMBER_OF_USERS, URL_BASE_PREFIX, \
    API_SERVICE_PARAMETERS, API_EVENT_PARAMETERS, API_URL_SECURITY_LOG_SUFFIX, ISO_8601_FORMAT, \
    MAX_SCRAPE_DATE_HOURS_AGO, LOGS_PER_PAGE, MAX_LOGS_PER_USER

logger = logging.getLogger(f'axonius.{__name__}')


# pylint: disable=logging-format-interpolation


class CloudAppSecurityConnection(RESTConnection):
    """ rest client for CloudAppSecurity adapter """

    def __init__(self, *args, token: str, scrape_date_hours_ago: int, **kwargs):
        super().__init__(*args, url_base_prefix=URL_BASE_PREFIX,
                         headers={'Content-Type': 'application/json',
                                  'Accept': 'application/json'},
                         **kwargs)
        self._token = token
        self._scrape_date_hours_ago = scrape_date_hours_ago

    def _connect(self):
        if not 0 < self._scrape_date_hours_ago <= MAX_SCRAPE_DATE_HOURS_AGO:
            raise ValueError(f'Error: Invalid fetch logs hour, 0 < X <= {MAX_SCRAPE_DATE_HOURS_AGO}')

        if not self._token:
            raise RESTException('No API Token')

        try:
            self._session_headers['Authorization'] = f'Bearer {self._token}'

            url_params = {
                'service': API_SERVICE_PARAMETERS[0],
                'event': API_EVENT_PARAMETERS[0],
                'limit': 1
            }
            self._get(API_URL_SECURITY_LOG_SUFFIX, url_params=url_params)

        except Exception as e:
            raise ValueError(f'Error: Invalid response from server, please check domain or credentials. {str(e)}')

    def get_device_list(self):
        pass

    @staticmethod
    def _get_start_and_end_iso_date(hours: int):
        # ISO-8601 timestamp is required by the api
        start_time = (datetime.datetime.now() - datetime.timedelta(hours=hours)).strftime(
            ISO_8601_FORMAT)
        end_time = datetime.datetime.now().strftime(ISO_8601_FORMAT)

        return start_time, end_time

    @staticmethod
    def _handle_user(users_by_id: dict, user_id: str, raw_data: dict):
        """
        Create sender/recipient information and increase total fetch counter
        If sender/recipient already exists append relevant information (total fetch counter remains the same)
        After reaching max number of logs for each user, discarding raw data and continue counting the user appearance.
        :return True if created a new user, else False
        """
        event = raw_data.get('event')
        service = raw_data.get('service')

        if users_by_id.get(user_id):
            users_by_id[user_id]['total_count'] += 1

            # May reach to event_service which does not exist while the user does exist
            if users_by_id.get('counters').get(event, service):
                users_by_id[user_id]['counters'][(event, service)] += 1
            else:
                # Creating the new event_service count for the existing user
                users_by_id[user_id]['counters'][(event, service)] = 1

            if users_by_id[user_id]['fetch_count'] < MAX_LOGS_PER_USER:
                users_by_id[user_id]['fetch_count'] += 1
                users_by_id[user_id]['raw'].append(raw_data)

        else:
            users_by_id[user_id] = {
                'total_count': 1,
                'fetch_count': 1,
                'raw': [raw_data],
                'counters': {
                    (event, service): 1
                }
            }
            return True

        return False

    # pylint: disable=too-many-nested-blocks, too-many-branches
    def _paginated_async_get_users(self, async_chunks: int):
        try:
            total_fetched_users = 0
            next_security_logs_requests = []
            senders_by_id = {}
            recipient_by_id = {}

            for service in API_SERVICE_PARAMETERS:
                for event in API_EVENT_PARAMETERS:
                    start_time, end_time = self._get_start_and_end_iso_date(hours=self._scrape_date_hours_ago)

                    next_security_logs_requests.append({
                        'name': API_URL_SECURITY_LOG_SUFFIX,
                        'url_params': {
                            'service': service,
                            'event': event,
                            'limit': LOGS_PER_PAGE,
                            'start': start_time,
                            'end': end_time}
                    })

            while next_security_logs_requests and total_fetched_users < MAX_NUMBER_OF_USERS:
                current_security_logs_requests = next_security_logs_requests
                next_security_logs_requests = []

                for response in self._async_get(current_security_logs_requests, retry_on_error=True,
                                                chunks=async_chunks):
                    if not self._is_async_response_good(response):
                        logger.error(f'Async response returned bad, its {response}')
                        continue

                    if not (isinstance(response, dict) and isinstance(response.get('security_events'), list)):
                        logger.warning(f'Invalid response returned: {response}')
                        continue

                    next_security_logs_requests.append({
                        'name': response.get('next_link'),
                        'force_full_url': True
                    })

                    for security_log in response.get('security_events'):
                        if not (isinstance(security_log, dict) and isinstance(security_log.get('message'), dict)):
                            logger.warning(f'Invalid security log received {security_log}')
                            continue
                        security_log_raw = security_log.get('message')

                        if isinstance(security_log_raw.get('mail_message_sender'), str):
                            sender = security_log_raw.get('mail_message_sender')
                            if self._handle_user(senders_by_id,
                                                 sender,
                                                 security_log_raw):
                                total_fetched_users += 1

                        if isinstance(security_log_raw.get('mail_message_recipient'), list):
                            recipients = security_log_raw.get('mail_message_recipient')
                            for recipient in recipients:
                                if self._handle_user(recipient_by_id,
                                                     recipient,
                                                     security_log_raw):
                                    total_fetched_users += 1

            for user_id in set(senders_by_id.keys()):
                result = {
                    'id': user_id,
                    'sender': senders_by_id.pop(user_id, {}),
                    'recipient': recipient_by_id.pop(user_id, {})
                }
                yield result

            for user_id in set(recipient_by_id.keys()):
                result = {
                    'id': user_id,
                    'sender': senders_by_id.pop(user_id, {}),
                    'recipient': recipient_by_id.pop(user_id, {})
                }
                yield result

            logger.info(f'Got total of {total_fetched_users} users')
        except Exception as err:
            logger.exception(f'Invalid request made while paginating users {str(err)}')
            raise

    def get_user_list(self, async_chunks: int):
        try:
            yield from self._paginated_async_get_users(async_chunks)
        except RESTException as err:
            logger.exception(str(err))
            raise
