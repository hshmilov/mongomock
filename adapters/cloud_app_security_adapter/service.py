import logging

from axonius.adapter_base import AdapterBase, AdapterProperty
from axonius.adapter_exceptions import ClientConnectionException
from axonius.clients.rest.connection import RESTConnection, RESTException
from axonius.clients.cloud_app_security.connection import CloudAppSecurityConnection
from axonius.clients.cloud_app_security.consts import SCRAPE_DATE_HOURS_AGO, DEFAULT_ASYNC_CHUNKS_SIZE, \
    MAX_SCRAPE_DATE_HOURS_AGO
from axonius.mixins.configurable import Configurable
from axonius.utils.datetime import parse_date
from axonius.utils.files import get_local_config_file
from axonius.utils.parsing import int_or_none
from cloud_app_security_adapter.client_id import get_client_id
from cloud_app_security_adapter.structures import CloudAppSecurityUserInstance, SecurityLog, EventServiceCount

logger = logging.getLogger(f'axonius.{__name__}')


# pylint: disable=logging-format-interpolation


class CloudAppSecurityAdapter(AdapterBase, Configurable):
    # pylint: disable=too-many-instance-attributes
    class MyUserAdapter(CloudAppSecurityUserInstance):
        pass

    def __init__(self, *args, **kwargs):
        super().__init__(config_file_path=get_local_config_file(__file__), *args, **kwargs)

    @staticmethod
    def _get_client_id(client_config):
        return get_client_id(client_config)

    @staticmethod
    def _test_reachability(client_config):
        return RESTConnection.test_reachability(client_config.get('domain'),
                                                https_proxy=client_config.get('https_proxy'))

    @staticmethod
    def get_connection(client_config):
        connection = CloudAppSecurityConnection(domain=client_config.get('domain'),
                                                verify_ssl=client_config.get('verify_ssl'),
                                                https_proxy=client_config.get('https_proxy'),
                                                proxy_username=client_config.get('proxy_username'),
                                                proxy_password=client_config.get('proxy_password'),
                                                token=client_config.get('token'),
                                                scrape_date_hours_ago=client_config.get('scrape_date_hours_ago'))
        with connection:
            pass  # check that the connection credentials are valid
        return connection

    def _connect_client(self, client_config):
        try:
            return self.get_connection(client_config)
        except RESTException as e:
            message = 'Error connecting to client with domain {0}, reason: {1}'.format(
                client_config.get('domain'), str(e))
            logger.exception(message)
            raise ClientConnectionException(message)

    # pylint: disable=arguments-differ
    def _query_users_by_client(self, client_name, client_data):
        """
        Get all users from a specific domain

        :param str client_name: The name of the client
        :param obj client_data: The data that represent a connection

        :return: A json with all the attributes returned from the Server
        """
        with client_data:
            yield from client_data.get_user_list(
                async_chunks=self.__async_chunks
            )

    @staticmethod
    def _clients_schema():
        """
        The schema CloudAppSecurityAdapter expects from configs

        :return: JSON scheme
        """
        return {
            'items': [
                {
                    'name': 'domain',
                    'title': 'Host Name or IP Address',
                    'type': 'string'
                },
                {
                    'name': 'token',
                    'title': 'API Token',
                    'type': 'string',
                    'format': 'password'
                },
                {
                    'name': 'scrape_date_hours_ago',
                    'type': 'number',
                    'title': 'Fetch logs from the last X hours (max. 72)',
                    'description': 'Logs data is limited to the last 72 hours',
                    'default': SCRAPE_DATE_HOURS_AGO,
                    'max': MAX_SCRAPE_DATE_HOURS_AGO,
                    'min': 0
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
                    'name': 'proxy_username',
                    'title': 'HTTPS Proxy User Name',
                    'type': 'string'
                },
                {
                    'name': 'proxy_password',
                    'title': 'HTTPS Proxy Password',
                    'type': 'string',
                    'format': 'password'
                }
            ],
            'required': [
                'domain',
                'token',
                'scrape_date_hours_ago',
                'verify_ssl'
            ],
            'type': 'array'
        }

    @staticmethod
    def _fill_cloud_app_security_user_fields(user_raw: dict, user: MyUserAdapter, is_sender: bool = True):
        try:
            if is_sender:
                user.sender_event_count = int_or_none(user_raw.get('total_count'))
            else:
                user.recipient_event_count = int_or_none(user_raw.get('total_count'))

            if isinstance(user_raw.get('counters'), dict):
                event_service_counts = []
                for (event, service), total in user_raw.get('counters').items():
                    event_service_count = EventServiceCount()
                    event_service_count.event = event
                    event_service_count.service = service
                    event_service_count.total = int_or_none(total)

                    event_service_counts.append(event_service_count)
                user.event_service_counts = event_service_counts

            if isinstance(user_raw.get('raw'), list):
                security_logs = []
                for security_log_raw in user_raw.get('raw'):
                    security_log = SecurityLog()
                    security_log.scan_type = security_log_raw.get('scan_type')
                    security_log.affected_user = security_log_raw.get('affected_user')
                    security_log.location = security_log_raw.get('location')
                    security_log.detection_time = parse_date(security_log_raw.get('detection_time'))
                    security_log.triggered_policy_name = security_log_raw.get('triggered_policy_name')
                    security_log.triggered_security_filter = security_log_raw.get('triggered_security_filter')
                    security_log.action = security_log_raw.get('action')
                    security_log.action_result = security_log_raw.get('action_result')
                    security_log.mail_message_id = security_log_raw.get('mail_message_id')
                    mail_message_sender = security_log_raw.get('mail_message_sender') or []
                    if isinstance(mail_message_sender, str):
                        mail_message_sender = [mail_message_sender]
                    security_log.mail_message_sender = mail_message_sender
                    security_log.mail_message_recipient = security_log_raw.get('mail_message_recipient')
                    security_log.mail_message_submit_time = parse_date(security_log_raw.get('mail_message_submit_time'))
                    security_log.mail_message_delivery_time = parse_date(
                        security_log_raw.get('mail_message_delivery_time'))
                    security_log.mail_message_subject = security_log_raw.get('mail_message_subject')
                    security_log.mail_message_file_name = security_log_raw.get('mail_message_file_name')
                    security_log.security_risk_name = security_log_raw.get('security_risk_name')
                    security_log.detected_by = security_log_raw.get('detected_by')
                    security_log.risk_level = security_log_raw.get('risk_level')
                    security_logs.append(security_log)
                if is_sender:
                    user.sender = security_logs
                else:
                    user.recipient = security_logs
        except Exception:
            logger.exception(f'Failed creating instance for recipient {user_raw}')

    def _create_user(self, user_raw: dict, user: MyUserAdapter):
        try:
            user_id = user_raw.get('id')
            if user_id is None:
                logger.warning(f'Bad user with no ID {user_raw}')
                return None
            user_id = str(user_id)
            user.id = user_id

            if '@' in user_id:
                username, domain = user_id.split('@', 1)
                user.username = username
                user.domain = domain
            else:
                user.username = username

            if user_raw.get('sender') and isinstance(user_raw.get('sender'), dict):
                self._fill_cloud_app_security_user_fields(user_raw.get('sender'), user)

            if user_raw.get('recipient') and isinstance(user_raw.get('recipient'), dict):
                self._fill_cloud_app_security_user_fields(user_raw.get('recipient'), user, is_sender=False)

            user.set_raw(user_raw)
            return user
        except Exception:
            logger.exception(f'Problem with fetching CloudAppSecurity User for {user_raw}')
            return None

    # pylint: disable=arguments-differ
    def _parse_users_raw_data(self, users_raw_data):
        """
        Gets raw data and yields User objects.
        :param users_raw_data: the raw data we get.
        :return:
        """
        for user_raw in users_raw_data:
            if not user_raw:
                continue
            try:
                # noinspection PyTypeChecker
                user = self._create_user(user_raw, self._new_user_adapter())
                if user:
                    yield user
            except Exception:
                logger.exception(f'Problem with fetching CloudAppSecurity User for {user_raw}')

    @classmethod
    def adapter_properties(cls):
        return [AdapterProperty.UserManagement]

    @classmethod
    def _db_config_schema(cls) -> dict:
        return {
            'items': [
                {
                    'name': 'async_chunks',
                    'type': 'integer',
                    'title': 'Async chunks in parallel'
                }
            ],
            'required': [
                'async_chunks'
            ],
            'pretty_name': 'Cloud App Security Configuration',
            'type': 'array'
        }

    @classmethod
    def _db_config_default(cls):
        return {
            'async_chunks': DEFAULT_ASYNC_CHUNKS_SIZE
        }

    def _on_config_update(self, config):
        self.__async_chunks = config.get('async_chunks') or DEFAULT_ASYNC_CHUNKS_SIZE
