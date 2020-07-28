import datetime
import json
import logging
# pylint: disable=import-error
from zeep.helpers import serialize_object
from axonius.fields import Field
from axonius.users.user_adapter import UserAdapter
from axonius.adapter_base import AdapterBase, AdapterProperty
from axonius.adapter_exceptions import ClientConnectionException
from axonius.clients.rest.connection import RESTConnection
from axonius.clients.rest.connection import RESTException
from axonius.utils.datetime import parse_date
from axonius.utils.files import get_local_config_file
from axonius.utils.json import from_json
from workday_adapter.connection import WorkdayConnection
from workday_adapter.client_id import get_client_id
from workday_adapter.consts import WORKER_PURGE_FIELDS

logger = logging.getLogger(f'axonius.{__name__}')


class WorkdayAdapter(AdapterBase):
    # pylint: disable=too-many-instance-attributes
    class MyUserAdapter(UserAdapter):
        start_date = Field(datetime.datetime, 'Employment Start Date')
        end_date = Field(datetime.datetime, 'Employment End Date')
        location = Field(str, 'Location')
        is_active = Field(bool, 'Is Active')
        active_status_date = Field(datetime.datetime, 'Active Status Change Date')
        hire_date = Field(datetime.datetime, 'Hire Date')
        is_terminated = Field(bool, 'Is Terminated')
        terminated_date = Field(datetime.datetime, 'Termination Date')
        is_rehire = Field(bool, 'Rehire')
        original_hire_date = Field(datetime.datetime, 'Original Hire Date')
        reporting_name = Field(str, 'Reporting Name')

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
        connection = WorkdayConnection(domain=client_config['domain'],
                                       tenant=client_config['tenant'],
                                       verify_ssl=client_config['verify_ssl'],
                                       https_proxy=client_config.get('https_proxy'),
                                       username=client_config['username'],
                                       password=client_config['password'])
        with connection:
            pass
        return connection

    def _connect_client(self, client_config):
        try:
            return self.get_connection(client_config)
        except RESTException as e:
            message = 'Error connecting to client with domain {0}, reason: {1}'.format(
                client_config['domain'], str(e))
            logger.exception(message)
            raise ClientConnectionException(message)

    # pylint:disable=arguments-differ
    @staticmethod
    def _query_users_by_client(key, data):
        with data:
            yield from data.get_users_list()

    @staticmethod
    def _clients_schema():
        """
        The schema WorkdayAdapter expects from configs

        :return: JSON scheme
        """
        return {
            'items': [
                {
                    'name': 'domain',
                    'title': 'Workday Domain',
                    'description': 'Example: https://MY_INSTANCE.workday.com',
                    'type': 'string'
                },
                {
                    'name': 'tenant',
                    'title': 'Workday Tenant Name',
                    'type': 'string'
                },
                # {
                #     'name': 'version',
                #     'title': 'Workday "Human Resources" API version',
                #     'description': 'Example: v34.0',
                #     'type': 'string',
                #     'default': 'v24.1'
                # },
                {
                    'name': 'username',
                    'title': 'User Name',
                    'type': 'string'
                },
                {
                    'name': 'password',
                    'title': 'Password',
                    'type': 'string',
                    'format': 'password'
                },
                {
                    'name': 'priavte_key',
                    'title': 'Private Key File',
                    'type': 'file'
                },
                {
                    'name': 'public_cert',
                    'title': 'Public Certificate File',
                    'type': 'file',
                    'format': 'password'
                },
                {
                    'name': 'cert_passphrase',
                    'title': 'Certificate Passphrase',
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
                'tenant',
                'username',
                'password',
                'verify_ssl'
            ],
            'type': 'array'
        }

    @staticmethod
    def _serialize_worker(worker_obj):
        worker_json = serialize_object(worker_obj, dict)
        for key in WORKER_PURGE_FIELDS:
            __purged = worker_json.pop(key, None)
        return worker_json

    @staticmethod
    def _parse_date(date_obj):
        try:
            bad_date = datetime.date(1900, 1, 1)
            if date_obj == bad_date or not date_obj:
                return None
            return parse_date(datetime.datetime.fromordinal(date_obj.toordinal()))
        except Exception as e:
            logger.warning(f'Failed to parse date {date_obj} as datetime.datetime: {str(e)}')
        return None

    # pylint: disable = too-many-statements
    def _create_user(self, worker_obj):
        try:
            user = self._new_user_adapter()
            user_id = worker_obj.User_ID
            if user_id is None:
                logger.warning(f'Bad user with no ID {worker_obj}')
                return None

            # Axonius generic stuff
            user.id = f'{user_id}_{str(worker_obj.Worker_ID) or ""}'
            user.mail = user_id
            user.employee_id = worker_obj.Worker_ID
            user_name = None
            # Parse the user's name from the object
            try:
                name_data = worker_obj.Personal_Data.Name_Data
                user_name = name_data.Legal_Name_Data.Name_Detail_Data.Formatted_Name
                user.display_name = user_name
                user.first_name = name_data.Legal_Name_Data.Name_Detail_Data.First_Name
                user.last_name = name_data.Legal_Name_Data.Name_Detail_Data.Last_Name
                user.reporting_name = name_data.Legal_Name_Data.Name_Detail_Data.Reporting_Name
            except Exception as e:
                logger.warning(f'Failed to process name for {user_id}: {str(e)}')

            # Parse the user's employment/job information
            try:
                # Get the "Primary Position Data" (this doesn't exist on older versions of the API)
                work_job_data = worker_obj.Employment_Data.Worker_Job_Data[0]
                user.user_title = work_job_data.Position_Detail_Data.Position_Title
                user.start_date = self._parse_date(work_job_data.Position_Detail_Data.Start_Date)
                user.end_date = self._parse_date(work_job_data.Position_Detail_Data.End_Date)
            except Exception as e:
                # Log as DEBUG because this information might not exist for older API versions, so less log spam
                logger.debug(f'Failed to parse job information for {user_id}: {str(e)}')

            # More employment information, this time always should be available
            try:
                # Get worker employment status data
                work_status_data = worker_obj.Employment_Data.Worker_Status_Data
                user.is_active = work_status_data.Active
                user.active_status_date = self._parse_date(work_status_data.Active_Status_Date)
                user.hire_date = self._parse_date(work_status_data.Hire_Date)
                user.is_terminated = work_status_data.Terminated
                user.terminated_date = self._parse_date(work_status_data.Termination_Date)
                user.is_rehire = work_status_data.Rehire
                user.original_hire_date = self._parse_date(work_status_data.Original_Hire_Date)
                if not getattr(user, 'end_date', None):
                    user.end_date = self._parse_date(work_status_data.End_Employment_Date)
            except Exception as e:
                logger.warning(f'Failed to parse employment status information for {user_id}: {str(e)}')

            # Parse the user's Organization information
            try:
                org_data = worker_obj.Organization_Data.Worker_Organization_Data
                org_units = list()
                for org in org_data:
                    this_org = org.Organization_Data
                    org_units.append(this_org.Organization_Name)
                    subtype = this_org.Organization_Subtype_Reference.Descriptor
                    if subtype != 'Department':
                        continue
                    user.user_department = this_org.Organization_Name
                    if this_org.Primary_Business_Site_Reference:
                        user.location = this_org.Primary_Business_Site_Reference.Descriptor
                user.organizational_unit = org_units
            except Exception as e:
                logger.warning(f'Failed to parse organization data for {user_id}: {str(e)}')

            # Set raw.
            # Purge sensitive information and add some back
            worker_raw = self._serialize_worker(worker_obj)
            worker_raw['name'] = user_name
            # pylint: disable = unnecessary-lambda
            # The object by default contains `datetime.date` objects which are not JSON-serializable
            # So I serialize the json myself, converting all objects to strings
            user.set_raw(from_json(json.dumps(worker_raw, default=lambda x: str(x))))
            return user
        except Exception:
            logger.exception(f'Problem with fetching Workday Worker for {worker_obj}')
            return None

    def _parse_users_raw_data(self, users_raw):
        for user_raw in users_raw:
            user = self._create_user(user_raw.Worker_Data)
            if user:
                yield user

    @classmethod
    def adapter_properties(cls):
        return [AdapterProperty.UserManagement]
