import logging

from axonius.adapter_base import AdapterBase, AdapterProperty
from axonius.adapter_exceptions import ClientConnectionException
from axonius.clients.rest.connection import RESTConnection
from axonius.clients.rest.connection import RESTException
from axonius.utils.files import get_local_config_file
from axonius.utils.datetime import parse_date
from knowbe4_adapter.connection import Knowbe4Connection
from knowbe4_adapter.client_id import get_client_id
from knowbe4_adapter.structures import Knowbe4UserInstance, SecurityTestResult, EnrollmentData

logger = logging.getLogger(f'axonius.{__name__}')


class Knowbe4Adapter(AdapterBase):
    class MyUserAdapter(Knowbe4UserInstance):
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
        connection = Knowbe4Connection(domain=client_config['domain'],
                                       verify_ssl=client_config['verify_ssl'],
                                       https_proxy=client_config.get('https_proxy'),
                                       apikey=client_config['apikey'])
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

    @staticmethod
    # pylint: disable=arguments-differ
    def _query_users_by_client(client_name, client_data):
        """
        Get all users from a specific domain

        :param str client_name: The name of the client
        :param obj client_data: The data that represent a connection

        :return: A json with all the attributes returned from the Server
        """
        with client_data:
            yield from client_data.get_user_list()

    @staticmethod
    def _clients_schema():
        """
        The schema Knowbe4Adapter expects from configs

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
                    'name': 'apikey',
                    'title': 'API Key',
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
                }
            ],
            'required': [
                'domain',
                'apikey',
                'verify_ssl'
            ],
            'type': 'array'
        }

    # pylint: disable=too-many-branches, too-many-statements, too-many-locals, too-many-nested-blocks
    @staticmethod
    def _fill_knowbe4_user_fields(user_raw: dict, user: MyUserAdapter):
        try:
            try:
                user.phish_prone_percentage = user_raw.get('phish_prone_percentage')
            except Exception:
                pass
            user.extension = user_raw.get('extension')
            user.location = user_raw.get('location')
            user.division = user_raw.get('division')
            user.manager_email = user_raw.get('manager_email')
            adi_manageable = user_raw.get('adi_manageable')
            if isinstance(adi_manageable, bool):
                user.adi_manageable = adi_manageable
            try:
                user.current_risk_score = user_raw.get('current_risk_score')
            except Exception:
                pass
            aliases = user_raw.get('aliases')
            if isinstance(aliases, list):
                user.aliases = aliases
            user.joined_on = parse_date(user_raw.get('joined_on'))
            user.organization = user_raw.get('organization')
            user.user_language = user_raw.get('language')
            user.comment = user_raw.get('comment')
            user.employee_start_date = parse_date(user_raw.get('employee_start_date'))
            user.archived_at = parse_date(user_raw.get('archived_at'))
            user.groups = user_raw.get('group_names')
            enrol_data = user_raw.get('enrol_data')
            if not isinstance(enrol_data, list):
                enrol_data = []
            for enrol_raw in enrol_data:
                try:
                    content_type = enrol_raw.get('content_type')
                    time_spent = enrol_raw.get('time_spent')
                    if not isinstance(time_spent, int):
                        time_spent = None
                    policy_acknowledged = enrol_raw.get('policy_acknowledged')
                    if not isinstance(policy_acknowledged, bool):
                        policy_acknowledged = None
                    enrollment_data_obj = EnrollmentData(content_type=content_type,
                                                         module_name=enrol_raw.get('module_name'),
                                                         campaign_name=enrol_raw.get('campaign_name'),
                                                         enrollment_date=parse_date(enrol_raw.get('enrollment_date')),
                                                         start_date=parse_date(enrol_raw.get('start_date')),
                                                         completion_date=parse_date(enrol_raw.get('completion_date')),
                                                         status=enrol_raw.get('status'),
                                                         time_spent=time_spent,
                                                         policy_acknowledged=policy_acknowledged)
                    user.enrollment_data.append(enrollment_data_obj)
                except Exception:
                    logger.exception(f'Problem with enrol {enrol_raw}')

            sec_test_user_data = user_raw.get('sec_test_user_data')
            if not isinstance(sec_test_user_data, list):
                sec_test_user_data = []
            for sec_data in sec_test_user_data:
                try:
                    (sec_test_raw, pst_user) = sec_data
                    sec_test_name = sec_test_raw.get('name')
                    sec_test_status = sec_test_raw.get('status')
                    sec_test_started_at = parse_date(sec_test_raw.get('started_at'))
                    sec_test_duration = sec_test_raw.get('duration')
                    if not isinstance(sec_test_duration, int):
                        sec_test_duration = None
                    template_name = (pst_user.get('template_name') or {}).get('name')
                    attachment_opened_at = parse_date(pst_user.get('attachment_opened_at'))
                    macro_enabled_at = parse_date(pst_user.get('macro_enabled_at'))
                    data_entered_at = parse_date(pst_user.get('data_entered_at'))
                    vulnerable_plugins_at = parse_date(pst_user.get('vulnerable-plugins_at'))
                    sec_test_result_obj = SecurityTestResult(sec_test_name=sec_test_name,
                                                             sec_test_status=sec_test_status,
                                                             sec_test_started_at=sec_test_started_at,
                                                             sec_test_duration=sec_test_duration,
                                                             template_name=template_name,
                                                             scheduled_at=parse_date(pst_user.get('scheduled_at')),
                                                             delivered_at=parse_date(pst_user.get('delivered_at')),
                                                             opened_at=parse_date(pst_user.get('opened_at')),
                                                             clicked_at=parse_date(pst_user.get('clicked_at')),
                                                             replied_at=parse_date(pst_user.get('replied_at')),
                                                             attachment_opened_at=attachment_opened_at,
                                                             macro_enabled_at=macro_enabled_at,
                                                             data_entered_at=data_entered_at,
                                                             vulnerable_plugins_at=vulnerable_plugins_at,
                                                             exploited_at=parse_date(pst_user.get('exploited_at')),
                                                             reported_at=parse_date(pst_user.get('reported_at')),
                                                             bounced_at=parse_date(pst_user.get('bounced_at')),
                                                             ip=pst_user.get('ip'),
                                                             ip_location=pst_user.get('ip_location'),
                                                             browser=pst_user.get('browser'),
                                                             browser_version=pst_user.get('browser_version'),
                                                             os=pst_user.get('os')
                                                             )
                    user.sec_test_results.append(sec_test_result_obj)

                except Exception:
                    logger.exception(f'Problem with sec data {sec_data}')
        except Exception:
            logger.exception(f'Failed creating instance for user {user_raw}')

    def _create_user(self, user_raw: dict, user: MyUserAdapter):
        try:
            user_id = user_raw.get('id')
            if user_id is None:
                logger.warning(f'Bad user with no ID {user_raw}')
                return None
            user.id = str(user_id) + '_' + (user_raw.get('email') or '')
            user.mail = user_raw.get('email')
            user.user_status = user_raw.get('status')
            user.employee_number = user_raw.get('employee_number')
            user.first_name = user_raw.get('first_name')
            user.last_name = user_raw.get('last_name')
            user.user_title = user_raw.get('job_title')
            user.user_telephone_number = user_raw.get('phone_number')
            user.user_manager = user_raw.get('manager_name')
            user.user_department = user_raw.get('department')
            user.last_logon = parse_date(user_raw.get('last_sign_in'))
            self._fill_knowbe4_user_fields(user_raw, user)

            user.set_raw(user_raw)

            return user
        except Exception:
            logger.exception(f'Problem with fetching Knowbe4 User for {user_raw}')
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
                logger.exception(f'Problem with fetching Knowbe4 User for {user_raw}')

    @classmethod
    def adapter_properties(cls):
        return [AdapterProperty.UserManagement]
